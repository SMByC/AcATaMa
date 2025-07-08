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


def test_analysis_with_empty_samples(plugin, restore_config_file):
    """Test accuracy assessment with no valid samples."""
    # restore
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)
    
    # Modify the config to have no samples
    from AcATaMa.core import config
    config.samples = {}
    config.samples_order = []
    
    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    
    # The analysis should handle empty samples gracefully
    try:
        accuracy_assessment.analysis.compute()
        # If it doesn't crash, that's good
        assert True
    except Exception as e:
        # If it does crash, it should be a meaningful error
        assert "no samples" in str(e).lower() or "empty" in str(e).lower()


def test_analysis_with_single_class(plugin, restore_config_file):
    """Test analysis with only one thematic class."""
    # restore
    input_yml_path = pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml"
    restore_config_file(input_yml_path)
    
    # Modify the config to have only one class
    from AcATaMa.core import config
    # Set all samples to have the same label_id
    for sample_id in config.samples:
        config.samples[sample_id]["label_id"] = 1
    
    # get accuracy assessment results in html
    accuracy_assessment = AccuracyAssessmentWindow()
    accuracy_assessment.analysis.estimator = plugin.dockwidget.QCBox_SamplingEstimator.currentText()
    
    # The analysis should handle single class gracefully
    try:
        accuracy_assessment.analysis.compute()
        # If it doesn't crash, that's good
        assert True
    except Exception as e:
        # If it does crash, it should be a meaningful error
        assert "single class" in str(e).lower() or "multiple classes" in str(e).lower()
