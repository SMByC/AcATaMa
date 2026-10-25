from types import SimpleNamespace

import fiona
import numpy as np
import pytest
from qgis.core import Qgis, QgsProject, QgsRasterRange, QgsVectorLayer
from qgis.gui import QgsMapLayerComboBox

from AcATaMa.core import estimators
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.core.map import Map
from AcATaMa.core.sampling_design import Sampling
from AcATaMa.gui import accuracy_assessment_results
from AcATaMa.gui.sampling_report import SamplingReport


def clean_raw_html(html):
    return html.replace("\n", "").replace("\t", "").replace(" ", "")


def test_accuracy_assessment_simple_html(plugin, restore_config_file):
    # restore
    input_yml_path = (
        pytest.tests_data_dir.parent.parent / "examples" / "Simple exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_to_review.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_accuracy_assessment_simple_post_stratify_html(plugin, restore_config_file):
    # restore
    input_yml_path = (
        pytest.tests_data_dir.parent.parent
        / "examples"
        / "Simple post-stratify exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(
    #     pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_post_stratify_to_review.html", "w"
    # )
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_post_stratify_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_accuracy_assessment_systematic_html(plugin, restore_config_file):
    # restore
    input_yml_path = (
        pytest.tests_data_dir.parent.parent / "examples" / "Systematic exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_to_review.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_accuracy_assessment_systematic_post_stratify_html(plugin, restore_config_file):
    # restore
    input_yml_path = (
        pytest.tests_data_dir.parent.parent
        / "examples"
        / "Systematic post-stratify exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(
    #     pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_post_stratify_to_review.html", "w"
    # )
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_post_stratify_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_accuracy_assessment_stratified_html(plugin, restore_config_file):
    # restore
    input_yml_path = (
        pytest.tests_data_dir.parent.parent / "examples" / "Stratified exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_stratified_to_review.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_stratified_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_accuracy_assessment_samples_in_zero_and_outside_html(plugin, restore_config_file):
    """Test accuracy assessment for samples with zero values and outside thematic map coverage."""
    # restore
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # Uncomment the following lines to generate the expected HTML file for review
    # in_file = open(
    #     pytest.tests_data_dir / "analysis" / "accuracy_assessment_samples_in_zero_and_outside_revised.html", "w"
    # )
    # in_file.write(result_html_computed)

    # load the html file
    with open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_samples_in_zero_and_outside_revised.html") as f:
        result_html_in_file = f.read()

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file)


def test_analysis_without_labeled_samples(plugin, restore_config_file):
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)

    accuracy_assessment = AccuracyAssessmentWindow()
    for point in accuracy_assessment.analysis.response_design.points:
        point.label_id = None
        point.is_labeled = False
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()

    assert accuracy_assessment.analysis.compute()
    assert accuracy_assessment.analysis.values == []
    html = accuracy_assessment_results.get_html(accuracy_assessment.analysis)
    assert "There are no labeled samples inside the thematic map" in html


def test_analysis_with_a_single_reference_class(plugin, restore_config_file):
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)

    accuracy_assessment = AccuracyAssessmentWindow()
    label_id = min(accuracy_assessment.analysis.response_design.buttons_config)
    for point in accuracy_assessment.analysis.response_design.points:
        point.label_id = label_id
        point.is_labeled = True
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()

    assert accuracy_assessment.analysis.compute()
    html = accuracy_assessment_results.get_html(accuracy_assessment.analysis)
    assert "Class area adjusted" in html


def test_analysis_with_samples_labeled_with_deleted_buttons(plugin, restore_config_file):
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)

    accuracy_assessment = AccuracyAssessmentWindow()
    point = next(p for p in accuracy_assessment.analysis.response_design.points if p.is_labeled)
    point.label_id = 999
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()

    # the error is reported to the user and the results are not computed
    assert not accuracy_assessment.analysis.compute()


def test_estimator_must_match_the_sampling_design(plugin, restore_config_file):
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)
    accuracy_assessment = AccuracyAssessmentWindow()
    sampling_report = SamplingReport.instances[accuracy_assessment.analysis.response_design.sampling_layer]
    assert sampling_report.report["general"]["sampling_type"] == "stratified"

    # stratified sample analyzed with the simple estimator
    accuracy_assessment.analysis.estimator = "Simple/systematic estimator"
    accuracy_assessment.analysis.compute()
    assert "Ignoring the stratification biases" in accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # stratified sample with strata different from the thematic map classes (other pixel counts)
    thematic_map_table = sampling_report.report["samples"]["thematic_map"]
    sampling_report.report["general"]["sampling_map"] = "other map"
    sampling_report.report["samples"]["sampling_map"] = {
        **thematic_map_table,
        "total_pixels": [count + 1 for count in thematic_map_table["total_pixels"]],
    }
    accuracy_assessment.analysis.estimator = "Stratified estimator"
    html = accuracy_assessment_results.get_html(accuracy_assessment.analysis)
    assert "Ignoring the stratification biases" not in html
    assert "(Stehman, 2014)" in html
    # the analysis with the strata map as thematic map (the same pixel counts)
    sampling_report.report["samples"]["sampling_map"] = thematic_map_table
    assert "(Stehman, 2014)" not in accuracy_assessment_results.get_html(accuracy_assessment.analysis)


def test_population_of_the_estimators(plugin, restore_config_file):
    """The simple estimator includes the map classes without samples, the stratified excludes them"""
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)
    accuracy_assessment = AccuracyAssessmentWindow()
    analysis = accuracy_assessment.analysis

    analysis.estimator = "Simple/systematic estimator"
    assert analysis.compute()
    layer = analysis.thematic_map.qgs_layer
    # all the pixels of the map (without no data) are in the population
    assert sum(analysis.thematic_pixels_count.values()) == layer.width() * layer.height()
    assert len(analysis.map_classes_without_samples) == 15
    assert "They are part of the population of the simple estimator" in accuracy_assessment_results.get_html(analysis)

    analysis.estimator = "Stratified estimator"
    assert analysis.compute()
    assert analysis.values == [0, 37]
    assert "They are excluded from the estimation" in accuracy_assessment_results.get_html(analysis)


def test_warning_for_samples_restricted_to_some_classes(plugin, restore_config_file):
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)
    accuracy_assessment = AccuracyAssessmentWindow()
    analysis = accuracy_assessment.analysis
    sampling_report = SamplingReport.instances[analysis.response_design.sampling_layer]
    # a simple random sample restricted with the classes of the thematic map
    general = sampling_report.report["general"]
    general["sampling_type"] = "simple"
    general["post_stratification_map"] = general["thematic_map"]
    general["post_stratification_classes"] = list(sampling_report.report["samples"]["thematic_map"]["pix_val"])

    analysis.estimator = "Simple/systematic estimator"
    analysis.compute()
    # all the classes were selected, so the sample is not restricted
    assert "The sample excluded the classes" not in accuracy_assessment_results.get_html(analysis)

    general["post_stratification_classes"] = [0, 37]
    assert sampling_report.get_classes_not_selected() == [34, 35, 36, 38, 40, 42, 43, 44, 45, 46, 47, 49, 51, 52, 53]
    assert "The sample excluded the classes 34, 35" in accuracy_assessment_results.get_html(analysis)

    # the post-stratified estimator excludes the classes without samples
    analysis.estimator = "Simple/systematic post-stratified estimator"
    analysis.compute()
    assert "The sample excluded the classes" not in accuracy_assessment_results.get_html(analysis)


def test_accuracy_assessment_export_to_csv(plugin, restore_config_file, tmp_path):
    input_yml_path = (
        pytest.tests_data_dir.parent.parent
        / "examples"
        / "Simple post-stratify exercise - 2019-2020 change - Tinigua.yaml"
    )
    restore_config_file(input_yml_path)
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()

    csv_file = tmp_path / "results.csv"
    accuracy_assessment_results.export_to_csv(accuracy_assessment.analysis, csv_file, ";", ",")
    rows = [line.split(";") for line in csv_file.read_text().splitlines()]

    area_rows = {row[0]: row for row in rows if row and row[0].startswith(("1 (", "2 (", "5 (")) and len(row) == 7}
    # area adjusted, standard error, limits, CV (%) and uncertainty (%) with the decimal separator
    assert area_rows["1 (Stable Forest)"][1:3] == ["141812,35578", "1983,56929"]
    assert area_rows["2 (Deforestation)"][5:7] == ["7,15", "14,01"]
    assert ["", "Overall Accuracy", "Standard error"] in rows


def test_failed_computation_does_not_keep_the_previous_results(plugin, restore_config_file, tmp_path):
    """A computation that fails (a sample labeled with a deleted button) invalidates the previous results,
    so they are neither shown nor exported"""
    restore_config_file(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    accuracy_assessment = AccuracyAssessmentWindow()
    analysis = accuracy_assessment.analysis
    analysis.estimator = estimators.STRATIFIED
    assert analysis.compute()
    accuracy_assessment.ResultsHTML.setHtml(accuracy_assessment_results.get_html(analysis))
    assert "Class area adjusted" in accuracy_assessment.ResultsHTML.toPlainText()

    next(point for point in analysis.response_design.points if point.is_labeled).label_id = 999
    accuracy_assessment.reload(msg_bar=False)
    assert analysis.values is None
    assert "Class area adjusted" not in accuracy_assessment.ResultsHTML.toPlainText()
    assert "could not be computed" in accuracy_assessment.ResultsHTML.toPlainText()
    csv_file = tmp_path / "results.csv"
    assert not accuracy_assessment_results.export_to_csv(analysis, csv_file, ";", ".")
    assert not csv_file.exists()


def test_results_with_a_single_sample_stratum(plugin, restore_config_file, tmp_path):
    """The standard errors that depend on the unknown variance of a stratum with a single sample are not
    reported (instead of reporting them underestimated)"""
    restore_config_file(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    analysis = AccuracyAssessmentWindow().analysis
    analysis.estimator = estimators.STRATIFIED
    assert analysis.compute()
    # leave a single labeled sample in the map class (stratum) 37
    for point in [p for p in analysis.response_design.points if p.is_labeled]:
        if analysis.thematic_map.get_pixel_value_from_pnt(point.QgsPnt) == 37:
            point.is_labeled = False
            break
    assert analysis.compute()
    assert np.array(analysis.error_matrix).sum(axis=1).tolist() == [8, 1]

    html = accuracy_assessment_results.get_html(analysis)
    assert "The strata 37" in html and "have a single sample" in html
    estimates = accuracy_assessment_results.get_estimates(analysis)
    for (
        _label,
        area,
        error,
        lower_limit,
        upper_limit,
        cv,
        uncertainty,
    ) in accuracy_assessment_results.get_class_area_adjusted(analysis, estimates):
        assert area >= 0
        assert np.isnan([error, lower_limit, upper_limit]).all()
        assert np.isnan(cv) and np.isnan(uncertainty)
    assert accuracy_assessment_results.export_to_csv(analysis, tmp_path / "results.csv", ";", ".")


def test_strata_from_another_band_of_the_thematic_map(plugin, restore_config_file):
    """A report of a previous version doesn't identify its maps (fingerprint), so the strata are compared with
    the thematic map of the analysis by the pixel counts of the classes with samples, which can't prove that
    they are the same map"""
    restore_config_file(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    analysis = AccuracyAssessmentWindow().analysis
    general = SamplingReport.instances[analysis.response_design.sampling_layer].report["general"]
    analysis.estimator = estimators.STRATIFIED
    assert analysis.compute()
    sampling_band = analysis.thematic_map.band
    assert "thematic_map_fingerprint" not in general and "thematic_map_band" not in general

    def warnings_with(text):
        return [w for w in accuracy_assessment_results.get_design_warnings(analysis) if text in w]

    assert not warnings_with("(Stehman, 2014)")
    assert len(warnings_with("did not identify its maps")) == 1

    # analysis with another band, whose classes are not the strata
    plugin.dockwidget.QCBox_band_ThematicMap.setCurrentIndex(0)
    assert analysis.compute()
    assert analysis.thematic_map.band != sampling_band
    warnings = warnings_with("(Stehman, 2014)")
    assert len(warnings) == 1
    assert f'"{general["thematic_map"]}"' in warnings[0]
    general["thematic_map_band"] = sampling_band
    assert f'"{general["thematic_map"]}" (band {sampling_band})' in warnings_with("(Stehman, 2014)")[0]


def test_maps_with_the_same_pixel_counts_are_not_the_same_map(plugin, make_raster, tmp_path):
    """The maps of the sampling are identified by their pixel values and georeferencing (fingerprint): maps with
    the same pixel counts by class but different classes in space are not the same strata or restriction"""
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    top_bottom, left_right = np.ones((8, 8)), np.ones((8, 8))
    top_bottom[4:, :] = 2
    left_right[:, 4:] = 2
    boxes = {name: QgsMapLayerComboBox() for name in ("strata", "current")}
    boxes["strata"].setLayer(make_raster(top_bottom, name="strata"))
    boxes["current"].setLayer(make_raster(left_right, name="current"))
    strata_map, current_map = Map(boxes["strata"], band=1), Map(boxes["current"], band=1)
    assert strata_map.get_pixel_counts() == current_map.get_pixel_counts() == {1: 32, 2: 32}

    def design_warnings(sampling, sampling_conf, name, estimator, thematic_map):
        sampling.generate_sampling_points(task, sampling_conf)
        sampling_layer = QgsVectorLayer(sampling.output_file, name, "ogr")
        # owned by the project, a layer destroyed at the exit of the interpreter crashes it
        QgsProject.instance().addMapLayer(sampling_layer)
        SamplingReport(sampling_layer, sampling, sampling_conf)
        analysis = SimpleNamespace(
            response_design=SimpleNamespace(sampling_layer=sampling_layer),
            estimator=estimator,
            thematic_map=thematic_map,
        )
        return accuracy_assessment_results.get_design_warnings(analysis)

    # stratified with the strata map as thematic map, analyzed with the current map
    conf = {
        "sampling_type": "stratified",
        "total_of_samples": [5, 5],
        "min_distance": 0,
        "classes_selected": [1, 2],
        "neighbor_aggregation": None,
        "random_seed": 1,
        "random_seed_by_user": True,
    }
    for thematic_map, warned in ((current_map, True), (strata_map, False)):
        sampling = Sampling(
            "stratified",
            strata_map,
            sampling_map=strata_map,
            sampling_method="fixed values",
            output_file=str(tmp_path / f"stratified_{warned}.gpkg"),
        )
        warnings = design_warnings(sampling, dict(conf), f"stratified {warned}", estimators.STRATIFIED, thematic_map)
        assert any("(Stehman, 2014)" in w for w in warnings) == warned
        assert not any("did not identify its maps" in w for w in warnings)

    # simple random sample restricted to the class 1 of the strata map, analyzed with the current map
    sampling = Sampling(
        "simple", current_map, post_stratification_map=strata_map, output_file=str(tmp_path / "restricted.gpkg")
    )
    conf = {**conf, "sampling_type": "simple", "total_of_samples": 10, "classes_selected": [1]}
    warnings = design_warnings(sampling, conf, "restricted", estimators.POST_STRATIFIED, current_map)
    assert any('restricted to the classes 1 of the post-stratification map "strata"' in w for w in warnings)


def test_samples_restricted_with_a_copy_of_the_thematic_map(plugin, make_raster, tmp_path):
    """A post-stratification map with the same pixel counts by class as the thematic map is identified as it:
    the post-stratified estimator is valid for the classes selected, the simple estimator is not"""
    data = np.ones((8, 8))
    data[:, 4:] = 2
    thematic_box, restriction_box = QgsMapLayerComboBox(), QgsMapLayerComboBox()
    thematic_box.setLayer(make_raster(data, name="thematic"))
    restriction_box.setLayer(make_raster(data, name="copy of the thematic map"))
    thematic_map = Map(thematic_box, band=1)
    output_file = tmp_path / "restricted.gpkg"
    sampling = Sampling(
        "simple", thematic_map, post_stratification_map=Map(restriction_box, band=1), output_file=str(output_file)
    )
    sampling_conf = {
        "sampling_type": "simple",
        "total_of_samples": 10,
        "min_distance": 0,
        "classes_selected": [1],
        "neighbor_aggregation": None,
        "random_seed": 7,
        "random_seed_by_user": True,
    }
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    sampling.generate_sampling_points(task, sampling_conf)
    sampling_layer = QgsVectorLayer(str(output_file), "restricted", "ogr")
    # owned by the project, a layer destroyed at the exit of the interpreter crashes it
    QgsProject.instance().addMapLayer(sampling_layer)
    sampling_report = SamplingReport(sampling_layer, sampling, sampling_conf)
    assert sampling_report.get_classes_not_selected() == [2]

    def design_warnings(estimator):
        analysis = SimpleNamespace(
            response_design=SimpleNamespace(sampling_layer=sampling_layer),
            estimator=estimator,
            thematic_map=thematic_map,
        )
        return accuracy_assessment_results.get_design_warnings(analysis)

    assert not any("restricted to the classes" in w for w in design_warnings(estimators.POST_STRATIFIED))
    assert not any("excluded the classes" in w for w in design_warnings(estimators.POST_STRATIFIED))
    assert any("The sample excluded the classes 2" in w for w in design_warnings(estimators.SIMPLE))


def test_design_warnings_of_the_sampling_report_are_in_the_results(plugin, restore_config_file):
    restore_config_file(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    analysis = AccuracyAssessmentWindow().analysis
    general = SamplingReport.instances[analysis.response_design.sampling_layer].report["general"]
    analysis.estimator = estimators.SIMPLE
    assert analysis.compute()
    general.update(
        sampling_type="systematic",
        initial_inset_mode="Fixed",
        max_xy_offset="0 pixels",
        points_spacing="4 pixels",
        neighbor_aggregation=(8, 8),
    )
    warnings = accuracy_assessment_results.get_design_warnings(analysis)
    assert any(warning.startswith("Non-random systematic grid!") for warning in warnings)
    # the consequences of the neighbor aggregation for the estimator of the analysis
    assert any(
        warning.startswith("Neighbor aggregation restricts the population!")
        and "the area estimates, which use the total area of the whole map, are not valid" in warning
        for warning in warnings
    )


def test_warning_for_samples_restricted_with_another_map(plugin, make_raster, tmp_path):
    """A sample restricted to the classes of another map (here with a smaller extent) only represents the
    area of those classes, but the estimators use the area of the classes in the whole thematic map"""
    thematic_box, restriction_box = QgsMapLayerComboBox(), QgsMapLayerComboBox()
    thematic_box.setLayer(make_raster(np.ones((8, 8)), name="thematic"))
    restriction_box.setLayer(make_raster(np.ones((4, 4)), name="restriction"))
    thematic_map = Map(thematic_box, band=1)
    output_file = tmp_path / "restricted.gpkg"
    sampling = Sampling(
        "simple", thematic_map, post_stratification_map=Map(restriction_box, band=1), output_file=str(output_file)
    )
    sampling_conf = {
        "sampling_type": "simple",
        "total_of_samples": 20,
        "min_distance": 0,
        "classes_selected": [1],
        "neighbor_aggregation": None,
        "random_seed": 45,
        "random_seed_by_user": True,
    }
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    sampling.generate_sampling_points(task, sampling_conf)
    sampling_layer = QgsVectorLayer(str(output_file), "restricted", "ogr")
    # owned by the project, a layer destroyed at the exit of the interpreter crashes it
    QgsProject.instance().addMapLayer(sampling_layer)
    sampling_report = SamplingReport(sampling_layer, sampling, sampling_conf)
    # all the classes of the restriction map were selected
    assert sampling_report.get_classes_not_selected() == []

    for estimator in (estimators.SIMPLE, estimators.POST_STRATIFIED):
        analysis = SimpleNamespace(
            response_design=SimpleNamespace(sampling_layer=sampling_layer),
            estimator=estimator,
            thematic_map=thematic_map,
        )
        warnings = accuracy_assessment_results.get_design_warnings(analysis)
        assert any('restricted to the classes 1 of the post-stratification map "restriction"' in w for w in warnings)


def test_export_of_the_labeled_samples_matches_only_valid_classes(plugin, restore_config_file, tmp_path):
    restore_config_file(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    analysis = AccuracyAssessmentWindow().analysis
    analysis.estimator = estimators.STRATIFIED
    assert analysis.compute()
    response_design = analysis.response_design
    # a labeled sample outside the thematic map (or in no data) and a sample labeled with a deleted button
    outside = analysis.samples_outside_the_thematic[0]
    deleted = next(
        point
        for point in response_design.points
        if point.is_labeled and point not in analysis.samples_outside_the_thematic
    )
    deleted.label_id = 999

    output_file = tmp_path / "labeled.gpkg"
    response_design.save_sampling_labeled(str(output_file))
    with fiona.open(output_file) as features:
        by_id = {feature["properties"]["ID"]: dict(feature["properties"]) for feature in features}

    assert by_id[outside.sample_id]["Is labeled as"] is not None
    assert by_id[outside.sample_id]["In thematic map as"] is None
    assert by_id[outside.sample_id]["Match"] is None
    assert by_id[deleted.sample_id]["Is labeled as"] is None
    assert by_id[deleted.sample_id]["Match"] is None
    valid = [p for p in by_id.values() if p["Is labeled as"] is not None and p["In thematic map as"] is not None]
    assert valid
    assert all(p["Match"] == ("Yes" if p["Is labeled as"] == p["In thematic map as"] else "No") for p in valid)


def test_warning_for_classes_without_reference_samples():
    """A zero standard error does not show that a class is absent"""
    analysis = SimpleNamespace(
        labels={"2": "Deforestation"},
        base_area_unit=Qgis.AreaUnit.SquareMeters,
        estimator=estimators.STRATIFIED,
        response_design=SimpleNamespace(sampling_layer=None),
        samples_outside_the_thematic=[],
        map_classes_without_samples={},
    )
    estimates = estimators.estimate([[50, 0], [3, 0]], [400, 600], analysis.estimator, values=[1, 2])
    assert estimates.area_proportions[1] == estimates.area_proportions_se[1] == 0
    warnings = accuracy_assessment_results.get_report_warnings(analysis, estimates)
    assert any("No sample was labeled as the classes 2 (Deforestation)" in warning for warning in warnings)
    estimates = estimators.estimate([[50, 2], [3, 9]], [400, 600], analysis.estimator, values=[1, 2])
    assert not any(
        "No sample was labeled" in warning
        for warning in accuracy_assessment_results.get_report_warnings(analysis, estimates)
    )


@pytest.mark.parametrize(
    ("estimator", "remedy"),
    [
        (estimators.STRATIFIED, "Add samples to these strata"),
        (estimators.POST_STRATIFIED, "Merge these map classes (post-strata) with similar ones"),
    ],
)
def test_remedy_for_single_sample_strata(estimator, remedy):
    """Merging is only suggested for post-strata: the strata of a stratified sample can have different
    sampling fractions, so pooling their samples would bias the estimates"""
    analysis = SimpleNamespace(
        labels={},
        base_area_unit=Qgis.AreaUnit.SquareMeters,
        estimator=estimator,
        response_design=SimpleNamespace(sampling_layer=None),
        samples_outside_the_thematic=[],
        map_classes_without_samples={},
    )
    estimates = estimators.estimate([[40, 5], [0, 1]], [500, 500], estimator, values=[1, 2])
    warnings = [w for w in accuracy_assessment_results.get_report_warnings(analysis, estimates) if "single sample" in w]
    assert len(warnings) == 1
    assert remedy in warnings[0]
    if estimator == estimators.STRATIFIED:
        assert "merge" not in warnings[0].lower()


def test_identification_of_the_maps_of_the_sampling(plugin, make_raster, tmp_path, monkeypatch):
    """The sampling report keeps the identification of the maps of the sampling (not regenerated from the layers,
    which can change), the pixels that were no data in the sampling are reported when they are part of the
    population of the analysis, and an unidentified map is reported as such"""
    layer = make_raster([[0, 0, 0, 0], [1, 1, 1, 1], [1, 1, 1, 1], [2, 2, 2, 2]], name="thematic")
    other_layer = make_raster([[2, 2, 1, 1], [2, 2, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]], name="other")
    box = QgsMapLayerComboBox()
    box.setLayer(layer)
    output_file = tmp_path / "simple.gpkg"
    sampling = Sampling("simple", Map(box, band=1, nodata=0), output_file=str(output_file))
    sampling_conf = {
        "sampling_type": "simple",
        "total_of_samples": 20,
        "min_distance": 0,
        "classes_selected": None,
        "neighbor_aggregation": None,
        "random_seed": 3,
        "random_seed_by_user": True,
    }
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    sampling.generate_sampling_points(task, sampling_conf)
    sampling_layer = QgsVectorLayer(str(output_file), "simple", "ogr")
    # owned by the project, a layer destroyed at the exit of the interpreter crashes it
    QgsProject.instance().addMapLayer(sampling_layer)
    sampling_report = SamplingReport(sampling_layer, sampling, sampling_conf)
    general = sampling_report.report["general"]
    assert general["thematic_map_nodata"] == [0]
    fingerprint = general["thematic_map_fingerprint"]

    def design_warnings(nodata=0, estimator=estimators.SIMPLE, thematic_map_box=box, **analysis):
        thematic_map = Map(thematic_map_box, band=1, nodata=nodata)
        return accuracy_assessment_results.get_design_warnings(
            SimpleNamespace(
                response_design=SimpleNamespace(sampling_layer=sampling_layer),
                estimator=estimator,
                thematic_map=thematic_map,
                **analysis,
            )
        )

    assert not design_warnings()
    # the no data value of the sampling is not set in the analysis: its pixels are in the population of the simple
    # estimator, not in the one of the post-stratified estimator (the map classes with samples)
    assert any("with the value 0 were no data in the sampling" in w for w in design_warnings(nodata=None))
    post_stratified = design_warnings(
        nodata=None, estimator=estimators.POST_STRATIFIED, values=[1, 2], error_matrix=[[5, 0], [0, 3]]
    )
    assert not any("were no data in the sampling" in w for w in post_stratified)

    # the analysis of another thematic map: the sampling frame can't be verified
    other_box = QgsMapLayerComboBox()
    other_box.setLayer(other_layer)
    assert any(
        'is not the thematic map "thematic" (band 1) of the sampling' in w and "can't verify" in w
        for w in design_warnings(nodata=None, thematic_map_box=other_box)
    )

    # a map that could not be identified when the report was created (not a previous version)
    general["thematic_map_fingerprint"] = None
    warnings = design_warnings(values=[1, 2], error_matrix=[[5, 0], [0, 3]])
    assert any("could not be identified when it was created" in w for w in warnings)
    assert not any("previous version" in w for w in warnings)
    general["thematic_map_fingerprint"] = fingerprint

    # the report keeps the sampling maps when it is reloaded (changing the area unit) after the layer changed
    layer.setDataSource(other_layer.source(), layer.name(), "gdal")
    sampling_report.reload()
    assert general["thematic_map_fingerprint"] == fingerprint
    assert sampling_report.report["general"]["thematic_map_fingerprint"] == fingerprint

    # a restriction defined on the thematic map, which can't be identified now: it is compared by the pixel counts
    # of the classes with samples (only the class 2, with 4 pixels in both)
    general.update(post_stratification_map=general["thematic_map"], post_stratification_classes=[1, 2])
    monkeypatch.setattr(accuracy_assessment_results, "get_map_fingerprint", lambda *args: None)
    warnings = design_warnings(values=[1, 2], error_matrix=[[0, 0], [0, 3]])
    assert any(
        "could not be read to identify it" in w and "do not prove that it is the same map" in w for w in warnings
    )
    assert not any("previous version" in w or "restricted to the classes" in w for w in warnings)
    # and with the class 1, with other pixel counts
    warnings = design_warnings(values=[1, 2], error_matrix=[[3, 0], [0, 3]])
    assert any("restricted to the classes 1, 2" in w for w in warnings)


def test_sampling_frame_of_the_thematic_map(plugin, make_raster, tmp_path):
    """The sampling frame is the area with data of the thematic map of the sampling, with all its no data (also
    the ranges set by the user in the layer), for all the designs"""
    task = type("QgsTask", (object,), {"setProgress": lambda x: None, "isCanceled": lambda: False})
    conf = {"min_distance": 0, "neighbor_aggregation": None, "random_seed": 5, "random_seed_by_user": True}

    def generate(sampling, sampling_conf, name):
        sampling.generate_sampling_points(task, sampling_conf)
        sampling_layer = QgsVectorLayer(sampling.output_file, name, "ogr")
        # owned by the project, a layer destroyed at the exit of the interpreter crashes it
        QgsProject.instance().addMapLayer(sampling_layer)
        SamplingReport(sampling_layer, sampling, sampling_conf)
        return sampling_layer

    def design_warnings(sampling_layer, thematic_map, estimator, values, error_matrix):
        return accuracy_assessment_results.get_design_warnings(
            SimpleNamespace(
                response_design=SimpleNamespace(sampling_layer=sampling_layer),
                estimator=estimator,
                thematic_map=thematic_map,
                values=values,
                error_matrix=error_matrix,
            )
        )

    # stratified with a separate strata map, analyzed with the strata map: the strata are right but the pixels
    # with no data in the thematic map of the sampling could not be sampled
    boxes = {name: QgsMapLayerComboBox() for name in ("thematic", "strata")}
    boxes["thematic"].setLayer(make_raster([[0, 0], [1, 1]], name="thematic"))
    boxes["strata"].setLayer(make_raster([[1, 2], [1, 2]], name="strata"))
    strata_map = Map(boxes["strata"], band=1)
    sampling = Sampling(
        "stratified",
        Map(boxes["thematic"], band=1, nodata=0),
        sampling_map=strata_map,
        sampling_method="fixed values",
        output_file=str(tmp_path / "stratified.gpkg"),
    )
    stratified_conf = {**conf, "sampling_type": "stratified", "total_of_samples": [3, 3], "classes_selected": [1, 2]}
    sampling_layer = generate(sampling, stratified_conf, "stratified")
    warnings = design_warnings(sampling_layer, strata_map, estimators.STRATIFIED, [1, 2], [[3, 0], [3, 0]])
    assert not any("(Stehman, 2014)" in w for w in warnings)
    assert any('is not the thematic map "thematic" (band 1) of the sampling' in w for w in warnings)

    # no data range set by the user in the layer of the sampling, removed in the analysis
    layer = make_raster([[0, 0], [1, 1]], name="user nodata")
    layer.dataProvider().setUserNoDataValue(1, [QgsRasterRange(0, 0)])
    box = QgsMapLayerComboBox()
    box.setLayer(layer)
    sampling = Sampling("simple", Map(box, band=1), output_file=str(tmp_path / "srs.gpkg"))
    simple_conf = {**conf, "sampling_type": "simple", "total_of_samples": 6, "classes_selected": None}
    sampling_layer = generate(sampling, simple_conf, "simple")
    assert SamplingReport.instances[sampling_layer].report["general"]["thematic_map_nodata_ranges"] == [[0, 0, 0]]
    assert not design_warnings(sampling_layer, Map(box, band=1), estimators.SIMPLE, [1], [[6]])
    layer.dataProvider().setUserNoDataValue(1, [])
    warnings = design_warnings(sampling_layer, Map(box, band=1), estimators.SIMPLE, [1], [[6]])
    assert any("with the value 0 were no data in the sampling" in w for w in warnings)

    # a sample restricted to the class 1, with the class 0 as no data (set by the user) only in the analysis: the
    # population of the simple estimator is the restricted one
    layer = make_raster([[0, 0], [1, 1]], name="restricted")
    box = QgsMapLayerComboBox()
    box.setLayer(layer)
    sampling = Sampling(
        "simple", Map(box, band=1), post_stratification_map=Map(box, band=1), output_file=str(tmp_path / "rs.gpkg")
    )
    sampling_layer = generate(sampling, {**simple_conf, "classes_selected": [1]}, "restricted")
    warnings = design_warnings(sampling_layer, Map(box, band=1), estimators.SIMPLE, [1], [[6]])
    assert any("The sample excluded the classes 0" in w for w in warnings)
    layer.dataProvider().setUserNoDataValue(1, [QgsRasterRange(0, 0)])
    warnings = design_warnings(sampling_layer, Map(box, band=1), estimators.SIMPLE, [1], [[6]])
    assert not any("excluded the classes" in w for w in warnings)
