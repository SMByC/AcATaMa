import fiona
import pytest
from shapely.geometry import shape

from AcATaMa.core import config
from AcATaMa.core.map import Map
from AcATaMa.core.sampling_design import Sampling


def test_simple_post_stratified_random_sampling(plugin, unwrap, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # load simple post stratify random sampling config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    categorical_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_CategMap_SimpRS,
                          band=int(plugin.dockwidget.QCBox_band_CategMap_SimpRS.currentText()))
    classes_selected = [int(p) for p in plugin.dockwidget.QPBtn_CategMapClassesSelection_SimpRS.text().split(",")]
    total_of_samples = int(plugin.dockwidget.numberOfSamples_SimpRS.value())
    min_distance = float(plugin.dockwidget.minDistance_SimpRS.value())
    number_of_neighbors = int(plugin.dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors.currentText())
    same_class_of_neighbors = int(plugin.dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(plugin.dockwidget.widget_generate_SimpRS.random_seed_by_user.text())
    output_file = tmpdir.join('test_simple_post_stratified_random_sampling.gpkg')

    sampling = Sampling("simple", thematic_map, categorical_map, output_file=str(output_file))
    sampling.generate_sampling_points(total_of_samples, min_distance, classes_selected, neighbor_aggregation,
                                      random_seed, plugin.dockwidget.widget_generate_SimpRS.QPBar_GenerateSamples)

    with fiona.open(pytest.tests_data_dir / "simple_post_stratified_random_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


def test_stratified_random_sampling(plugin, unwrap, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # load stratify random sampling area based proportion config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    categorical_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_CategMap_StraRS,
                          band=int(plugin.dockwidget.QCBox_band_CategMap_StraRS.currentText()))

    classes_for_sampling = []
    total_of_samples = []
    for row in range(plugin.dockwidget.QTableW_StraRS.rowCount()):
        classes_for_sampling.append(int(plugin.dockwidget.QTableW_StraRS.item(row, 0).text()))
        total_of_samples.append(plugin.dockwidget.QTableW_StraRS.item(row, 2).text())
    total_of_samples = [int(ns) for ns in total_of_samples]
    number_of_neighbors = int(plugin.dockwidget.widget_generate_StraRS.QCBox_NumberOfNeighbors.currentText())
    same_class_of_neighbors = int(plugin.dockwidget.widget_generate_StraRS.QCBox_SameClassOfNeighbors.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    sampling_method = "area based proportion"
    srs_config = {}
    srs_config["total_std_error"] = plugin.dockwidget.TotalExpectedSE.value()
    srs_config["std_dev"] = []
    for row in range(plugin.dockwidget.QTableW_StraRS.rowCount()):
        srs_config["std_dev"].append(float(plugin.dockwidget.QTableW_StraRS.item(row, 3).text()))


    min_distance = float(plugin.dockwidget.minDistance_StraRS.value())
    random_seed = int(plugin.dockwidget.widget_generate_StraRS.random_seed_by_user.text())
    output_file = tmpdir.join('test_stratified_random_sampling.gpkg')

    sampling = Sampling("stratified", thematic_map, categorical_map, sampling_method,
                        srs_config=srs_config, output_file=str(output_file))
    sampling.generate_sampling_points(total_of_samples, min_distance, classes_for_sampling, neighbor_aggregation,
                                      random_seed, plugin.dockwidget.widget_generate_StraRS.QPBar_GenerateSamples)

    with fiona.open(pytest.tests_data_dir / "stratified_random_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


def test_systematic_post_stratified_random_sampling(plugin, unwrap, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # load simple post stratify random sampling config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    categorical_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_CategMap_SystS,
                          band=int(plugin.dockwidget.QCBox_band_CategMap_SystS.currentText()))
    points_spacing = float(plugin.dockwidget.PointsSpacing_SystS.value())
    initial_inset = float(plugin.dockwidget.InitialInset_SystS.value())
    max_xy_offset = float(plugin.dockwidget.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in plugin.dockwidget.QPBtn_CategMapClassesSelection_SystS.text().split(",")]
    number_of_neighbors = int(plugin.dockwidget.widget_generate_SystS.QCBox_NumberOfNeighbors.currentText())
    same_class_of_neighbors = int(plugin.dockwidget.widget_generate_SystS.QCBox_SameClassOfNeighbors.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(plugin.dockwidget.widget_generate_SystS.random_seed_by_user.text())
    output_file = tmpdir.join('test_systematic_post_stratified_random_sampling.gpkg')

    sampling = Sampling("systematic", thematic_map, categorical_map, output_file=str(output_file))
    sampling.generate_systematic_sampling_points(points_spacing, initial_inset, max_xy_offset,
                                                 classes_selected, neighbor_aggregation, random_seed,
                                                 plugin.dockwidget.widget_generate_SystS.QPBar_GenerateSamples)

    with fiona.open(pytest.tests_data_dir / "systematic_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))

