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
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_PostStratMap_SimpRS,
                                  band=int(sampling_design.QCBox_band_PostStratMap_SimpRS.currentText()),
                                  nodata=float(sampling_design.nodata_PostStratMap_SimpRS.text().strip() or "nan"))
    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SimpRS.text().split(",")]
    total_of_samples = int(sampling_design.numberOfSamples_SimpRS.value())
    min_distance = float(sampling_design.minDistance_SimpRS.value())
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SimpRS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SimpRS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SimpRS.text())
    output_file = tmpdir.join('test_simple_post_stratified_random_sampling.gpkg')

    sampling = Sampling("simple", thematic_map, post_stratification_map, output_file=str(output_file))
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": total_of_samples,
        "min_distance": min_distance,
        "classes_selected": classes_selected,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed
    }
    # run the sampling
    sampling.generate_sampling_points(task, sampling_conf)

    with fiona.open(pytest.tests_data_dir / "simple_post_stratified_random_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


def test_stratified_random_sampling(plugin, unwrap, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load stratify random sampling area based proportion config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_StratMap_StraRS,
                                  band=int(sampling_design.QCBox_band_StratMap_StraRS.currentText()),
                                  nodata=float(sampling_design.nodata_StratMap_StraRS.text().strip() or "nan"))

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
    output_file = tmpdir.join('test_stratified_random_sampling.gpkg')

    sampling = Sampling("stratified", thematic_map, post_stratification_map, sampling_method,
                        srs_config=srs_config, output_file=str(output_file))
    # create a mummy QgsTask object
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    # config arguments
    sampling_conf = {
        "total_of_samples": total_of_samples,
        "min_distance": min_distance,
        "classes_selected": classes_for_sampling,
        "neighbor_aggregation": neighbor_aggregation,
        "random_seed": random_seed
    }
    # run the sampling
    sampling.generate_sampling_points(task, sampling_conf)

    with fiona.open(pytest.tests_data_dir / "stratified_random_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


def test_systematic_post_stratified_random_sampling(plugin, unwrap, tmpdir):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
                                  band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
                                  nodata=float(sampling_design.nodata_PostStratMap_SystS.text().strip() or "nan"))
    points_spacing = float(sampling_design.PointsSpacing_SystS.value())
    initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SystS.text())
    output_file = tmpdir.join('test_systematic_post_stratified_random_sampling.gpkg')

    sampling = Sampling("systematic", thematic_map, post_stratification_map, output_file=str(output_file))
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
        "random_seed": random_seed
    }
    # run the sampling
    sampling.generate_systematic_sampling_points(task, sampling_conf)

    with fiona.open(pytest.tests_data_dir / "systematic_sampling.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


def test_systematic_post_stratified_with_initial_inset_random(plugin, unwrap, tmpdir):
    import random
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sampling.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # load simple post stratify random sampling config
    thematic_map = Map(file_selected_combo_box=plugin.dockwidget.QCBox_ThematicMap,
                       band=int(plugin.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(plugin.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
                                  band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
                                  nodata=float(sampling_design.nodata_PostStratMap_SystS.text().strip() or "nan"))
    points_spacing = float(sampling_design.PointsSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())

    classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
    number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
    same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
    neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    random_seed = int(sampling_design.random_seed_by_user_SystS.text())
    output_file = tmpdir.join('test_systematic_post_stratified_with_initial_inset_random.gpkg')

    # set initial inset
    random.seed(random_seed)
    initial_inset = random.uniform(0, points_spacing)

    sampling = Sampling("systematic", thematic_map, post_stratification_map, output_file=str(output_file))
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
        "random_seed": random_seed
    }
    # run the sampling
    sampling.generate_systematic_sampling_points(task, sampling_conf)

    with fiona.open(pytest.tests_data_dir / "systematic sampling random inset.gpkg") as source, \
            fiona.open(str(output_file)) as target:
        for s, t in zip(source, target):
            assert shape(s['geometry']).equals(shape(t['geometry']))


