from types import SimpleNamespace

import fiona
import numpy as np
import pytest
from qgis.core import Qgis

from AcATaMa.core import estimators
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.gui import accuracy_assessment_results


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
