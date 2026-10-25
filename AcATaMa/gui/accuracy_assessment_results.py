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
"""

import csv
import os

import numpy as np
from qgis.core import Qgis

from AcATaMa.core import estimators
from AcATaMa.utils.qgis_utils import get_source_from
from AcATaMa.utils.system_utils import error_handler

METHODS_NOTES = {
    estimators.SIMPLE: [
        "Accuracy estimated from the sample counts (Stehman and Foody, 2009, Table 21.3).",
        "Area proportion of each reference class estimated as n<sub>+j</sub>/n (Stehman, 2013, Eq. 18), "
        "with the variance estimator p(1 - p)/(n - 1), unbiased for simple random sampling with replacement "
        "(Cochran, 1977).",
    ],
    estimators.POST_STRATIFIED: [
        "Map classes used as post-strata with weights W<sub>i</sub> from the mapped area. Accuracy and its "
        "standard errors estimated with Olofsson et al. (2014), Eqs. 1-7.",
        "Area proportions estimated with Olofsson et al. (2014), Eq. 9, and the approximate (large sample) "
        "post-stratified variance of Cochran (1977), Eq. 5A.42 (Stehman, 2013, Eq. 48), for sampling with "
        "replacement.",
    ],
    estimators.STRATIFIED: [
        "Map classes used as strata with weights W<sub>i</sub> from the mapped area. Accuracy, area and their "
        "standard errors estimated with Olofsson et al. (2014), Eqs. 1-7 and 9-11.",
    ],
}
METHODS_COMMON_NOTES = [
    "The variances are the ones of sampling with replacement (without finite population correction), as the "
    "random sampling of AcATaMa, whose samples can fall in the same pixel; for samples without replacement, "
    "omitting the correction makes them larger, negligibly when the sampling fractions are small, also within "
    "each stratum. The variances of the producer's accuracy and of the post-stratified area are large sample "
    "approximations.",
    "Confidence limits: area &plusmn; z &middot; SE. Coefficient of variation: 100 &middot; SE/area. "
    "Uncertainty: 100 &middot; z &middot; SE/area (half-width of the confidence interval relative to the area).",
    "For systematic samples the standard errors are approximations that usually overestimate the variance "
    "(Olofsson et al., 2014).",
]


def rf(fv, r=5):
    """Round a value for the report, NaN as "-" """
    if fv is None or np.isnan(fv):
        return "-"
    return round(float(fv), r)


def rf_nonzero(fv, r=5):
    """Round a cell of a matrix of proportions, empty cells as "-" """
    return rf(fv, r) if fv > 0 else "-"


def rsig(fv, digits=4):
    """Format a small positive value with significant digits, empty cells as "-" """
    if fv is None or np.isnan(fv) or fv <= 0:
        return "-"
    return float(f"{fv:.{digits}g}")


def percentage(fv):
    """Percentage value for the html report, NaN as "-" """
    value = rf(fv, 2)
    return value if value == "-" else f"{value} %"


def has_samples(accu_asse):
    """If the error matrix has samples"""
    return bool(accu_asse.values) and sum(sum(row) for row in accu_asse.error_matrix) > 0


def get_estimates(accu_asse):
    """Estimates for the error matrix and pixel counts of the analysis"""
    pixel_counts = [accu_asse.thematic_pixels_count[value] for value in accu_asse.values]
    return estimators.estimate(accu_asse.error_matrix, pixel_counts, accu_asse.estimator, accu_asse.values)


def get_report_warnings(accu_asse, estimates):
    """List of warnings (as plain text lines) about the data and the estimation"""
    warnings = []

    def class_label(value):
        return "{} ({})".format(value, accu_asse.labels.get(str(value), "-"))

    if accu_asse.base_area_unit == Qgis.AreaUnit.SquareDegrees:
        warnings.append(
            "The thematic map has a geographic coordinate system, therefore all area values are not accurate. "
            "Use a projected (e.g. equal-area or UTM) coordinate system."
        )
    if accu_asse.samples_outside_the_thematic:
        lines = [
            f"There are {len(accu_asse.samples_outside_the_thematic)} samples labeled that are outside the thematic "
            "map area or inside the no data values, they are ignored for the accuracy assessment results:"
        ]
        lines += [
            f"    {idx + 1}) Sample ID: {sample.sample_id}, "
            f"Coordinate: {int(sample.QgsPnt.x())},{int(sample.QgsPnt.y())}"
            for idx, sample in enumerate(accu_asse.samples_outside_the_thematic)
        ]
        warnings.append("\n".join(lines))
    if estimates is None:
        return warnings
    # all the map classes with pixels but no samples, also the ones not in the error matrix
    without_samples = getattr(accu_asse, "map_classes_without_samples", None) or dict.fromkeys(
        estimates.unsampled_strata, 0
    )
    if without_samples:
        classes = ", ".join(class_label(value) for value in without_samples)
        area = sum(without_samples.values()) * accu_asse.pixel_area_value
        mapped_area = f" ({rf(area)} {accu_asse.pixel_area_unit})" if area > 0 else ""
        if accu_asse.estimator == estimators.SIMPLE:
            warnings.append(
                f"The map classes {classes} have mapped area{mapped_area} but no samples. They are part of the "
                "population of the simple estimator (included in the total area), but the sample has no "
                "information about their accuracy."
            )
        else:
            warnings.append(
                f"The map classes {classes} have mapped area{mapped_area} but no samples, so the estimator "
                "cannot be computed for them. They are excluded from the estimation: the total area and all "
                "estimates refer to the remaining map classes (strata)."
                + (
                    " If these classes were part of the sampled population, merge them with similar classes or use "
                    "the simple estimator to include their area."
                    if accu_asse.estimator == estimators.POST_STRATIFIED
                    else ""
                )
            )
    if estimates.single_sample_strata:
        classes = ", ".join(class_label(value) for value in estimates.single_sample_strata)
        if accu_asse.estimator == estimators.POST_STRATIFIED:
            # merging post-strata keeps the estimator valid, unlike merging the strata of a stratified sample,
            # whose sampling fractions can be different
            remedy = "Merge these map classes (post-strata) with similar ones or increase the sample size."
        else:
            remedy = "Add samples to these strata, at least 2 per stratum (30-50 or more are recommended)."
        warnings.append(
            f"The strata {classes} have a single sample, so the variance within them cannot be estimated and the "
            "standard errors that depend on it (overall and producer's accuracy and all the area estimates) are "
            f"not reported. {remedy}"
        )
    unobserved = [
        value for value, n_col in zip(estimates.values, estimates.error_matrix.sum(axis=0), strict=True) if not n_col
    ]
    if unobserved:
        classes = ", ".join(class_label(value) for value in unobserved)
        warnings.append(
            f"No sample was labeled as the classes {classes}, so their estimated area is zero, but this does not "
            "show that they are absent: a class with a small area can be missed by the sample, which the standard "
            "error does not account for."
        )
    return warnings


def html_matrix(column_labels, row_values, cells, extra_columns=(), bottom_rows=()):
    """Error matrix as a HTML table with the map classes as rows and the validation classes as columns

    Args:
        extra_columns: list of (header, cells by row) after the matrix columns
        bottom_rows: list of (label, cells by matrix column, cells for the extra columns)
    """
    html = """
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        """
    html += f"""<th colspan="{len(column_labels)}">Validation</th>"""
    html += """<td class="empty"></td>""" * len(extra_columns)
    html += """
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        """
    html += "".join(f"<th>{label}</th>" for label in column_labels)
    html += "".join(f"<th>{header}</th>" for header, _ in extra_columns)
    html += "</tr>"
    for idx_row, value in enumerate(row_values):
        html += "<tr>"
        if idx_row == 0:
            html += f"""<th class="th-rows" rowspan="{len(row_values)}">Thematic<br />map</th>"""
        html += f"<th>{value}</th>"
        html += "".join(f"""<td class="highlight">{cell}</td>""" for cell in cells[idx_row])
        html += "".join(f"<td>{column[idx_row]}</td>" for _, column in extra_columns)
        html += "</tr>"
    for label, row_cells, extra_cells in bottom_rows:
        html += f"""<tr><td class="empty"></td><th>{label}</th>"""
        html += "".join(f"<td>{cell}</td>" if cell != "" else """<td class="empty"></td>""" for cell in row_cells)
        html += "".join(f"<td>{cell}</td>" if cell != "" else """<td class="empty"></td>""" for cell in extra_cells)
        html += "</tr>"
    html += """
        </tbody>
        </table>
        """
    return html


def html_accuracy_table(headers, row_labels, columns):
    html = """
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            """
    html += "".join(f"<th>{header}</th>" for header in headers)
    html += "</tr>"
    for idx_row, label in enumerate(row_labels):
        html += f"<tr><th>{label}</th>"
        html += f"""<td class="highlight">{columns[0][idx_row]}</td>"""
        html += "".join(f"<td>{column[idx_row]}</td>" for column in columns[1:])
        html += "</tr>"
    html += """
            </tbody>
            </table>
            """
    return html


@error_handler
def get_html(accu_asse):
    html = """
        <head>

        <style type="text/css">
        table {
          table-layout: fixed;
          white-space: normal!important;
          background: #ffffff;
          margin: 4px;
        }
        th {
          word-wrap: break-word;
          padding: 4px 6px;
          background: #efefef;
          valign: middle;
        }
        td {
          word-wrap: break-word;
          padding: 4px 6px;
          background: #efefef;
        }
        .highlight {
          background: #dddddd;
        }
        .th-rows {
          max-width: 120px;
        }
        .empty {
          background: #f9f9f9;
        }
        </style>
        </head>
        <body>
        """
    html += "<h2>Analysis - Accuracy assessment results</h2>"
    html += f"<p><strong>Thematic map:</strong> {os.path.basename(accu_asse.thematic_map.file_path)}</p>"
    sampling_file = os.path.basename(get_source_from(accu_asse.response_design.sampling_layer))
    html += f"<p><strong>Sampling file:</strong> {sampling_file}</p>"
    html += f"<p><strong>Estimator:</strong> {accu_asse.estimator}</p>"
    html += (
        f"<p><strong>Response design state:</strong> {accu_asse.response_design.total_labeled}"
        f"/{accu_asse.response_design.num_points} samples labeled</p>"
    )

    estimates = get_estimates(accu_asse) if has_samples(accu_asse) else None

    for warning in get_report_warnings(accu_asse, estimates):
        html += (
            "<p style='color:black;background-color:#ffc53a;white-space:pre-wrap;padding:4px'>"
            "<strong>Warning!</strong><br/>" + warning.replace("\n", "<br/>") + "</p>"
        )
    if estimates is None:
        html += "<p>There are no labeled samples inside the thematic map to compute the accuracy assessment.</p>"
        html += "</body>"
        return html

    values = accu_asse.values
    labels = ["{} ({})".format(value, accu_asse.labels.get(str(value), "-")) for value in values]
    weighted = accu_asse.estimator != estimators.SIMPLE
    total_area = estimates.total_pixels * accu_asse.pixel_area_value
    error_matrix = estimates.error_matrix.astype(int)

    ###########################################################################
    # #### 1) Error matrix

    class_areas = [
        rf(estimates.pixel_counts[i] * accu_asse.pixel_area_value) if estimates.in_population[i] else "-"
        for i in range(len(values))
    ]
    weights = [rf(estimates.weights[i]) if estimates.in_population[i] else "-" for i in range(len(values))]
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>1) Error matrix:</h3>"
    html += html_matrix(
        labels,
        values,
        error_matrix.tolist(),
        extra_columns=[
            ("Total", error_matrix.sum(axis=1).tolist()),
            ("User's accuracy", [rf(ua) for ua in estimates.users_accuracy]),
            (f"Total class area ({accu_asse.pixel_area_unit})", class_areas),
            ("Wi", weights),
        ],
        bottom_rows=[
            ("Total", error_matrix.sum(axis=0).tolist(), [int(error_matrix.sum()), "", rf(total_area), ""]),
            (
                "Producer's accuracy",
                [rf(pa) for pa in estimates.producers_accuracy],
                ["", rf(estimates.overall_accuracy), "", ""],
            ),
        ],
    )

    ###########################################################################
    # #### 2) Accuracy

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>2) Accuracy:</h3>"
    html += "<h4>Overall:</h4>"
    html += f"""
            <table>
            <tbody>
            <tr>
            <td><strong>Overall Accuracy</strong></td>
            <td><strong>Standard error</strong></td>
            </tr>
            <tr>
            <td class="highlight">{rf(estimates.overall_accuracy)}</td>
            <td>{rf(estimates.overall_accuracy_se)}</td>
            </tr>
            </tbody>
            </table>
            """
    html += "<h4>User:</h4>"
    html += html_accuracy_table(
        ["User's accuracy", "Standard error"],
        labels,
        [[rf(v) for v in estimates.users_accuracy], [rf(v) for v in estimates.users_accuracy_se]],
    )
    html += "<h4>Producer:</h4>"
    html += html_accuracy_table(
        ["Producer's accuracy", "Standard error"],
        labels,
        [[rf(v) for v in estimates.producers_accuracy], [rf(v) for v in estimates.producers_accuracy_se]],
    )

    # #### 2b) Accuracy matrix of estimated area proportion

    if accu_asse.estimator == estimators.STRATIFIED:
        proportions = estimates.proportions
        row_sums = proportions.sum(axis=1)
        col_sums = proportions.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            user_matrix = np.where(row_sums[:, None] > 0, proportions / row_sums[:, None], 0)
            producer_matrix = np.where(col_sums[None, :] > 0, proportions / col_sums[None, :], 0)
        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>2b) Accuracy matrix of estimated area proportion:</h3>"
        html += "<h4>User:</h4>"
        html += html_matrix(labels, values, [[rf_nonzero(t) for t in row] for row in user_matrix])
        html += "<h4>Producer:</h4>"
        html += html_matrix(labels, values, [[rf_nonzero(t) for t in row] for row in producer_matrix])

    if weighted:
        #######################################################################
        # #### 3) Error matrix of estimated area proportion

        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>3) Error matrix of estimated area proportion:</h3>"
        html += html_matrix(
            labels,
            values,
            [[rf_nonzero(t) for t in row] for row in estimates.proportions],
            extra_columns=[("Wi", [rf_nonzero(t) for t in estimates.proportions.sum(axis=1)])],
            bottom_rows=[("total", [rf(t) for t in estimates.area_proportions], [""])],
        )

        #######################################################################
        # #### 4) Quadratic error matrix of estimated area proportion

        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>4) Quadratic error matrix of estimated area proportion:</h3>"
        html += (
            "<p>Contribution of each stratum (map class) to the variance of the estimated area proportion; "
            "the total row is the standard error (square root of the column sum).</p>"
        )
        html += html_matrix(
            labels,
            values,
            [[rsig(t) for t in row] for row in estimates.variance_contributions],
            bottom_rows=[("total (standard error)", [rf(t) for t in estimates.area_proportions_se], [])],
        )

    ###########################################################################
    # #### 3/5) Class area adjusted

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>{}) Class area adjusted:</h3>".format("5" if weighted else "3")
    html += """
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        """
    headers = [
        f"Area adjusted ({accu_asse.pixel_area_unit})",
        "Standard error",
        f"Lower limit (z={accu_asse.z_score})",
        f"Upper limit (z={accu_asse.z_score})",
        "Coefficient of variation",
        "Uncertainty",
    ]
    html += "".join(f"<th>{header}</th>" for header in headers)
    html += "</tr>"
    for row in get_class_area_adjusted(accu_asse, estimates):
        label, area, error, lower_limit, upper_limit, cv, uncertainty = row
        html += f"<tr><th>{label}</th>"
        html += f"<td>{rf(area)}</td><td>{rf(error)}</td><td>{rf(lower_limit)}</td><td>{rf(upper_limit)}</td>"
        html += f"<td>{percentage(cv)}</td><td>{percentage(uncertainty)}</td>"
        html += "</tr>"
    html += f"""
        <tr>
          <th>total</th>
          <td>{rf(total_area)}</td>
          <td class="empty"></td>
          <td class="empty"></td>
          <td class="empty"></td>
          <td class="empty"></td>
          <td class="empty"></td>
        </tr>
        </tbody>
        </table>
        """

    ###########################################################################
    # #### Methods

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h4>Notes:</h4><ul>"
    html += "".join(f"<li>{note}</li>" for note in METHODS_NOTES[accu_asse.estimator] + METHODS_COMMON_NOTES)
    html += "</ul>"

    html += """
        </body>
        """

    return html


def get_class_area_adjusted(accu_asse, estimates):
    """Rows of (label, area, standard error, lower limit, upper limit, CV %, uncertainty %)"""
    total_area = estimates.total_pixels * accu_asse.pixel_area_value
    rows = []
    for idx, value in enumerate(estimates.values):
        area = estimates.area_proportions[idx] * total_area
        error = estimates.area_proportions_se[idx] * total_area
        # the limits are unknown (NaN) when the standard error can't be estimated
        lower_limit = max(area - accu_asse.z_score * error, 0) if not np.isnan(error) else np.nan
        upper_limit = area + accu_asse.z_score * error
        cv = error / area * 100 if area > 0 else np.nan
        uncertainty = accu_asse.z_score * error / area * 100 if area > 0 else np.nan
        label = "{} ({})".format(value, accu_asse.labels.get(str(value), "-"))
        rows.append((label, area, error, lower_limit, upper_limit, cv, uncertainty))
    return rows


@error_handler
def export_to_csv(accu_asse, file_out, csv_separator, csv_decimal_separator):
    if accu_asse.values is None:
        raise ValueError("There are no results to export, the accuracy assessment was not computed")
    csv_rows = []
    csv_rows.append(["Analysis - Accuracy assessment results"])
    csv_rows.append([])
    csv_rows.append(["Thematic map:"])
    csv_rows.append([os.path.basename(accu_asse.thematic_map.file_path)])
    csv_rows.append([])
    csv_rows.append(["Sampling file:"])
    csv_rows.append([os.path.basename(get_source_from(accu_asse.response_design.sampling_layer))])
    csv_rows.append([])
    csv_rows.append(["Estimator:"])
    csv_rows.append([accu_asse.estimator])
    csv_rows.append([])
    csv_rows.append(["Response design state:"])
    csv_rows.append(
        [f"{accu_asse.response_design.total_labeled}/{accu_asse.response_design.num_points} samples labeled"]
    )

    estimates = get_estimates(accu_asse) if has_samples(accu_asse) else None
    for warning in get_report_warnings(accu_asse, estimates):
        csv_rows.append([])
        csv_rows.append(["Warning:"])
        csv_rows += [[line.strip()] for line in warning.split("\n")]

    if estimates is not None:
        csv_rows += get_csv_results_rows(accu_asse, estimates)

    with open(file_out, "w", newline="", encoding="utf-8") as csvfile:
        csv_w = csv.writer(csvfile, delimiter=str(csv_separator))
        # replace with the user define decimal separator
        if csv_decimal_separator != ".":
            for idx, row in enumerate(csv_rows):
                csv_rows[idx] = [
                    str(item).replace(".", csv_decimal_separator) if isinstance(item, float) else item for item in row
                ]
        csv_w.writerows(csv_rows)
    return True


def get_csv_results_rows(accu_asse, estimates):
    values = accu_asse.values
    labels = ["{} ({})".format(value, accu_asse.labels.get(str(value), "-")) for value in values]
    weighted = accu_asse.estimator != estimators.SIMPLE
    total_area = estimates.total_pixels * accu_asse.pixel_area_value
    error_matrix = estimates.error_matrix.astype(int)

    def matrix_rows(matrix_cells):
        rows = []
        for idx_row, value in enumerate(values):
            rows.append(["Thematic map" if idx_row == 0 else "", value, *matrix_cells[idx_row]])
        return rows

    csv_rows = []

    # #### 1) Error matrix
    csv_rows.append([])
    csv_rows.append(["1) Error matrix:"])
    csv_rows.append(["", "", "Validation"])
    csv_rows.append(
        ["", "", *labels, "Total", "User's accuracy", f"Total class area ({accu_asse.pixel_area_unit})", "Wi"]
    )
    for idx_row, row in enumerate(matrix_rows(error_matrix.tolist())):
        in_population = estimates.in_population[idx_row]
        csv_rows.append(
            [
                *row,
                int(error_matrix[idx_row].sum()),
                rf(estimates.users_accuracy[idx_row]),
                rf(estimates.pixel_counts[idx_row] * accu_asse.pixel_area_value) if in_population else "-",
                rf(estimates.weights[idx_row]) if in_population else "-",
            ]
        )
    csv_rows.append(["", "total", *error_matrix.sum(axis=0).tolist(), int(error_matrix.sum()), "", rf(total_area)])
    producers_accuracy = [rf(pa) for pa in estimates.producers_accuracy]
    csv_rows.append(["", "Producer's accuracy", *producers_accuracy, "", rf(estimates.overall_accuracy)])

    # #### 2) Accuracy
    csv_rows.append([])
    csv_rows.append(["2) Accuracy:"])
    csv_rows.append([])
    csv_rows.append(["Overall:"])
    csv_rows.append(["", "Overall Accuracy", "Standard error"])
    csv_rows.append(["", rf(estimates.overall_accuracy), rf(estimates.overall_accuracy_se)])
    csv_rows.append([])
    csv_rows.append(["User:"])
    csv_rows.append(["", "User's Accuracy", "Standard error"])
    for idx, label in enumerate(labels):
        csv_rows.append([label, rf(estimates.users_accuracy[idx]), rf(estimates.users_accuracy_se[idx])])
    csv_rows.append([])
    csv_rows.append(["Producer:"])
    csv_rows.append(["", "Producer's Accuracy", "Standard error"])
    for idx, label in enumerate(labels):
        csv_rows.append([label, rf(estimates.producers_accuracy[idx]), rf(estimates.producers_accuracy_se[idx])])

    # #### 2b) Accuracy matrix of estimated area proportion
    if accu_asse.estimator == estimators.STRATIFIED:
        proportions = estimates.proportions
        row_sums = proportions.sum(axis=1)
        col_sums = proportions.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            user_matrix = np.where(row_sums[:, None] > 0, proportions / row_sums[:, None], 0)
            producer_matrix = np.where(col_sums[None, :] > 0, proportions / col_sums[None, :], 0)
        csv_rows.append([])
        csv_rows.append(["2b) Accuracy matrix of estimated area proportion:"])
        csv_rows.append([])
        csv_rows.append(["User:"])
        csv_rows.append(["", "", "Validation"])
        csv_rows.append(["", "", *labels])
        csv_rows += matrix_rows([[rf_nonzero(t) for t in row] for row in user_matrix])
        csv_rows.append([])
        csv_rows.append(["Producer:"])
        csv_rows.append(["", "", "Validation"])
        csv_rows.append(["", "", *labels])
        csv_rows += matrix_rows([[rf_nonzero(t) for t in row] for row in producer_matrix])

    if weighted:
        # #### 3) Error matrix of estimated area proportion
        csv_rows.append([])
        csv_rows.append(["3) Error matrix of estimated area proportion:"])
        csv_rows.append(["", "", "Validation"])
        csv_rows.append(["", "", *labels, "Wi"])
        row_weights = estimates.proportions.sum(axis=1)
        for idx_row, row in enumerate(matrix_rows([[rf_nonzero(t) for t in r] for r in estimates.proportions])):
            csv_rows.append([*row, rf_nonzero(row_weights[idx_row])])
        csv_rows.append(["", "total", *[rf(t) for t in estimates.area_proportions]])

        # #### 4) Quadratic error matrix of estimated area proportion
        csv_rows.append([])
        csv_rows.append(["4) Quadratic error matrix of estimated area proportion:"])
        csv_rows.append(["", "", "Validation"])
        csv_rows.append(["", "", *labels])
        csv_rows += matrix_rows([[rsig(t) for t in row] for row in estimates.variance_contributions])
        csv_rows.append(["", "total (standard error)", *[rf(t) for t in estimates.area_proportions_se]])

    # #### 3/5) Class area adjusted
    csv_rows.append([])
    csv_rows.append(["{}) Class area adjusted:".format("5" if weighted else "3")])
    csv_rows.append(["", "z score of the confidence limits:", float(accu_asse.z_score)])
    csv_rows.append(
        [
            "",
            f"Area adjusted ({accu_asse.pixel_area_unit})",
            "Standard error",
            "Lower limit",
            "Upper limit",
            "Coefficient of variation (%)",
            "Uncertainty (%)",
        ]
    )
    for label, area, error, lower_limit, upper_limit, cv, uncertainty in get_class_area_adjusted(accu_asse, estimates):
        csv_rows.append([label, rf(area), rf(error), rf(lower_limit), rf(upper_limit), rf(cv, 2), rf(uncertainty, 2)])
    csv_rows.append(["total", rf(total_area)])

    # #### Notes
    csv_rows.append([])
    csv_rows.append(["Notes:"])
    for note in METHODS_NOTES[accu_asse.estimator] + METHODS_COMMON_NOTES:
        csv_rows.append([html_to_text(note)])

    return csv_rows


def html_to_text(text):
    """Plain text of the notes for the csv"""
    for html_code, char in (("&plusmn;", "+/-"), ("&middot;", "*"), ("<sub>", ""), ("</sub>", "")):
        text = text.replace(html_code, char)
    return text
