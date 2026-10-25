import math
import random
from types import SimpleNamespace

import fiona
import numpy as np
import pytest
from osgeo import gdal
from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRasterLayer, QgsRectangle
from qgis.gui import QgsMapLayerComboBox
from shapely.geometry import shape

from AcATaMa.core import sampling_design
from AcATaMa.core.map import Map
from AcATaMa.core.sampling_design import (
    Sampling,
    get_expected_number_of_samples,
    get_grid_margins,
    get_initial_insets,
    get_offset_draws_confidence_level,
    get_random_seed,
)
from AcATaMa.utils.others_utils import get_nodata_format
from AcATaMa.utils.system_utils import block_signals_to

# synthetic map of 32x32 pixels of 10 units, in 4x4 pixel blocks: the blocks of the even block-columns
# are fully valid and the blocks of the odd block-columns have only their top-left pixel valid
PIXEL_SIZE = 10
X_MIN, Y_MAX = 500000, 1000000


def partially_valid_map(tmp_path):
    data = np.ones((32, 32), dtype=np.uint8)
    for col in range(32):
        if (col // 4) % 2 == 1:
            data[:, col] = 0
    data[0::4, 4::8] = 1
    path = tmp_path / "partially_valid_map.tif"
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 32, 32, 1, gdal.GDT_Byte)
    dataset.SetGeoTransform((X_MIN, PIXEL_SIZE, 0, Y_MAX, 0, -PIXEL_SIZE))
    dataset.GetRasterBand(1).WriteArray(data)
    dataset.GetRasterBand(1).SetNoDataValue(0)
    dataset = None
    layer = QgsRasterLayer(str(path), "partially valid map")
    QgsProject.instance().addMapLayer(layer)
    combo_box = QgsMapLayerComboBox()
    combo_box.setLayer(layer)
    return Map(file_selected_combo_box=combo_box, band=1, nodata=0), combo_box


def run_systematic(thematic_map, tmp_path, by, seed, confidence_level, inset=2, inset_y=None):
    """Systematic sampling with 4x4 pixels offset areas aligned with the blocks of the synthetic map"""
    unit = 1 if by == "pixels" else PIXEL_SIZE
    sampling = Sampling("systematic", thematic_map, output_file=str(tmp_path / f"sampling_{by}_{seed}.gpkg"))
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    sampling_conf = {
        "total_of_samples": 64,
        "points_spacing": 4 * unit,
        "initial_inset": inset * unit,
        "initial_inset_y": (inset if inset_y is None else inset_y) * unit,
        "max_xy_offset": 2 * unit if confidence_level != "aligned" else 0,
        "classes_selected": None,
        "neighbor_aggregation": None,
        "random_seed": seed,
        "confidence_level": None if confidence_level == "aligned" else confidence_level,
    }
    getattr(sampling, f"generate_systematic_sampling_points_by_{by}")(task, sampling_conf)
    return [
        (int((point.x() - X_MIN) // PIXEL_SIZE), int((Y_MAX - point.y()) // PIXEL_SIZE))
        for point in sampling.points.values()
    ]


@pytest.mark.parametrize("by", ["pixels", "distance"])
def test_systematic_single_draw_has_equal_inclusion_probabilities(plugin, tmp_path, by):
    """Monte Carlo: the valid pixels of the partially and fully valid offset areas are selected
    with the same probability (1/16) with a single draw, but not when the draw is repeated"""
    thematic_map, _combo_box = partially_valid_map(tmp_path)
    valid_pixels_in = {"full": 16 * 32, "partial": 32}

    def inclusion_frequencies(confidence_level, replicates):
        selected = {"full": 0, "partial": 0}
        for seed in range(replicates):
            for col, _row in run_systematic(thematic_map, tmp_path, by, seed, confidence_level):
                selected["partial" if (col // 4) % 2 == 1 else "full"] += 1
        return {block: selected[block] / (replicates * valid_pixels_in[block]) for block in selected}

    single_draw = inclusion_frequencies(None, replicates=40)
    assert single_draw["full"] == pytest.approx(1 / 16)
    assert 0.6 < single_draw["partial"] / single_draw["full"] < 1.5

    repeated_draws = inclusion_frequencies(0.95, replicates=8)
    assert repeated_draws["partial"] / repeated_draws["full"] > 10


@pytest.mark.parametrize("by", ["pixels", "distance"])
def test_systematic_random_start_has_equal_inclusion_probabilities(plugin, tmp_path, by):
    """Monte Carlo with the random initial inset of the sampling design window on a fully valid map:
    the pixels on the edges are selected as often as the others and the mean sample size is the area
    divided by the squared spacing"""
    data = np.ones((24, 24), dtype=np.uint8)
    path = tmp_path / "valid_map.tif"
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 24, 24, 1, gdal.GDT_Byte)
    dataset.SetGeoTransform((X_MIN, PIXEL_SIZE, 0, Y_MAX, 0, -PIXEL_SIZE))
    dataset.GetRasterBand(1).WriteArray(data)
    dataset.GetRasterBand(1).SetNoDataValue(0)
    dataset = None
    layer = QgsRasterLayer(str(path), "valid map")
    QgsProject.instance().addMapLayer(layer)
    combo_box = QgsMapLayerComboBox()
    combo_box.setLayer(layer)
    thematic_map = Map(file_selected_combo_box=combo_box, band=1, nodata=0)

    unit = 1 if by == "pixels" else PIXEL_SIZE
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    replicates = 240
    frequency = np.zeros((24, 24))
    for seed in range(replicates):
        initial_inset, initial_inset_y = get_initial_insets("Random", 0, 6 * unit, seed)
        sampling = Sampling("systematic", thematic_map, output_file=str(tmp_path / f"sampling_{seed}.gpkg"))
        sampling_conf = {
            "total_of_samples": 16,
            "points_spacing": 6 * unit,
            "initial_inset": initial_inset,
            "initial_inset_y": initial_inset_y,
            "max_xy_offset": 3 * unit,
            "classes_selected": None,
            "neighbor_aggregation": None,
            "random_seed": seed,
            "confidence_level": None,
        }
        getattr(sampling, f"generate_systematic_sampling_points_by_{by}")(task, sampling_conf)
        for point in sampling.points.values():
            frequency[int((Y_MAX - point.y()) // PIXEL_SIZE), int((point.x() - X_MIN) // PIXEL_SIZE)] += 1

    expected = replicates / 36  # each pixel is selected with probability 1/(6x6)
    top_left_edges = np.concatenate([frequency[0, :], frequency[1:, 0]])
    bottom_right_edges = np.concatenate([frequency[-1, :], frequency[:-1, -1]])
    assert 0.8 < top_left_edges.mean() / expected < 1.25
    assert 0.8 < bottom_right_edges.mean() / expected < 1.25
    assert 0.8 < frequency[6:18, 6:18].mean() / expected < 1.25
    assert frequency.sum() / replicates == pytest.approx(24 * 24 / 36, rel=0.06)


class ArrayMap:
    """Fully valid map of size x size pixels of 1 unit, without layer, for fast Monte Carlo simulations"""

    nodata = None

    def __init__(self, size):
        self.size = size
        self.qgs_layer = SimpleNamespace(
            crs=lambda: QgsCoordinateReferenceSystem("EPSG:32618"),
            rasterUnitsPerPixelX=lambda: 1,
            rasterUnitsPerPixelY=lambda: 1,
        )

    def extent(self):
        return QgsRectangle(0, 0, self.size, self.size)

    def get_pixel_centroid(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return math.floor(x) + 0.5, math.floor(y) + 0.5
        return None, None


def test_systematic_single_draw_by_distance_has_equal_expected_samples_by_pixel(plugin, monkeypatch):
    """Monte Carlo: with offset areas that tile the map but cut the pixels (fixed inset of half a pixel),
    the pixels cut in 2 or 4 by the borders of the offset areas have the same expected number of samples
    as the others (1/4), because a second sample in the same pixel is not discarded"""
    monkeypatch.setattr(
        sampling_design.QgsVectorFileWriter, "create", lambda *args: SimpleNamespace(addFeature=lambda feature: True)
    )
    monkeypatch.setattr(
        Sampling,
        "check_sampling_point",
        lambda self, point: self.thematic_map.get_pixel_centroid(point.QgsPnt.x(), point.QgsPnt.y())[0] is not None,
    )
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    size, replicates = 8, 4000
    thematic_map = ArrayMap(size)
    frequency = np.zeros((size, size))
    for seed in range(replicates):
        sampling = Sampling("systematic", thematic_map, output_file="in memory.gpkg")
        sampling_conf = {
            "total_of_samples": 16,
            "points_spacing": 2,
            "initial_inset": 0.5,
            "initial_inset_y": 0.5,
            "max_xy_offset": 1,
            "classes_selected": None,
            "neighbor_aggregation": None,
            "random_seed": seed,
            "confidence_level": None,
        }
        sampling.generate_systematic_sampling_points_by_distance(task, sampling_conf)
        for point in sampling.points.values():
            frequency[math.floor(point.y()), math.floor(point.x())] += 1
    frequency /= replicates

    # the even/odd rows and columns are the pixels inside an offset area or cut by its borders
    for rows in (slice(0, None, 2), slice(1, None, 2)):
        for cols in (slice(0, None, 2), slice(1, None, 2)):
            assert frequency[rows, cols].mean() == pytest.approx(1 / 4, abs=0.007)
    assert frequency.sum() == pytest.approx(size * size / 4, abs=0.1)


def test_expected_number_of_samples():
    # the density of the grid, also by distance with overlapping offset areas (the pixels are not deduplicated)
    assert get_expected_number_of_samples(6400, 10) == 64
    assert get_expected_number_of_samples(6400, 10, 30) == 64
    assert get_expected_number_of_samples(100, 60, 30, pixel_size=(30, 30)) == 25
    assert get_expected_number_of_samples(100, 60, pixel_size=(30, 30)) == 25
    # the aligned grid by distance samples a pixel once, all of them with a spacing smaller than the pixels
    assert get_expected_number_of_samples(64, 0.5) == 64
    assert get_expected_number_of_samples(64, 0.5, 1) == 256
    # by pixels, without overlapping offset areas
    assert get_expected_number_of_samples(64, 2, 1, by_pixels=True) == 16
    assert get_expected_number_of_samples(64, 4, 1, by_pixels=True) == 4
    # each pixel in 4 offset areas of 4 pixels
    assert get_expected_number_of_samples(64, 1, 1, by_pixels=True) == pytest.approx(64 * (1 - (3 / 4) ** 4))
    # values not converted to pixels yet (as integers in the sampling by pixels)
    assert get_expected_number_of_samples(64, 1.4, 0.8, by_pixels=True) == 64
    assert get_expected_number_of_samples(64, 0.6, 0.8, by_pixels=True) == 64


def test_expected_number_of_samples_of_a_dense_aligned_grid(plugin, monkeypatch):
    """The aligned grid by distance with a spacing smaller than the pixels samples each pixel once"""
    monkeypatch.setattr(
        sampling_design.QgsVectorFileWriter, "create", lambda *args: SimpleNamespace(addFeature=lambda feature: True)
    )
    monkeypatch.setattr(
        Sampling,
        "check_sampling_point",
        lambda self, point: self.thematic_map.get_pixel_centroid(point.QgsPnt.x(), point.QgsPnt.y())[0] is not None,
    )
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    for seed in range(5):
        initial_inset, initial_inset_y = get_initial_insets("Random", 0, 0.5, seed)
        sampling = Sampling("systematic", ArrayMap(8), output_file="in memory.gpkg")
        sampling_conf = {
            "total_of_samples": 64,
            "points_spacing": 0.5,
            "initial_inset": initial_inset,
            "initial_inset_y": initial_inset_y,
            "max_xy_offset": 0,
            "classes_selected": None,
            "neighbor_aggregation": None,
            "random_seed": seed,
            "confidence_level": None,
        }
        sampling.generate_systematic_sampling_points_by_distance(task, sampling_conf)
        assert sampling.samples_generated == get_expected_number_of_samples(64, 0.5) == 64


def test_expected_number_of_samples_when_changing_the_systematic_unit(plugin, make_raster):
    """The values are converted to the new unit before computing the expected number of samples, once"""
    plugin.dockwidget.QCBox_ThematicMap.setLayer(make_raster(np.ones((8, 8))))
    sampling_design = plugin.dockwidget.sampling_design_window
    sampling_design.QCBox_Systematic_Sampling_Unit.setCurrentText("Distance")
    sampling_design.CL_PerPixelCoverage.setCurrentIndex(0)
    sampling_design.PointSpacing_SystS.setValue(1.4)
    sampling_design.MaxXYoffset_SystS.setValue(0.8)
    assert sampling_design.QPBar_GenerateSamples_SystS.maximum() == round(64 / 1.4**2)
    with block_signals_to(sampling_design.QCBox_Systematic_Sampling_Unit):
        sampling_design.QCBox_Systematic_Sampling_Unit.setCurrentText("Pixels")
    # called directly so that an error fails the test (in a slot it is only reported)
    sampling_design.set_systematic_sampling_unit("Pixels")
    assert (sampling_design.PointSpacing_SystS.value(), sampling_design.MaxXYoffset_SystS.value()) == (1, 1)
    assert sampling_design.QPBar_GenerateSamples_SystS.maximum() == round(64 * (1 - (3 / 4) ** 4))


@pytest.mark.parametrize(("points_spacing", "max_xy_offset"), [(1, 1), (3, 2)])
def test_expected_number_of_samples_by_pixels_with_overlapping_offset_areas(
    plugin, monkeypatch, points_spacing, max_xy_offset
):
    """Monte Carlo with a random start: a pixel drawn by several overlapping offset areas is sampled once"""
    monkeypatch.setattr(
        sampling_design.QgsVectorFileWriter, "create", lambda *args: SimpleNamespace(addFeature=lambda feature: True)
    )
    monkeypatch.setattr(
        Sampling,
        "check_sampling_point",
        lambda self, point: self.thematic_map.get_pixel_centroid(point.QgsPnt.x(), point.QgsPnt.y())[0] is not None,
    )
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    size, replicates = 12, 1500
    thematic_map = ArrayMap(size)
    sample_sizes = []
    for seed in range(replicates):
        initial_inset, initial_inset_y = get_initial_insets("Random", 0, points_spacing, seed)
        sampling = Sampling("systematic", thematic_map, output_file="in memory.gpkg")
        sampling_conf = {
            "total_of_samples": 16,
            "points_spacing": points_spacing,
            "initial_inset": initial_inset,
            "initial_inset_y": initial_inset_y,
            "max_xy_offset": max_xy_offset,
            "classes_selected": None,
            "neighbor_aggregation": None,
            "random_seed": seed,
            "confidence_level": None,
        }
        sampling.generate_systematic_sampling_points_by_pixels(task, sampling_conf)
        sample_sizes.append(sampling.samples_generated)
    expected = get_expected_number_of_samples(size * size, points_spacing, max_xy_offset, by_pixels=True)
    assert expected < size * size / points_spacing**2
    assert np.mean(sample_sizes) == pytest.approx(expected, rel=0.01)


@pytest.mark.parametrize(
    ("inset", "max_xy_offset", "points_spacing"),
    [(0, 2, 4), (2, 2, 4), (12, 2, 4), (3.7, 5, 4), (0.5, 1, 2), (7, 0.5, 3), (1e-6, 3, 6)],
)
def test_grid_margins(inset, max_xy_offset, points_spacing):
    """The grid starts at the last grid point before the inset whose offset area overlaps the map"""
    margin, end_margin = get_grid_margins(inset, max_xy_offset, points_spacing)
    first_grid_point = inset - margin
    assert first_grid_point + max_xy_offset > 0
    assert first_grid_point - points_spacing + max_xy_offset <= 0
    assert margin % points_spacing == pytest.approx(0, abs=1e-9)
    assert end_margin >= max(max_xy_offset, points_spacing)


@pytest.mark.parametrize("by", ["pixels", "distance"])
def test_systematic_single_draw_with_a_fixed_inset_larger_than_the_spacing(plugin, make_raster, tmp_path, by):
    """The fixed initial inset only sets the position of the grid: the offset areas of the grid points before
    it also cover the map, so no strip of the map is left without samples"""
    layer = make_raster(np.ones((16, 16)))
    combo_box = QgsMapLayerComboBox()
    combo_box.setLayer(layer)
    thematic_map = Map(file_selected_combo_box=combo_box, band=1, nodata=None)
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    columns, rows, sample_sizes = set(), set(), []
    for seed in range(20):
        sampling = Sampling("systematic", thematic_map, output_file=str(tmp_path / f"sampling_{by}_{seed}.gpkg"))
        sampling_conf = {
            "total_of_samples": 16,
            "points_spacing": 4,
            "initial_inset": 12,
            "initial_inset_y": 12,
            "max_xy_offset": 2,
            "classes_selected": None,
            "neighbor_aggregation": None,
            "random_seed": seed,
            "confidence_level": None,
        }
        getattr(sampling, f"generate_systematic_sampling_points_by_{by}")(task, sampling_conf)
        sample_sizes.append(sampling.samples_generated)
        columns |= {math.floor(point.x() - 500000) for point in sampling.points.values()}
        rows |= {math.floor(1000000 - point.y()) for point in sampling.points.values()}
    # 9 offset areas inside the map, 12 with half and 4 with a quarter of their area in it
    assert np.mean(sample_sizes) == pytest.approx(16 * 16 / 4**2, abs=1.5)
    assert columns == set(range(16))
    assert rows == set(range(16))


@pytest.mark.parametrize("by", ["pixels", "distance"])
def test_systematic_initial_inset_independent_in_x_and_y(plugin, tmp_path, by):
    thematic_map, _combo_box = partially_valid_map(tmp_path)
    pixels = run_systematic(thematic_map, tmp_path, by, seed=1, confidence_level="aligned", inset=0, inset_y=1)
    assert pixels
    assert {col % 4 for col, _row in pixels} == {0}
    assert {row % 4 for _col, row in pixels} == {1}


def test_offset_draws_options():
    assert get_offset_draws_confidence_level("1 draw (equal probability)") is None
    assert get_offset_draws_confidence_level("Up to 95% coverage") == 0.95
    assert get_offset_draws_confidence_level("80%") == 0.8


def test_initial_insets():
    inset, inset_y = get_initial_insets("Random", 0, 100, 7)
    assert 0 <= inset < 100
    assert 0 <= inset_y < 100
    assert inset != inset_y
    assert get_initial_insets("Random", 0, 100, 7) == (inset, inset_y)
    # independent of the stream used by the sampling with the same seed
    random.seed(7)
    assert random.uniform(0, 100) != inset
    assert get_initial_insets("Fixed", 25, 100, 7) == (25, 25)


def test_random_seed():
    seed, by_user = get_random_seed(False, "")
    assert isinstance(seed, int)
    assert 0 <= seed < 2**32
    assert not by_user
    assert get_random_seed(True, "123") == (123, True)
    assert get_random_seed(True, "s33d") == ("s33d", True)


def test_simple_post_stratified_random_sampling(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = Map(
        file_selected_combo_box=sampling_design.QCBox_PostStratMap_SimpRS,
        band=int(sampling_design.QCBox_band_PostStratMap_SimpRS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SimpRS.text()),
    )
    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SimpRS.text().split(",")]
    total_of_samples = int(sampling_design.numberOfSamples_SimpRS.value())
    min_distance = float(sampling_design.minDistance_SimpRS.value())
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SimpRS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SimpRS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SimpRS.text())
    output_file = tmpdir.join("test_simple_post_stratified_random_sampling.gpkg")

    sampling = Sampling(
        "simple", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": total_of_samples,
        "min_distance": min_distance,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
    }
    # run the sampling
    sampling.generate_sampling_points(task, sampling_conf)

    with (
        fiona.open(pytest.tests_data_dir / "simple_post_stratified_random_sampling.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_stratified_random_sampling(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load stratify random sampling area based proportion config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    sampling_map = Map(
        file_selected_combo_box=sampling_design.QCBox_SamplingMap_StraRS,
        band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()),
    )

    classes_for_sampling = []
    total_of_samples = []
    for row in range(sampling_design.QTableW_StraRS.rowCount()):
        classes_for_sampling.append(int(sampling_design.QTableW_StraRS.item(row, 0).text()))
        total_of_samples.append(sampling_design.QTableW_StraRS.item(row, 2).text())
    total_of_samples = [int(ns) for ns in total_of_samples]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_StraRS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_StraRS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    sampling_method = "area based proportion"
    srs_config = {}
    srs_config["total_std_error"] = sampling_design.TotalExpectedSE.value()
    srs_config["ui"] = []
    for row in range(sampling_design.QTableW_StraRS.rowCount()):
        srs_config["ui"].append(float(sampling_design.QTableW_StraRS.item(row, 3).text()))

    min_distance = float(sampling_design.minDistance_StraRS.value())
    random_seed = int(sampling_design.random_seed_by_user_StraRS.text())
    output_file = tmpdir.join("test_stratified_random_sampling.gpkg")

    sampling = Sampling(
        "stratified",
        thematic_map,
        sampling_map=sampling_map,
        sampling_method=sampling_method,
        srs_config=srs_config,
        output_file=str(output_file),
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": total_of_samples,
        "min_distance": min_distance,
        "classes_selected": classes_for_sampling,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
    }
    # run the sampling
    sampling.generate_sampling_points(task, sampling_conf)

    with (
        fiona.open(pytest.tests_data_dir / "stratified_random_sampling.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_systematic_by_distance_post_stratified_random_sampling(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = Map(
        file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
        band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SystS.text()),
    )
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SystS.text())
    output_file = tmpdir.join("test_systematic_post_stratified_random_sampling.gpkg")

    sampling = Sampling(
        "systematic", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": sampling_design.QPBar_GenerateSamples_SystS.maximum(),
        "points_spacing": points_spacing,
        "initial_inset": initial_inset,
        "max_xy_offset": max_xy_offset,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
        "confidence_level": 0.95,
    }
    # run the sampling
    sampling.generate_systematic_sampling_points_by_distance(task, sampling_conf)

    with (
        fiona.open(pytest.tests_data_dir / "systematic_sampling.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_systematic_by_distance_post_stratified_with_initial_inset_random(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = Map(
        file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
        band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SystS.text()),
    )
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SystS.text())
    output_file = tmpdir.join("test_systematic_post_stratified_with_initial_inset_random.gpkg")

    # set initial inset
    random.seed(random_seed)
    initial_inset = random.uniform(0, points_spacing)

    sampling = Sampling(
        "systematic", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": sampling_design.QPBar_GenerateSamples_SystS.maximum(),
        "points_spacing": points_spacing,
        "initial_inset": initial_inset,
        "max_xy_offset": max_xy_offset,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
        "confidence_level": 0.95,
    }
    # run the sampling
    sampling.generate_systematic_sampling_points_by_distance(task, sampling_conf)

    with (
        fiona.open(pytest.tests_data_dir / "systematic sampling random inset.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_systematic_by_pixels_no_offset(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_systematic_by_pixels_no_offset.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = Map(
        file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
        band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SystS.text()),
    )
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = sampling_design.random_seed_by_user_SystS.text()
    output_file = tmpdir.join("test_systematic_post_stratified_no_offset.gpkg")

    # define the initial inset
    if sampling_design.QCBox_InitialInsetMode_SystS.currentText() == "Random":
        random.seed(random_seed)
        initial_inset = random.uniform(0, points_spacing)
    else:
        initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())

    sampling = Sampling(
        "systematic", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": sampling_design.QPBar_GenerateSamples_SystS.maximum(),
        "points_spacing": points_spacing,
        "initial_inset": initial_inset,
        "max_xy_offset": max_xy_offset,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
        "confidence_level": 0.95,
    }
    # run the sampling
    sampling.generate_systematic_sampling_points_by_pixels(task, sampling_conf)
    with (
        fiona.open(pytest.tests_data_dir / "systematic_by_pixels_no_offset.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_systematic_by_pixels_with_offset(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_systematic_by_pixels_with_offset.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = Map(
        file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
        band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SystS.text()),
    )
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = sampling_design.random_seed_by_user_SystS.text()
    output_file = tmpdir.join("test_systematic_post_stratified_with_offset.gpkg")

    # define the initial inset
    if sampling_design.QCBox_InitialInsetMode_SystS.currentText() == "Random":
        random.seed(random_seed)
        initial_inset = random.uniform(0, points_spacing)
    else:
        initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())

    sampling = Sampling(
        "systematic", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": sampling_design.QPBar_GenerateSamples_SystS.maximum(),
        "points_spacing": points_spacing,
        "initial_inset": initial_inset,
        "max_xy_offset": max_xy_offset,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
        "confidence_level": 0.95,
    }
    # run the sampling
    sampling.generate_systematic_sampling_points_by_pixels(task, sampling_conf)
    with (
        fiona.open(pytest.tests_data_dir / "systematic_by_pixels_with_offset.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))


def test_systematic_right_bottom_borders_with_offset(plugin, restore_config_file, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_systematic_right_bottom_borders_with_offset.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load config for systematic sampling with right/bottom borders and offset, by distance and
    # without post-stratification nor neighbor aggregation as in the configuration file
    assert sampling_design.QCBox_Systematic_Sampling_Unit.currentText() == "Distance"
    assert not sampling_design.QGBox_SystSwithPS.isChecked()
    assert not sampling_design.QGBox_neighbour_aggregation_SystS.isChecked()
    thematic_map = Map(
        file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
        band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
        nodata=get_nodata_format(plugin.dockwidget.nodata_ThematicMap.text()),
    )
    post_stratification_map = None
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())
    classes_selected = None
    neighbor_aggregation = None
    random_seed = sampling_design.random_seed_by_user_SystS.text()
    output_file = tmpdir.join("test_systematic_right_bottom_borders_with_offset.gpkg")

    # define the initial inset
    if sampling_design.QCBox_InitialInsetMode_SystS.currentText() == "Random":
        random.seed(random_seed)
        initial_inset = random.uniform(0, points_spacing)
    else:
        initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())

    sampling = Sampling(
        "systematic", thematic_map, post_stratification_map=post_stratification_map, output_file=str(output_file)
    )
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": sampling_design.QPBar_GenerateSamples_SystS.maximum(),
        "points_spacing": points_spacing,
        "initial_inset": initial_inset,
        "max_xy_offset": max_xy_offset,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed,
        "confidence_level": 0.95,
    }
    # run the sampling
    sampling.generate_systematic_sampling_points_by_distance(task, sampling_conf)
    with (
        fiona.open(pytest.tests_data_dir / "systematic_right_bottom_borders_with_offset.gpkg") as source,
        fiona.open(str(output_file)) as target,
    ):
        assert len(source) == len(target)
        for s, t in zip(source, target, strict=True):
            assert shape(s["geometry"]).equals(shape(t["geometry"]))

    # each sample is inside the map and inside the offset area of a different grid point
    extent = thematic_map.extent()
    grid_points = set()
    for point in sampling.points.values():
        assert extent.contains(point)
        column = round((point.x() - extent.xMinimum() - initial_inset) / points_spacing)
        row = round((extent.yMaximum() - initial_inset - point.y()) / points_spacing)
        assert abs(point.x() - (extent.xMinimum() + initial_inset + column * points_spacing)) <= max_xy_offset
        assert abs(point.y() - (extent.yMaximum() - initial_inset - row * points_spacing)) <= max_xy_offset
        grid_points.add((column, row))
    assert len(grid_points) == len(sampling.points)
