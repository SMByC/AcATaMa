import pytest

from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.gui import accuracy_assessment_results


def clean_raw_html(html):
    return html.replace('\n', '').replace('\t', '').replace(' ', '')


def test_accuracy_assessment_simple_html(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Simple exercise - 2019-2020 change - Tinigua.yml"
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
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_simple_post_stratify_html(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Simple post-stratify exercise - 2019-2020 change - Tinigua.yml"
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_post_stratify_to_review.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_post_stratify_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_systematic_html(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Systematic exercise - 2019-2020 change - Tinigua.yml"
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
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_systematic_post_stratify_html(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Systematic post-stratify exercise - 2019-2020 change - Tinigua.yml"
    restore_config_file(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_post_stratify_to_review.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_post_stratify_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_stratified_html(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Stratified exercise - 2019-2020 change - Tinigua.yml"
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
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_stratified_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


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
    # in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_samples_in_zero_and_outside_revised.html", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_samples_in_zero_and_outside_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())
