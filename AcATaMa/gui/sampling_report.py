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
import math
import os
from typing import ClassVar

import numpy as np
from qgis.core import Qgis, QgsUnitTypes
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from AcATaMa.core import estimators
from AcATaMa.core.map import (
    get_map_fingerprint,
    get_source_nodata,
    get_user_nodata_ranges,
    get_values_and_colors_table,
    in_nodata_ranges,
)
from AcATaMa.utils.qgis_utils import get_source_from
from AcATaMa.utils.system_utils import get_save_file_name, output_file_is_OK

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(plugin_folder, "ui", "sampling_report.ui"))


def rf(fv, r=5):
    if np.isnan(fv):
        return "-"
    return round(fv, r)


def get_report_number(value_with_unit):
    """Number of a "<value> <unit>" field of the report, zero if it is not set"""
    try:
        return float(str(value_with_unit).split()[0])
    except (ValueError, IndexError):
        return 0


def get_samples_distribution_table(map_layer, points, area_unit):
    table = {
        "pix_val": [],
        "color": [],
        "num_samples": [],
        "total_pixels": [],
        "total_area": [],
    }

    samples_in_pix_val = {}
    for point in points:
        map_value = map_layer.get_pixel_value_from_pnt(point)
        if map_value not in samples_in_pix_val:
            samples_in_pix_val[map_value] = 0
        samples_in_pix_val[map_value] += 1

    values_and_colors_table = get_values_and_colors_table(map_layer.qgs_layer, map_layer.band, map_layer.nodata)
    pixel_area_base = map_layer.qgs_layer.rasterUnitsPerPixelX() * map_layer.qgs_layer.rasterUnitsPerPixelY()
    pixel_area_value = pixel_area_base * QgsUnitTypes.fromUnitToUnitFactor(
        QgsUnitTypes.distanceToAreaUnit(map_layer.qgs_layer.crs().mapUnits()), area_unit
    )
    # the no data of the layer (also the ranges set by the user) is not a class, its pixels can't be sampled
    source_nodata = get_source_nodata(map_layer.qgs_layer, map_layer.band)
    user_nodata_ranges = get_user_nodata_ranges(map_layer.qgs_layer, map_layer.band)

    for i, pix_val in enumerate(values_and_colors_table["Pixel Value"]):
        if pix_val == source_nodata or in_nodata_ranges(pix_val, user_nodata_ranges):
            continue
        table["pix_val"].append(pix_val)
        table["color"].append(
            [
                values_and_colors_table["Red"][i],
                values_and_colors_table["Green"][i],
                values_and_colors_table["Blue"][i],
                values_and_colors_table["Alpha"][i],
            ]
        )
        table["num_samples"].append(samples_in_pix_val.get(pix_val, 0))
        total_pixels = map_layer.get_total_pixels_by_value(pix_val)
        table["total_pixels"].append(total_pixels)
        table["total_area"].append(total_pixels * pixel_area_value)

    return table


class SamplingReport(QDialog, FORM_CLASS):
    instance_opened = False
    instances: ClassVar[dict] = {}

    def __init__(self, sampling_layer, sampling=None, sampling_conf=None, report=None):
        QDialog.__init__(self)
        self.setupUi(self)
        self.sampling_layer = sampling_layer
        self.sampling = sampling
        self.sampling_conf = sampling_conf
        # CSV export settings (defaults match the csvSeparator/csvDecimal fields in the ui)
        self.settingsWidget.setVisible(False)
        self.csv_separator = self.csvSeparator.text() or ";"
        self.csv_decimal = self.csvDecimal.text() or "."
        self.csvSeparator.textChanged.connect(lambda value: setattr(self, "csv_separator", value))
        self.csvDecimal.textChanged.connect(lambda value: setattr(self, "csv_decimal", value))
        # dialog buttons box: rename Save button and wire it to the CSV export
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Save).setText("Export to CSV")
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.export_to_csv)
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        # fill the area units (available both for fresh samplings and for
        # reports restored from a yaml configuration; in the restored case
        # we can no longer recompute from the raster, but we can still
        # convert the stored area values between units with a factor)
        self.area_unit.clear()
        for area_unit in sorted(Qgis.AreaUnit, key=lambda x: x.value):
            if area_unit == Qgis.AreaUnit.Unknown:
                continue
            self.area_unit.addItem(
                f"{QgsUnitTypes.toString(area_unit)} ({QgsUnitTypes.toAbbreviatedString(area_unit)})"
            )
        self.area_unit.blockSignals(True)
        if sampling:
            self.area_unit.setCurrentIndex(QgsUnitTypes.distanceToAreaUnit(sampling_layer.crs().mapUnits()))
        elif report is not None:
            self.area_unit.setCurrentIndex(report["general"]["area_unit"])
        self.area_unit.blockSignals(False)
        self.area_unit.currentIndexChanged.connect(self.reload)

        if report is not None:
            self.report = report
        else:
            self.generate_sampling_report()

        self.sampling_report.zoomOut()

        SamplingReport.instances[sampling_layer] = self

    def generate_sampling_report(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        thematic_map_table = get_samples_distribution_table(
            self.sampling.thematic_map,
            self.sampling.points.values(),
            Qgis.AreaUnit(self.area_unit.currentIndex()),
        )

        systematic_unit = AcATaMa.dockwidget.sampling_design_window.PointSpacing_SystS.suffix().strip()
        offset_draws = None
        if self.sampling_conf["sampling_type"] == "systematic":

            def systematic_value(value):
                return int(value) if systematic_unit == "pixels" else value

            points_spacing = "{} {}".format(systematic_value(self.sampling_conf["points_spacing"]), systematic_unit)
            initial_inset_x = systematic_value(self.sampling_conf["initial_inset"])
            initial_inset_y = systematic_value(self.sampling_conf.get("initial_inset_y", initial_inset_x))
            if initial_inset_x == initial_inset_y:
                initial_inset = f"{initial_inset_x} {systematic_unit}"
            else:
                initial_inset = f"X: {initial_inset_x}, Y: {initial_inset_y} {systematic_unit}"
            max_xy_offset = "{} {}".format(systematic_value(self.sampling_conf["max_xy_offset"]), systematic_unit)
            if self.sampling_conf["max_xy_offset"] > 0:
                offset_draws = self.sampling_conf.get("offset_draws")
        else:
            points_spacing = initial_inset = max_xy_offset = None

        if self.sampling_conf["random_seed"] is None:
            random_seed = "Auto"
        elif self.sampling_conf.get("random_seed_by_user", True):
            random_seed = self.sampling_conf["random_seed"]
        else:
            random_seed = "{} (automatic)".format(self.sampling_conf["random_seed"])

        def is_thematic_map(map_layer):
            return (map_layer.qgs_layer, map_layer.band) == (
                self.sampling.thematic_map.qgs_layer,
                self.sampling.thematic_map.band,
            )

        def map_name(map_layer):
            if map_layer.qgs_layer == self.sampling.thematic_map.qgs_layer and not is_thematic_map(map_layer):
                return f"{map_layer.qgs_layer.name()} (band {map_layer.band})"
            return map_layer.qgs_layer.name()

        # the fingerprints identify the maps of the sampling in the analysis
        def fingerprint(map_layer):
            return get_map_fingerprint(map_layer.qgs_layer, map_layer.band)

        if self.sampling.post_stratification_map and not is_thematic_map(self.sampling.post_stratification_map):
            post_stratification_table = get_samples_distribution_table(
                self.sampling.post_stratification_map,
                self.sampling.points.values(),
                Qgis.AreaUnit(self.area_unit.currentIndex()),
            )
            post_stratification_map_fingerprint = fingerprint(self.sampling.post_stratification_map)
        else:
            post_stratification_table = None
            post_stratification_map_fingerprint = None

        if self.sampling.sampling_map is not None and not is_thematic_map(self.sampling.sampling_map):
            sampling_map = map_name(self.sampling.sampling_map)
            sampling_map_table = get_samples_distribution_table(
                self.sampling.sampling_map,
                self.sampling.points.values(),
                Qgis.AreaUnit(self.area_unit.currentIndex()),
            )
            sampling_map_fingerprint = fingerprint(self.sampling.sampling_map)
        else:
            sampling_map = None
            sampling_map_table = None
            sampling_map_fingerprint = None

        self.report = {
            "general": {
                "sampling_layer": self.sampling_layer.name(),
                "thematic_map": self.sampling.thematic_map.qgs_layer.name(),
                "thematic_map_band": self.sampling.thematic_map.band,
                "thematic_map_fingerprint": fingerprint(self.sampling.thematic_map),
                # the no data values and ranges of the thematic map, whose pixels could not be sampled
                "thematic_map_nodata": [
                    float(value)
                    for value in (
                        self.sampling.thematic_map.nodata,
                        get_source_nodata(self.sampling.thematic_map.qgs_layer, self.sampling.thematic_map.band),
                    )
                    if value is not None and not math.isnan(value)
                ],
                "thematic_map_nodata_ranges": [
                    list(no_data_range)
                    for no_data_range in get_user_nodata_ranges(
                        self.sampling.thematic_map.qgs_layer, self.sampling.thematic_map.band
                    )
                ],
                "sampling_map": sampling_map,
                "sampling_map_fingerprint": sampling_map_fingerprint,
                "post_stratification_map_fingerprint": post_stratification_map_fingerprint,
                "sampling_type": self.sampling_conf["sampling_type"],
                "stratified_method": self.sampling.sampling_method
                if self.sampling_conf["sampling_type"] == "stratified"
                else None,
                "total_of_samples": self.sampling.samples_generated,
                "points_spacing": points_spacing,
                "initial_inset": initial_inset,
                "initial_inset_mode": self.sampling_conf.get("initial_inset_mode"),
                "max_xy_offset": max_xy_offset,
                "offset_draws": offset_draws,
                "post_stratification_map": map_name(self.sampling.post_stratification_map)
                if self.sampling.post_stratification_map
                else None,
                "post_stratification_classes": self.sampling_conf["classes_selected"]
                if self.sampling.post_stratification_map
                else [],
                "min_distance": "{} {}".format(
                    self.sampling_conf["min_distance"],
                    QgsUnitTypes.toString(self.sampling.thematic_map.qgs_layer.crs().mapUnits()),
                )
                if self.sampling_conf["sampling_type"] in ["simple", "stratified"]
                else None,
                "neighbor_aggregation": self.sampling_conf["neighbor_aggregation"],
                "random_seed": random_seed,
                "area_unit": self.area_unit.currentIndex(),
            },
            "samples": {
                "thematic_map": thematic_map_table,
                "total_of_samples_by_stratum": self.sampling_conf["total_of_samples"]
                if self.sampling_conf["sampling_type"] == "stratified"
                else None,
                "samples_not_in_thematic_map": self.sampling.samples_generated - sum(thematic_map_table["num_samples"]),
                "sampling_map": sampling_map_table,
                "samples_not_in_sampling_map": self.sampling.samples_generated - sum(sampling_map_table["num_samples"])
                if sampling_map_table
                else None,
                "post_stratification": post_stratification_table,
                "samples_not_in_post_stratification": self.sampling.samples_generated
                - sum(post_stratification_table["num_samples"])
                if post_stratification_table
                else None,
            },
        }

    def show(self):
        self.sampling_report.setHtml(self.get_html())
        self.sampling_report.setOpenExternalLinks(True)
        SamplingReport.instance_opened = self

        super().show()

    def reload(self):
        # the report is not generated again from the map layers, which could have changed since the sampling
        # (it records the maps of the sampling), so convert the already-computed total_area values using the
        # unit factor, then update the report's stored area_unit
        old_area_unit = Qgis.AreaUnit(self.report["general"]["area_unit"])
        new_area_unit_index = self.area_unit.currentIndex()
        new_area_unit = Qgis.AreaUnit(new_area_unit_index)
        factor = QgsUnitTypes.fromUnitToUnitFactor(old_area_unit, new_area_unit)
        for table_key in ("thematic_map", "sampling_map", "post_stratification"):
            table = self.report["samples"].get(table_key)
            if table:
                table["total_area"] = [v * factor for v in table["total_area"]]
        self.report["general"]["area_unit"] = new_area_unit_index
        self.sampling_report.setHtml(self.get_html())
        self.sampling_report.setOpenExternalLinks(True)

    def get_html(self):
        sampling_type = {
            "simple": "Simple random sampling",
            "stratified": "Stratified random sampling",
            "systematic": "Systematic random sampling",
        }

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

        html += """
            <h2>Sampling Report</h2>
            <h3>General</h3>
            <table>
                <tr>
                    <th>Sampling Layer</th>
                    <td>{sampling_layer}</td>
                </tr>
                <tr>
                    <th>Thematic Map</th>
                    <td>{thematic_map}</td>
                </tr>
            """.format(
            sampling_layer=self.report["general"]["sampling_layer"], thematic_map=self.report["general"]["thematic_map"]
        )
        # sampling map
        if self.report["general"]["sampling_map"]:
            html += """
                <tr>
                    <th>Sampling Map</th>
                    <td>{sampling_map}</td>
                </tr>
            """.format(sampling_map=self.report["general"]["sampling_map"])

        html += """
                <tr>
                    <th>Sampling Type</th>
                    <td>{sampling_type}</td>
                </tr>
            """.format(sampling_type=sampling_type[self.report["general"]["sampling_type"]])

        if self.report["general"]["sampling_type"] == "stratified":
            html += """
                    <tr>
                        <th>Stratified method</th>
                        <td>{stratified_method}</td>
                    </tr>
                """.format(stratified_method=self.report["general"]["stratified_method"].capitalize())

        html += """
                <tr>
                    <th>Total of Samples</th>
                    <td>{total_of_samples}</td>
                </tr>
            """.format(
            total_of_samples=self.report["general"]["total_of_samples"],
        )

        if self.report["general"]["sampling_type"] == "systematic":
            html += """
                <tr>
                    <th>Points Spacing (XY)</th>
                    <td>{points_spacing}</td>
                </tr>
                <tr>
                    <th>Initial Inset</th>
                    <td>{initial_inset}</td>
                </tr>
                <tr>
                    <th>Max XY Offset</th>
                    <td>{max_xy_offset}</td>
                </tr>
            """.format(
                points_spacing=self.report["general"]["points_spacing"],
                initial_inset=self.report["general"]["initial_inset"],
                max_xy_offset=self.report["general"]["max_xy_offset"],
            )
            if self.report["general"].get("offset_draws"):
                html += """
                    <tr>
                        <th>Draws per Offset Area</th>
                        <td>{offset_draws}</td>
                    </tr>
                """.format(offset_draws=self.report["general"]["offset_draws"])

        if self.report["general"]["sampling_type"] in ["simple", "systematic"]:
            html += """
                    <tr>
                        <th>Post-Stratification Map</th>
                        <td>{post_stratification_map}</td>
                    </tr>
                    <tr>
                        <th>Post-Stratification Classes</th>
                        <td>{post_stratification_classes}</td>
                    </tr>
                """.format(
                post_stratification_map=self.report["general"]["post_stratification_map"],
                post_stratification_classes=", ".join(
                    [str(x) for x in self.report["general"]["post_stratification_classes"]]
                )
                if self.report["general"]["post_stratification_classes"]
                else None,
            )

        if self.report["general"]["sampling_type"] in ["simple", "stratified"]:
            html += """
                    <tr>
                        <th>Min Distance</th>
                        <td>{min_distance}</td>
                    </tr>
                """.format(min_distance=self.report["general"]["min_distance"])

        html += """
                <tr>
                    <th>Neighbor Aggregation</th>
                    <td>{neighbor_aggregation}</td>
                </tr>
                <tr>
                    <th>Random Seed</th>
                    <td>{random_seed}</td>
                </tr>
            </table>
            """.format(
            neighbor_aggregation="{}/{}".format(
                self.report["general"]["neighbor_aggregation"][1], self.report["general"]["neighbor_aggregation"][0]
            )
            if self.report["general"]["neighbor_aggregation"]
            else None,
            random_seed=self.report["general"]["random_seed"],
        )

        html += """
            <h3>Distribution of samples on the thematic map</h3>
            <table>
                <tr>
                    <th>Pix Val</th>
                    <th>Color</th>
                    <th>Num Samples</th>
                    <th>Total Pixels</th>
                    <th>Total Area ({area_unit})</th>
                </tr>
        """.format(area_unit=QgsUnitTypes.toAbbreviatedString(Qgis.AreaUnit(self.report["general"]["area_unit"])))
        for i, pix_val in enumerate(self.report["samples"]["thematic_map"]["pix_val"]):
            html += """
                <tr>
                    <td>{pix_val}</td>
                    <td style="background-color: rgb({r}, {g}, {b})"></td>
                    <td>{num_samples}</td>
                    <td>{total_pixels}</td>
                    <td>{total_area}</td>
                </tr>
            """.format(
                pix_val=pix_val,
                r=self.report["samples"]["thematic_map"]["color"][i][0],
                g=self.report["samples"]["thematic_map"]["color"][i][1],
                b=self.report["samples"]["thematic_map"]["color"][i][2],
                num_samples=self.report["samples"]["thematic_map"]["num_samples"][i],
                total_pixels=self.report["samples"]["thematic_map"]["total_pixels"][i],
                total_area=rf(self.report["samples"]["thematic_map"]["total_area"][i]),
            )
        html += """</table>"""
        if self.report["samples"]["samples_not_in_thematic_map"] > 0:
            html += """
                <h4>Samples not in the thematic map *</h4>
                <table>
                    <tr>
                        <th>Num Samples</th>
                    </tr>
                    <tr>
                        <td>{num_samples}</td>
                    </tr>
                </table>
                <i>* Samples in no-data or outside</i>
            """.format(num_samples=self.report["samples"]["samples_not_in_thematic_map"])

        if self.report["samples"]["sampling_map"]:
            html += """
                <h3>Distribution of samples on the sampling map</h3>
                <table>
                    <tr>
                        <th>Pix Val</th>
                        <th>Color</th>
                        <th>Num Samples</th>
                        <th>Total Pixels</th>
                        <th>Total Area ({area_unit})</th>
                    </tr>
            """.format(area_unit=QgsUnitTypes.toAbbreviatedString(Qgis.AreaUnit(self.report["general"]["area_unit"])))
            for i, pix_val in enumerate(self.report["samples"]["sampling_map"]["pix_val"]):
                html += """
                    <tr>
                        <td>{pix_val}</td>
                        <td style="background-color: rgb({r}, {g}, {b})"></td>
                        <td>{num_samples}</td>
                        <td>{total_pixels}</td>
                        <td>{total_area}</td>
                    </tr>
                """.format(
                    pix_val=pix_val,
                    r=self.report["samples"]["sampling_map"]["color"][i][0],
                    g=self.report["samples"]["sampling_map"]["color"][i][1],
                    b=self.report["samples"]["sampling_map"]["color"][i][2],
                    num_samples=self.report["samples"]["sampling_map"]["num_samples"][i],
                    total_pixels=self.report["samples"]["sampling_map"]["total_pixels"][i],
                    total_area=rf(self.report["samples"]["sampling_map"]["total_area"][i]),
                )
            html += """</table>"""
            if self.report["samples"]["samples_not_in_sampling_map"] > 0:
                html += """
                    <h4>Samples not in the sampling map *</h4>
                    <table>
                        <tr>
                            <th>Num Samples</th>
                        </tr>
                        <tr>
                            <td>{num_samples}</td>
                        </tr>
                    </table>
                    <i>* Samples in no-data or outside</i>
                """.format(num_samples=self.report["samples"]["samples_not_in_sampling_map"])

        if self.report["samples"]["post_stratification"]:
            html += """
                <h3>Distribution of samples on the post-stratification map</h3>
                <table>
                    <tr>
                        <th>Pix Val</th>
                        <th>Color</th>
                        <th>Num Samples</th>
                        <th>Total Pixels</th>
                        <th>Total Area ({area_unit})</th>
                    </tr>
            """.format(area_unit=QgsUnitTypes.toAbbreviatedString(Qgis.AreaUnit(self.report["general"]["area_unit"])))
            for i, pix_val in enumerate(self.report["samples"]["post_stratification"]["pix_val"]):
                html += """
                    <tr>
                        <td>{pix_val}</td>
                        <td style="background-color: rgb({r}, {g}, {b})"></td>
                        <td>{num_samples}</td>
                        <td>{total_pixels}</td>
                        <td>{total_area}</td>
                    </tr>
                """.format(
                    pix_val=pix_val,
                    r=self.report["samples"]["post_stratification"]["color"][i][0],
                    g=self.report["samples"]["post_stratification"]["color"][i][1],
                    b=self.report["samples"]["post_stratification"]["color"][i][2],
                    num_samples=self.report["samples"]["post_stratification"]["num_samples"][i],
                    total_pixels=self.report["samples"]["post_stratification"]["total_pixels"][i],
                    total_area=rf(self.report["samples"]["post_stratification"]["total_area"][i]),
                )
            html += """</table>"""
            if self.report["samples"]["samples_not_in_post_stratification"] > 0:
                html += """
                    <h4>Samples not in the post-stratification map *</h4>
                    <table>
                        <tr>
                            <th>Num Samples</th>
                        </tr>
                        <tr>
                            <td>{num_samples}</td>
                        </tr>
                    </table>
                    <i>* Samples in no-data or outside</i>
                """.format(num_samples=self.report["samples"]["samples_not_in_post_stratification"])

        ### warning boxes

        # simple num samples mismatch
        if self.sampling_conf is not None and self.report["general"]["sampling_type"] == "simple":
            desired_num_samples = self.sampling_conf["total_of_samples"]
            actual_num_samples = self.report["samples"]["thematic_map"]["num_samples"]
            if desired_num_samples != sum(actual_num_samples):
                html += f"""
                    <br/>
                    <div style="background-color: #fffff3; font-size: 80%">
                        <p style="font-size: 80%; color: #3b3b3b">
                        <span style="font-weight: bold;">Warning: Desired/actual sample count mismatch!</span><br>
                        The number of samples generated does not match the user's desired number of samples. This is
                        generally acceptable, as the actual number may be smaller than the target due to the sampling
                        method and certain restrictions in the sampling conditions. However, if the discrepancy is
                        significantly large, please review the sampling design options.
                        </p>

                        <table>
                            <tr>
                                <th>Desired Samples</th>
                                <th>Actual Samples</th>
                                <th>Difference</th>
                            </tr>
                            <tr>
                                <td>{desired_num_samples}</td>
                                <td>{sum(actual_num_samples)}</td>
                                <td>{desired_num_samples - sum(actual_num_samples)}</td>
                            </tr>
                        </table>
                    </div>
                """

        # stratified num samples mismatch
        if self.sampling_conf is not None and self.report["general"]["sampling_type"] == "stratified":
            strata_table, desired_num_samples_per_stratum, actual_num_samples_per_stratum = self.get_strata_samples()

            # check if the original number of samples set by the user was reached
            if desired_num_samples_per_stratum != actual_num_samples_per_stratum:
                # create a html table with the headers:
                # Pix Val, Color, Desired Num Samples, Actual Num Samples, Difference
                html += """
                    <br/>
                    <div style="background-color: #fffff3; font-size: 80%">
                        <p style="font-size: 80%; color: #3b3b3b">
                        <span style="font-weight: bold;">Warning: Desired/actual sample count mismatch!</span><br>
                        The number of samples generated does not match the user's desired number of samples. This is
                        generally acceptable, as the actual number may be smaller than the target due to the sampling
                        method and certain restrictions in the sampling conditions. However, if the discrepancy is
                        significantly large, please review the sampling design options.
                        </p>

                        <table>
                            <tr>
                                <th>Pix Val</th>
                                <th>Color</th>
                                <th>Desired Samples</th>
                                <th>Actual Samples</th>
                                <th>Difference</th>
                            </tr>
                """

                for i, pix_val in enumerate(strata_table["pix_val"]):
                    html += """
                        <tr>
                            <td>{pix_val}</td>
                            <td style="background-color: rgb({r}, {g}, {b})"></td>
                            <td>{desired_num_samples}</td>
                            <td>{actual_num_samples}</td>
                            <td>{difference}</td>
                        </tr>
                    """.format(
                        pix_val=pix_val,
                        r=strata_table["color"][i][0],
                        g=strata_table["color"][i][1],
                        b=strata_table["color"][i][2],
                        desired_num_samples=desired_num_samples_per_stratum[i],
                        actual_num_samples=actual_num_samples_per_stratum[i],
                        difference=desired_num_samples_per_stratum[i] - actual_num_samples_per_stratum[i],
                    )

                html += """
                        </table>
                    </div>
                """

        # minimum samples in strata
        if self.report["general"]["sampling_type"] == "stratified" or (
            self.report["general"]["sampling_type"] in ["simple", "systematic"]
            and self.report["general"]["post_stratification_map"]
        ):
            if self.report["general"]["sampling_type"] == "stratified":
                if self.report["samples"]["sampling_map"]:
                    table = self.report["samples"]["sampling_map"]
                else:
                    table = self.report["samples"]["thematic_map"]
            else:  # simple or systematic with post-stratification
                if self.report["samples"]["post_stratification"]:
                    table = self.report["samples"]["post_stratification"]
                else:
                    table = self.report["samples"]["thematic_map"]

            if min((num_samples for num_samples in table["num_samples"] if num_samples > 0), default=0) < 30:
                html += """
                    <br/>
                    <div style="background-color: #fffff3;">
                        <p style="font-size: 80%; color: #3b3b3b">
                        <span style="font-weight: bold;">Warning: Check minimum samples in strata!</span><br>
                        Using stratified or post-stratified sampling for map data analysis, land use/land cover
                        classification and similar topics, a minimum sample size of 30 (Van Genderen et al., 1978) or
                        50 (Stehman & Foody, 2019; Hay, 1979) per evaluated stratum is generally recommended as a rule
                        of thumb, it does not guarantee a given precision. Determining the minimum sample size requires
                        consideration of several factors such as data type, the specific research objectives, and the
                        desired level of precision.
                        </p>
                    </div>
                """

        for title, text in self.get_design_warnings():
            html += f"""
                <br/>
                <div style="background-color: #fffff3;">
                    <p style="font-size: 80%; color: #3b3b3b">
                    <span style="font-weight: bold;">Warning: {title}</span><br>
                    {text}
                    </p>
                </div>
            """

        html += """
            </body>
        """

        return html

    def get_strata_samples(self):
        """Table of the strata with the desired and the actual number of samples by stratum"""
        # the sampling map table only exists when it is not the thematic map
        strata_table = self.report["samples"]["sampling_map"] or self.report["samples"]["thematic_map"]
        desired_by_value = dict(
            zip(self.sampling_conf["classes_selected"], self.sampling_conf["total_of_samples"], strict=True)
        )
        desired = [desired_by_value.get(pix_val, 0) for pix_val in strata_table["pix_val"]]
        return strata_table, desired, list(strata_table["num_samples"])

    def get_classes_not_selected(self):
        """Classes with pixels of the post-stratification map that were not selected for sampling, so
        they are not part of the population of the sample"""
        general = self.report["general"]
        if general["sampling_type"] not in ["simple", "systematic"] or not general.get("post_stratification_map"):
            return []
        # the post-stratification table only exists when it is not the thematic map
        table = self.report["samples"].get("post_stratification") or self.report["samples"]["thematic_map"]
        selected = {int(value) for value in general.get("post_stratification_classes") or []}
        return [
            pix_val
            for pix_val, total_pixels in zip(table["pix_val"], table["total_pixels"], strict=True)
            if total_pixels and int(pix_val) not in selected
        ]

    def get_design_warnings(self, estimator=None):
        """Sampling design options that restrict the population or change the inclusion probabilities, with
        their consequences for the estimator of the analysis when it is given"""
        general = self.report["general"]
        warnings = []
        if general["neighbor_aggregation"]:
            if estimator == estimators.SIMPLE:
                consequence = (
                    "the accuracy estimates refer only to that part of the map, and the area estimates, which use the "
                    "total area of the whole map, are not valid"
                )
            elif estimator in [estimators.POST_STRATIFIED, estimators.STRATIFIED]:
                consequence = (
                    "the user's accuracies refer only to that part of the map, while the overall and producer's "
                    "accuracies and the area estimates, which are weighted with the mapped area of the classes in "
                    "the whole map, are not valid, neither for the whole map nor for that part"
                )
            else:
                consequence = (
                    "the accuracy estimated from the sample counts refers only to that part of the map, while the "
                    "area estimates and the estimates weighted with the mapped area of the classes in the whole map "
                    "(stratified and post-stratified estimators) are not valid, neither for the whole map nor for "
                    "that part"
                )
            warnings.append(
                (
                    "Neighbor aggregation restricts the population!",
                    "Only pixels with a homogeneous neighborhood can be sampled, a part of the map whose area is not "
                    f"known, so {consequence}. Accuracy is generally higher there than for the whole map because edge "
                    "and heterogeneous pixels are excluded (Stehman and Foody, 2019).",
                )
            )
        if get_report_number(general["min_distance"]) > 0:
            warnings.append(
                (
                    "Minimum distance between samples",
                    "Discarding the candidate samples closer than the minimum distance to a previous sample makes the "
                    "inclusion probabilities very complicated and they are not derived, so strictly the sample is not "
                    "a probability sample (Stehman and Foody, 2019), while the estimators assume the inclusion "
                    "probabilities of simple (or stratified) random sampling. A minimum distance is not needed for "
                    "design-based inference, whose estimators are unbiased regardless of spatial correlation; the "
                    "smaller it is compared to the mean distance between samples, the fewer candidates are discarded "
                    "and the closer the design is to random sampling. To spread the sample, use systematic sampling.",
                )
            )
        if general["sampling_type"] == "systematic":
            max_xy_offset = get_report_number(general["max_xy_offset"])
            points_spacing = get_report_number(general["points_spacing"])
            if general.get("initial_inset_mode") == "Fixed" and max_xy_offset == 0:
                warnings.append(
                    (
                        "Non-random systematic grid!",
                        "The grid has a fixed initial inset and no random offset, so it is not a probability sample "
                        "and the design-based estimators do not strictly apply. Use a random initial inset.",
                    )
                )
            elif general.get("initial_inset_mode") == "Fixed" and not math.isclose(2 * max_xy_offset, points_spacing):
                warnings.append(
                    (
                        "Offset areas do not tile the map!",
                        "With a fixed initial inset the offset areas must tile the map (max offset of half the points "
                        "spacing): a smaller max offset leaves gaps whose locations can never be selected, and a "
                        "larger one overlaps the offset areas, so the inclusion probabilities are not equal in "
                        "general. Use a random initial inset or a max offset of half the points spacing.",
                    )
                )
            offset_draws = general.get("offset_draws")
            if get_report_number(general["max_xy_offset"]) > 0 and (offset_draws is None or "%" in offset_draws):
                warnings.append(
                    (
                        "Unequal inclusion probabilities!",
                        ("This sample was generated by a previous version of AcATaMa. " if offset_draws is None else "")
                        + "Repeating the random draw in each offset area until a valid pixel is found favors the "
                        "valid pixels of partially valid offset areas (near no data, the map edges or the classes not "
                        "selected), whose inclusion probability is larger than for the rest of the map. The simple "
                        "and post-stratified estimators assume equal inclusion probabilities, use a single draw per "
                        "offset area to fulfill it.",
                    )
                )
        return warnings

    def _build_csv_rows(self):
        """
        Build the list of CSV rows directly from the structured report data.
        This avoids any HTML parsing: the html representation and the csv
        export share the same source (self.report), so they stay in sync.
        """
        sampling_type_label = {
            "simple": "Simple random sampling",
            "stratified": "Stratified random sampling",
            "systematic": "Systematic random sampling",
        }

        general = self.report["general"]
        samples = self.report["samples"]
        area_unit_abbr = QgsUnitTypes.toAbbreviatedString(Qgis.AreaUnit(general["area_unit"]))

        rows = []
        rows.append(["Sampling Report"])
        rows.append([])

        # --- General ---
        rows.append(["General"])
        rows.append(["Sampling Layer", general["sampling_layer"]])
        rows.append(["Thematic Map", general["thematic_map"]])
        if general["sampling_map"]:
            rows.append(["Sampling Map", general["sampling_map"]])
        rows.append(["Sampling Type", sampling_type_label.get(general["sampling_type"], general["sampling_type"])])
        if general["sampling_type"] == "stratified" and general["stratified_method"]:
            rows.append(["Stratified method", general["stratified_method"].capitalize()])
        rows.append(["Total of Samples", general["total_of_samples"]])
        if general["sampling_type"] == "systematic":
            rows.append(["Points Spacing (XY)", general["points_spacing"]])
            rows.append(["Initial Inset", general["initial_inset"]])
            rows.append(["Max XY Offset", general["max_xy_offset"]])
            if general.get("offset_draws"):
                rows.append(["Draws per Offset Area", general["offset_draws"]])
        if general["sampling_type"] in ["simple", "systematic"]:
            rows.append(["Post-Stratification Map", general["post_stratification_map"]])
            post_classes = general["post_stratification_classes"]
            rows.append(
                ["Post-Stratification Classes", ", ".join([str(x) for x in post_classes]) if post_classes else None]
            )
        if general["sampling_type"] in ["simple", "stratified"]:
            rows.append(["Min Distance", general["min_distance"]])
        neighbor_aggregation = general["neighbor_aggregation"]
        rows.append(
            [
                "Neighbor Aggregation",
                f"{neighbor_aggregation[1]}/{neighbor_aggregation[0]}" if neighbor_aggregation else None,
            ]
        )
        rows.append(["Random Seed", general["random_seed"]])
        rows.append([])

        def _distribution_rows(title, table, samples_not_in_map_key, not_in_map_label, include_color=True):
            rows.append([title])
            header = ["Pix Val"]
            if include_color:
                header.append("Color (RGBA)")
            header += ["Num Samples", "Total Pixels", f"Total Area ({area_unit_abbr})"]
            rows.append(header)
            for i, pix_val in enumerate(table["pix_val"]):
                row = [pix_val]
                if include_color:
                    rgba = table["color"][i]
                    row.append(f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]})")
                row += [table["num_samples"][i], table["total_pixels"][i], rf(table["total_area"][i])]
                rows.append(row)
            not_in_map = samples[samples_not_in_map_key]
            if not_in_map is not None and not_in_map > 0:
                rows.append([])
                rows.append([not_in_map_label, not_in_map])
                rows.append(["(Samples in no-data or outside)"])
            rows.append([])

        # --- Distribution of samples on the thematic map ---
        _distribution_rows(
            "Distribution of samples on the thematic map",
            samples["thematic_map"],
            "samples_not_in_thematic_map",
            "Samples not in the thematic map",
            include_color=False,
        )

        # --- Distribution of samples on the sampling map ---
        if samples["sampling_map"]:
            _distribution_rows(
                "Distribution of samples on the sampling map",
                samples["sampling_map"],
                "samples_not_in_sampling_map",
                "Samples not in the sampling map",
            )

        # --- Distribution of samples on the post-stratification map ---
        if samples["post_stratification"]:
            _distribution_rows(
                "Distribution of samples on the post-stratification map",
                samples["post_stratification"],
                "samples_not_in_post_stratification",
                "Samples not in the post-stratification map",
            )

        # --- Desired/actual sample count mismatch warnings ---
        if self.sampling_conf is not None and general["sampling_type"] == "simple":
            desired = self.sampling_conf["total_of_samples"]
            actual = sum(samples["thematic_map"]["num_samples"])
            if desired != actual:
                rows.append(["Warning: Desired/actual sample count mismatch"])
                rows.append(["Desired Samples", "Actual Samples", "Difference"])
                rows.append([desired, actual, desired - actual])
                rows.append([])

        if self.sampling_conf is not None and general["sampling_type"] == "stratified":
            strata_table, desired_per_stratum, actual_per_stratum = self.get_strata_samples()
            if desired_per_stratum != actual_per_stratum:
                rows.append(["Warning: Desired/actual sample count mismatch (per stratum)"])
                rows.append(["Pix Val", "Desired Samples", "Actual Samples", "Difference"])
                for i, pix_val in enumerate(strata_table["pix_val"]):
                    rows.append(
                        [
                            pix_val,
                            desired_per_stratum[i],
                            actual_per_stratum[i],
                            desired_per_stratum[i] - actual_per_stratum[i],
                        ]
                    )
                rows.append([])

        for title, text in self.get_design_warnings():
            rows.append([f"Warning: {title}"])
            rows.append([text])
            rows.append([])

        return rows

    def export_to_csv(self):
        # build a suggested file path based on the sampling file location,
        # falling back to the thematic map folder if the sampling file lives in tmp
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        file_path = get_source_from(AcATaMa.dockwidget.QCBox_SamplingFile)
        path, filename = os.path.split(file_path) if file_path else ("", "")
        if file_path and AcATaMa.dockwidget.tmp_dir in path:
            path = os.path.split(get_source_from(AcATaMa.dockwidget.QCBox_ThematicMap))[0]
        suggested_filename = (
            os.path.splitext(os.path.join(path, filename))[0] + " - sampling report.csv"
            if filename
            else "acatama sampling report.csv"
        )

        output_file = get_save_file_name(
            self, "Export sampling report to csv", suggested_filename, "CSV files (*.csv);;All files (*.*)"
        )

        if not output_file_is_OK(output_file):
            return

        try:
            csv_rows = self._build_csv_rows()
            # normalize cell values: None -> "None", and apply the decimal
            # separator only inside float values (keeping the column
            # delimiter untouched)
            normalized_rows = []
            for row in csv_rows:
                normalized_row = []
                for item in row:
                    if item is None:
                        normalized_row.append("None")
                    elif isinstance(item, float) and self.csv_decimal != ".":
                        normalized_row.append(str(item).replace(".", self.csv_decimal))
                    else:
                        normalized_row.append(item)
                normalized_rows.append(normalized_row)
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                csv_w = csv.writer(csvfile, delimiter=str(self.csv_separator))
                csv_w.writerows(normalized_rows)
            self.MsgBar.pushMessage(
                f'File saved successfully "{os.path.basename(output_file)}"',
                level=Qgis.MessageLevel.Success,
                duration=5,
            )
        except Exception as err:
            self.MsgBar.pushMessage(f"Failed saving the csv file: {err}", level=Qgis.MessageLevel.Critical, duration=10)

    def closeEvent(self, event):
        SamplingReport.instance_opened = False
        event.accept()
        self.close()
