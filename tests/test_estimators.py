import numpy as np
import pytest

from AcATaMa.core import estimators as E

# Olofsson et al. (2014) Table 8, stratified random sample with the map classes as strata
OLOFSSON_2014_MATRIX = [[66, 0, 5, 4], [0, 55, 8, 12], [1, 0, 153, 11], [2, 1, 9, 313]]
OLOFSSON_2014_PIXELS = [200_000, 150_000, 3_200_000, 6_450_000]
# Olofsson et al. (2013) Tables 3-4 (example 1) and Table 6 (example 2)
OLOFSSON_2013_EX1_MATRIX = [[97, 0, 3], [3, 279, 18], [2, 1, 97]]
OLOFSSON_2013_EX1_PIXELS = [22353, 1122543, 610228]
OLOFSSON_2013_EX2_MATRIX = [[127, 66, 54], [2, 322, 17], [0, 15, 540]]
OLOFSSON_2013_EX2_PIXELS = [0.007, 0.295, 0.698]


def test_stratified_reproduces_olofsson_2014_example():
    estimates = E.estimate(OLOFSSON_2014_MATRIX, OLOFSSON_2014_PIXELS, E.STRATIFIED)
    hectares_per_pixel = 0.09

    # Section 5.2.2: area estimates with 95% confidence intervals in hectares
    area = estimates.area_proportions * estimates.total_pixels * hectares_per_pixel
    margin = 1.96 * estimates.area_proportions_se * estimates.total_pixels * hectares_per_pixel
    assert np.round(area).tolist() == [21158, 11686, 285770, 581386]
    assert np.round(margin).tolist() == [6158, 3756, 15510, 16282]
    assert round(estimates.area_proportions_se[0], 4) == 0.0035
    # Table 9, column totals
    assert np.round(estimates.area_proportions, 4).tolist() == [0.0235, 0.0130, 0.3175, 0.6460]
    # Section 5.2.1: accuracy estimates with 95% confidence intervals
    assert np.round(estimates.users_accuracy, 2).tolist() == [0.88, 0.73, 0.93, 0.96]
    assert np.round(1.96 * estimates.users_accuracy_se, 2).tolist() == [0.07, 0.10, 0.04, 0.02]
    assert round(estimates.overall_accuracy, 2) == 0.95
    assert round(1.96 * estimates.overall_accuracy_se, 2) == 0.02
    assert np.round(estimates.producers_accuracy, 2).tolist() == [0.75, 0.85, 0.93, 0.96]
    # only the deforestation interval is compared: the half-widths of the text for forest gain (0.23) and
    # stable non-forest (0.01) differ from Eq. 7 (0.2544 and 0.01836, also with mapaccuracy::olofsson)
    assert round(1.96 * estimates.producers_accuracy_se[0], 2) == 0.21


@pytest.mark.parametrize(
    ("matrix", "pixels", "expected"),
    [
        # values computed with mapaccuracy::olofsson (Costa, R package version 0.1.2)
        (
            OLOFSSON_2014_MATRIX,
            OLOFSSON_2014_PIXELS,
            {
                "overall_accuracy_se": 0.009430417216,
                "producers_accuracy": [0.7486614048, 0.8471563981, 0.9345089086, 0.9616089928],
                "producers_accuracy_se": [0.1088315576, 0.129800184, 0.01751246054, 0.009368130348],
                "area_proportions_se": [0.003490722441, 0.002129153076, 0.008792424205, 0.009229963919],
            },
        ),
        (
            OLOFSSON_2013_EX1_MATRIX,
            OLOFSSON_2013_EX1_PIXELS,
            {
                "overall_accuracy_se": 0.0111643995,
                "producers_accuracy": [0.4806308243, 0.9941886771, 0.8969258968],
                "producers_accuracy_se": [0.1145584559, 0.005778278613, 0.02102355329],
                "area_proportions_se": [0.006125723598, 0.01005743398, 0.01061797108],
            },
        ),
        (
            OLOFSSON_2013_EX2_MATRIX,
            OLOFSSON_2013_EX2_PIXELS,
            {
                "overall_accuracy_se": 0.006053311498,
                "producers_accuracy": [0.6753468084, 0.9307202679, 0.9766497594],
                "producers_accuracy_se": [0.1554026956, 0.01499094976, 0.004899944753],
                "area_proportions_se": [0.001241837162, 0.006052423117, 0.005940044414],
            },
        ),
    ],
)
def test_stratified_matches_reference_implementation(matrix, pixels, expected):
    estimates = E.estimate(matrix, pixels, E.STRATIFIED)
    for name, value in expected.items():
        np.testing.assert_allclose(getattr(estimates, name), value, rtol=1e-8)


def test_producers_accuracy_se_uses_row_totals():
    """Olofsson et al. (2014) Eq. 7 uses (n_ij/n_i+)(1 - n_ij/n_i+) for the strata i != j"""
    n = np.array(OLOFSSON_2014_MATRIX, dtype=float)
    weights = np.array(OLOFSSON_2014_PIXELS) / sum(OLOFSSON_2014_PIXELS)
    estimates = E.estimate(n, OLOFSSON_2014_PIXELS, E.STRATIFIED)
    n_rows = n.sum(axis=1)
    j = 1
    q = n[:, j] / n_rows
    p_j = estimates.producers_accuracy[j]
    own = weights[j] ** 2 * (1 - p_j) ** 2 * q[j] * (1 - q[j]) / (n_rows[j] - 1)
    others = sum(weights[i] ** 2 * q[i] * (1 - q[i]) / (n_rows[i] - 1) for i in range(4) if i != j)
    expected = np.sqrt((own + p_j**2 * others) / estimates.area_proportions[j] ** 2)
    assert estimates.producers_accuracy_se[j] == pytest.approx(expected, rel=1e-12)


def test_post_stratified_variance_from_unit_level_data():
    """Cochran (1977) Eq. 5A.42 for sampling with replacement (without finite population correction) with
    the sample variance of the indicator y_u in each post-stratum"""
    matrix = np.array([[325, 0, 15], [0, 17, 0], [7, 1, 135]])
    pixels = np.array([1611984, 63375, 711441])
    estimates = E.estimate(matrix, pixels, E.POST_STRATIFIED)
    n, N = matrix.sum(), pixels.sum()
    weights = pixels / N
    for j in range(3):
        s2 = [np.var(np.repeat([1.0, 0.0], [row[j], row.sum() - row[j]]), ddof=1) for row in matrix]
        variance = np.dot(weights, s2) / n + np.dot(1 - weights, s2) / n**2
        assert estimates.area_proportions_se[j] == pytest.approx(np.sqrt(variance), rel=1e-12)
    # estimated area of the post-stratified estimator (Olofsson et al., 2014, Eq. 9)
    expected = (weights[:, None] * matrix / matrix.sum(axis=1)[:, None]).sum(axis=0)
    np.testing.assert_allclose(estimates.area_proportions, expected, rtol=1e-12)
    np.testing.assert_allclose(estimates.variance_contributions.sum(axis=0), estimates.area_proportions_se**2)


def test_simple_estimator_formulas():
    matrix = np.array([[40, 5, 5], [10, 30, 0], [0, 2, 8]])
    pixels = [5000, 4000, 1000]
    estimates = E.estimate(matrix, pixels, E.SIMPLE)
    n = 100
    assert estimates.overall_accuracy == pytest.approx(0.78)
    assert estimates.overall_accuracy_se == pytest.approx(np.sqrt(0.78 * 0.22 / 99))
    np.testing.assert_allclose(estimates.users_accuracy, [0.8, 0.75, 0.8])
    np.testing.assert_allclose(estimates.producers_accuracy, [0.8, 30 / 37, 8 / 13])
    np.testing.assert_allclose(estimates.producers_accuracy_se[2], np.sqrt(8 / 13 * 5 / 13 / 12))
    p = np.array([50, 37, 13]) / n
    np.testing.assert_allclose(estimates.area_proportions, p)
    np.testing.assert_allclose(estimates.area_proportions_se, np.sqrt(p * (1 - p) / (n - 1)))
    assert estimates.variance_contributions is None


def test_variance_estimators_are_approximately_unbiased_under_simple_random_sampling():
    """Monte Carlo check: mean of the estimated variances equals the empirical variance of the estimates
    under simple random sampling with replacement, as the random sampling of AcATaMa (its points can fall in
    the same pixel), with a large sampling fraction where a finite population correction would underestimate
    them. The variance of the simple estimator is unbiased, the post-stratified one is a large sample
    approximation (Stehman, 2013)"""
    rng = np.random.default_rng(2026)
    population_size, sample_size, replicates = 1000, 300, 2000
    map_classes = rng.choice(3, size=population_size, p=[0.6, 0.3, 0.1])
    confusion = np.array([[0.92, 0.05, 0.03], [0.10, 0.80, 0.10], [0.15, 0.15, 0.70]])
    cumulative = confusion.cumsum(axis=1)[map_classes]
    reference_classes = (rng.random(population_size)[:, None] > cumulative).sum(axis=1)
    pixels = np.bincount(map_classes, minlength=3)
    true_proportions = np.bincount(reference_classes, minlength=3) / population_size

    for estimator in (E.SIMPLE, E.POST_STRATIFIED):
        proportions, variances = [], []
        for _ in range(replicates):
            sample = rng.choice(population_size, size=sample_size, replace=True)
            matrix = np.zeros((3, 3))
            np.add.at(matrix, (map_classes[sample], reference_classes[sample]), 1)
            estimates = E.estimate(matrix, pixels, estimator)
            proportions.append(estimates.area_proportions)
            variances.append(estimates.area_proportions_se**2)
        proportions, variances = np.array(proportions), np.array(variances)
        np.testing.assert_allclose(proportions.mean(axis=0), true_proportions, atol=0.004)
        # a correction 1 - n/N would give 0.7
        np.testing.assert_allclose(variances.mean(axis=0) / proportions.var(axis=0, ddof=1), 1, atol=0.1)


@pytest.mark.parametrize("estimator", [E.POST_STRATIFIED, E.STRATIFIED])
def test_weighted_estimators_proportions_sum_to_one(estimator):
    estimates = E.estimate(OLOFSSON_2014_MATRIX, OLOFSSON_2014_PIXELS, estimator)
    assert estimates.proportions.sum() == pytest.approx(1)
    np.testing.assert_allclose(estimates.proportions.sum(axis=1), estimates.weights)


@pytest.mark.parametrize("estimator", E.ESTIMATORS)
def test_reference_class_absent_from_the_map(estimator):
    """A reference class without mapped pixels nor samples as map class must not invalidate the results"""
    matrix = [[40, 5, 5], [10, 30, 2], [0, 0, 0]]
    estimates = E.estimate(matrix, [5000, 4000, 0], estimator)
    assert np.isfinite(estimates.overall_accuracy_se)
    assert np.isfinite(estimates.area_proportions_se).all()
    assert np.isfinite(estimates.producers_accuracy_se[:2]).all()
    assert np.isnan(estimates.users_accuracy[2])
    assert not estimates.unsampled_strata
    assert estimates.total_pixels == 9000


@pytest.mark.parametrize("estimator", [E.POST_STRATIFIED, E.STRATIFIED])
def test_stratum_without_samples_is_excluded(estimator):
    matrix = [[40, 5, 5], [10, 30, 2], [0, 0, 0]]
    estimates = E.estimate(matrix, [5000, 4000, 1000], estimator, values=[1, 2, 3])
    assert estimates.unsampled_strata == [3]
    assert estimates.total_pixels == 9000
    assert estimates.weights[2] == 0
    assert estimates.proportions.sum() == pytest.approx(1)


def test_simple_estimator_keeps_unsampled_classes_in_the_population():
    matrix = [[40, 5, 5], [10, 30, 2], [0, 0, 0]]
    estimates = E.estimate(matrix, [5000, 4000, 1000], E.SIMPLE, values=[1, 2, 3])
    assert estimates.total_pixels == 10000
    assert not estimates.unsampled_strata


@pytest.mark.parametrize("estimator", [E.POST_STRATIFIED, E.STRATIFIED])
def test_single_sample_stratum_has_unknown_variance(estimator):
    """The variance within a stratum with a single sample can't be estimated, so the standard errors
    that depend on it are unknown (NaN) instead of underestimated"""
    matrix = [[40, 5, 5], [10, 30, 2], [0, 0, 1]]
    estimates = E.estimate(matrix, [5000, 4000, 1000], estimator, values=[1, 2, 3])
    assert estimates.single_sample_strata == [3]
    assert np.isnan(estimates.users_accuracy_se[2])
    assert np.isfinite(estimates.users_accuracy_se[:2]).all()
    assert np.isnan(estimates.overall_accuracy_se)
    assert np.isnan(estimates.producers_accuracy_se).all()
    assert np.isnan(estimates.area_proportions_se).all()
    assert np.isnan(estimates.variance_contributions[2]).all()
    assert np.isfinite(estimates.variance_contributions[:2]).all()
    # the point estimates are not affected
    assert np.isfinite(estimates.area_proportions).all()
    assert estimates.overall_accuracy == pytest.approx(0.5 * 40 / 50 + 0.4 * 30 / 42 + 0.1)


@pytest.mark.parametrize("estimator", E.ESTIMATORS)
def test_samples_in_a_class_without_pixels_are_rejected(estimator):
    """A sample in a map class means that the class has pixels, else the pixel counts are not the ones
    of the map where the samples are"""
    with pytest.raises(ValueError, match="have samples but no pixels"):
        E.estimate([[40, 10], [5, 45]], [1000, 0], estimator, values=[1, 2])


@pytest.mark.parametrize("estimator", E.ESTIMATORS)
def test_population_without_pixels_is_rejected(estimator):
    with pytest.raises(ValueError, match="no pixels"):
        E.estimate([[5, 5], [1, 9]], [0, 0], estimator)


@pytest.mark.parametrize("estimator", E.ESTIMATORS)
def test_variances_without_finite_population_correction(estimator):
    """The variances are the ones of sampling with replacement, so they only depend on the size of the
    population through the weights, also for a sample as large as the population"""
    matrix = np.array([[50, 7], [3, 40]])
    large_population = E.estimate(matrix, [4 * 10**8, 6 * 10**8], estimator)
    for pixels in ([400, 600], [40, 60], [4, 6]):
        estimates = E.estimate(matrix, pixels, estimator)
        np.testing.assert_allclose(estimates.area_proportions_se, large_population.area_proportions_se, rtol=1e-12)
        assert estimates.overall_accuracy_se == pytest.approx(large_population.overall_accuracy_se, rel=1e-12)
    if estimator == E.SIMPLE:
        np.testing.assert_allclose(large_population.area_proportions_se, np.sqrt(0.53 * 0.47 / 99))


def test_invalid_inputs():
    with pytest.raises(ValueError):
        E.estimate([[1, 0], [0, 1]], [10, 10], "unknown estimator")
    with pytest.raises(ValueError):
        E.estimate([[0, 0], [0, 0]], [10, 10], E.SIMPLE)
