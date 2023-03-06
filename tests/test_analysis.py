import pytest

from AcATaMa.core import config
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.gui import accuracy_assessment_results


def clean_raw_html(html):
    return html.replace('\n', '').replace('\t', '').replace(' ', '')


def test_accuracy_assessment_simple_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Simple exercise - 2019-2020 change - Tinigua.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator_A.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "accuracy_assessment_html_test_1", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_simple_post_stratify_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Simple post-stratify exercise - 2019-2020 change - Tinigua.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator_A.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_simple_post_stratify_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_systematic_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Systematic exercise - 2019-2020 change - Tinigua.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator_A.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "accuracy_assessment_html_test_1", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_systematic_post_stratify_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Systematic post-stratify exercise - 2019-2020 change - Tinigua.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator_A.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_systematic_post_stratify_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())


def test_accuracy_assessment_stratified_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir.parent.parent / "examples" / "Stratified exercise - 2019-2020 change - Tinigua.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator_A.currentText()
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "analysis" / "accuracy_assessment_stratified_revised.html", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())
