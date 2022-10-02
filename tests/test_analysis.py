import pytest

from AcATaMa.core import config
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.gui import accuracy_assessment_results


def clean_raw_html(html):
    return html.replace('\n', '').replace('\t', '').replace(' ', '')


def disabled_test_accuracy_assessment_html(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "accuracy_assessment_config.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = \
        {0: 'Simple random sampling', 1: 'Simple random sampling post-stratified', 2: 'Stratified random sampling'} \
            [plugin.dockwidget.QCBox_SamplingEstimator_A.currentIndex()]
    accuracy_assessment.analysis.compute()
    # set content results in HTML
    result_html_computed = accuracy_assessment_results.get_html(accuracy_assessment.analysis)

    # in_file = open(pytest.tests_data_dir / "accuracy_assessment_html_test_1", 'w')
    # in_file.write(result_html_computed)

    # load the html file
    result_html_in_file = open(pytest.tests_data_dir / "accuracy_assessment_html_test_1", 'r')

    assert clean_raw_html(result_html_computed) == clean_raw_html(result_html_in_file.read())
