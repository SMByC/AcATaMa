"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2026 by Xavier C. Llano, SMByC
        email                : xavier.corredor.llano@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

Design-based estimators of map accuracy and class area from an error matrix of sample counts.

This module is free of QGIS dependencies so the statistics can be verified in isolation.
Notation follows Olofsson et al. (2014): rows i are map classes (the strata), columns j are
reference classes, n_ij are sample counts, N_i the mapped pixels of class i and W_i = N_i / N.
The variances are the ones of sampling with replacement (without finite population correction),
as the random sampling of AcATaMa, whose sampling points can fall in the same pixel; for samples
without replacement, omitting the correction makes the variance estimates larger, negligibly when
the sampling fractions are small, also within each stratum (n_i / N_i). The variances of the
producer's accuracy and of the post-stratified area are large sample approximations.

References:
    Cochran, W.G. (1977). Sampling Techniques, 3rd ed. Wiley.
    Olofsson, P. et al. (2014). Good practices for estimating area and assessing accuracy of
        land change. Remote Sensing of Environment 148, 42-57.
    Stehman, S.V. (2013). Estimating area from an accuracy assessment error matrix.
        Remote Sensing of Environment 132, 202-211.
    Stehman, S.V., Foody, G.M. (2009). Accuracy assessment. In: The SAGE Handbook of Remote Sensing.
"""

from dataclasses import dataclass, field

import numpy as np

SIMPLE = "Simple/systematic estimator"
POST_STRATIFIED = "Simple/systematic post-stratified estimator"
STRATIFIED = "Stratified estimator"
ESTIMATORS = (SIMPLE, POST_STRATIFIED, STRATIFIED)


@dataclass
class Estimates:
    """Accuracy and area estimates; standard errors that cannot be estimated are NaN"""

    estimator: str
    values: list
    error_matrix: np.ndarray
    pixel_counts: np.ndarray
    # rows (map classes) that define the population whose area and accuracy are estimated
    in_population: np.ndarray
    total_pixels: float
    weights: np.ndarray
    # estimated error matrix in terms of proportion of area (p_ij)
    proportions: np.ndarray
    overall_accuracy: float
    overall_accuracy_se: float
    users_accuracy: np.ndarray
    users_accuracy_se: np.ndarray
    producers_accuracy: np.ndarray
    producers_accuracy_se: np.ndarray
    area_proportions: np.ndarray
    area_proportions_se: np.ndarray
    # contribution of each stratum (row) to the variance of the area proportions (columns)
    variance_contributions: np.ndarray | None = None
    # map classes with mapped area but without samples, excluded from the population
    unsampled_strata: list = field(default_factory=list)
    # strata with a single sample, whose variance cannot be estimated, so the standard errors that
    # depend on it are NaN
    single_sample_strata: list = field(default_factory=list)


def _divide(numerator, denominator):
    """Element-wise division returning NaN where the denominator is zero"""
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator != 0, numerator / np.where(denominator != 0, denominator, 1), np.nan)


def estimate(error_matrix, pixel_counts, estimator, values=None):
    """Compute the accuracy and area estimates for the given estimator.

    Args:
        error_matrix: square matrix of sample counts, rows are map classes and columns reference classes
        pixel_counts: number of mapped pixels of each class (same order as the rows)
        estimator: one of SIMPLE, POST_STRATIFIED or STRATIFIED
        values: class values of the rows/columns, used to report the warnings
    """
    if estimator not in ESTIMATORS:
        raise ValueError(f"Unknown estimator: {estimator}")

    n = np.asarray(error_matrix, dtype=float)
    pixels = np.asarray(pixel_counts, dtype=float)
    q = n.shape[0]
    values = list(range(q)) if values is None else list(values)
    n_rows = n.sum(axis=1)
    n_cols = n.sum(axis=0)
    n_total = n.sum()
    if n_total == 0:
        raise ValueError("The error matrix has no samples")

    # the (post-)stratified estimator is undefined for a stratum without samples, so the
    # stratum is excluded and the estimates refer to the area of the sampled strata
    in_population = np.ones(q, dtype=bool) if estimator == SIMPLE else n_rows > 0
    total_pixels = float(pixels[in_population].sum())
    if total_pixels <= 0:
        raise ValueError("The population has no pixels")
    # a sample in a map class means that the class has pixels, else the pixel counts are not the ones of the
    # map where the samples are (another map, band or no data value)
    strata_without_pixels = [values[i] for i in range(q) if n_rows[i] > 0 and pixels[i] <= 0]
    if strata_without_pixels:
        raise ValueError(
            "The map classes {} have samples but no pixels in the thematic map".format(
                ", ".join(str(value) for value in strata_without_pixels)
            )
        )
    weights = np.where(in_population, pixels, 0.0) / total_pixels

    unsampled_strata = [values[i] for i in range(q) if n_rows[i] == 0 and pixels[i] > 0 and not in_population[i]]

    # within-stratum proportions n_ij/n_i+ and the estimated variance of each of them, unknown (NaN)
    # for a stratum with a single sample
    q_ij = np.nan_to_num(_divide(n, n_rows[:, None]))
    estimable = n_rows > 1
    within_variance = np.where(
        estimable[:, None],
        q_ij * (1 - q_ij) / np.where(estimable, n_rows - 1, 1)[:, None],
        np.where(n_rows[:, None] == 1, np.nan, 0.0),
    )

    users_accuracy = _divide(np.diag(n), n_rows)
    users_accuracy_se = np.sqrt(
        np.where(estimable, users_accuracy * (1 - users_accuracy) / np.where(estimable, n_rows - 1, 1), np.nan)
    )

    if estimator == SIMPLE:
        # Stehman and Foody (2009) Table 21.3; area: Stehman (2013) Eq. 18 with the unbiased estimator
        # of the variance of a proportion under simple random sampling with replacement (Cochran, 1977)
        proportions = n / n_total
        overall_accuracy = float(np.trace(n) / n_total)
        overall_accuracy_se = (
            float(np.sqrt(overall_accuracy * (1 - overall_accuracy) / (n_total - 1))) if n_total > 1 else np.nan
        )
        producers_accuracy = _divide(np.diag(n), n_cols)
        producers_accuracy_se = np.sqrt(
            np.where(
                n_cols > 1, producers_accuracy * (1 - producers_accuracy) / np.where(n_cols > 1, n_cols - 1, 1), np.nan
            )
        )
        area_proportions = n_cols / n_total
        area_proportions_se = (
            np.sqrt(area_proportions * (1 - area_proportions) / (n_total - 1)) if n_total > 1 else np.full(q, np.nan)
        )
        return Estimates(
            estimator=estimator,
            values=values,
            error_matrix=n,
            pixel_counts=pixels,
            in_population=in_population,
            total_pixels=total_pixels,
            weights=weights,
            proportions=proportions,
            overall_accuracy=overall_accuracy,
            overall_accuracy_se=overall_accuracy_se,
            users_accuracy=users_accuracy,
            users_accuracy_se=users_accuracy_se,
            producers_accuracy=producers_accuracy,
            producers_accuracy_se=producers_accuracy_se,
            area_proportions=area_proportions,
            area_proportions_se=area_proportions_se,
        )

    # stratified estimators, Olofsson et al. (2014) Eqs. 1-7 and 9, used as post-stratified
    # estimators for simple random and systematic samples
    single_sample_strata = [values[i] for i in range(q) if n_rows[i] == 1]
    proportions = weights[:, None] * q_ij
    overall_accuracy = float(np.trace(proportions))
    overall_accuracy_se = float(np.sqrt(np.sum(weights**2 * np.diag(within_variance))))
    area_proportions = proportions.sum(axis=0)
    producers_accuracy = _divide(np.diag(proportions), area_proportions)

    # Olofsson et al. (2014) Eq. 7, expressed with the area weights W_i = N_i/N
    producers_accuracy_se = np.full(q, np.nan)
    for j in range(q):
        if area_proportions[j] == 0:
            continue
        p_j = producers_accuracy[j]
        own_stratum = weights[j] ** 2 * (1 - p_j) ** 2 * within_variance[j, j]
        other_strata = p_j**2 * sum(weights[i] ** 2 * within_variance[i, j] for i in range(q) if i != j)
        producers_accuracy_se[j] = np.sqrt((own_stratum + other_strata) / area_proportions[j] ** 2)

    if estimator == STRATIFIED:
        # Olofsson et al. (2014) Eq. 10
        variance_contributions = weights[:, None] ** 2 * within_variance
    else:
        # post-stratified variance, Cochran (1977) Eq. 5A.42 and Stehman (2013) Eq. 48 without the finite
        # population correction (sampling with replacement), where the sample variance of y_u (1 if the
        # reference class is j) in stratum i is n_i q_ij (1 - q_ij)/(n_i - 1)
        sample_variance = n_rows[:, None] * within_variance
        stratum_factor = np.where(in_population & (weights > 0), weights / n_total + (1 - weights) / n_total**2, 0)
        variance_contributions = stratum_factor[:, None] * sample_variance
    area_proportions_se = np.sqrt(variance_contributions.sum(axis=0))

    return Estimates(
        estimator=estimator,
        values=values,
        error_matrix=n,
        pixel_counts=pixels,
        in_population=in_population,
        total_pixels=total_pixels,
        weights=weights,
        proportions=proportions,
        overall_accuracy=overall_accuracy,
        overall_accuracy_se=overall_accuracy_se,
        users_accuracy=users_accuracy,
        users_accuracy_se=users_accuracy_se,
        producers_accuracy=producers_accuracy,
        producers_accuracy_se=producers_accuracy_se,
        area_proportions=area_proportions,
        area_proportions_se=area_proportions_se,
        variance_contributions=variance_contributions,
        unsampled_strata=unsampled_strata,
        single_sample_strata=single_sample_strata,
    )
