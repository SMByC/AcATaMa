# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2024 by Xavier C. Llano, SMByC
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
import os
import numpy as np

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsUnitTypes

from AcATaMa.core.map import get_values_and_colors_table

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'sampling_report.ui'))

def rf(fv, r=5):
    if np.isnan(fv):
        return "-"
    return round(fv, r)

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
        QgsUnitTypes.distanceToAreaUnit(map_layer.qgs_layer.crs().mapUnits()), area_unit)

    for i, pix_val in enumerate(values_and_colors_table["Pixel Value"]):
        table["pix_val"].append(pix_val)
        table["color"].append([values_and_colors_table["Red"][i],
                               values_and_colors_table["Green"][i],
                               values_and_colors_table["Blue"][i],
                               values_and_colors_table["Alpha"][i]])
        table["num_samples"].append(samples_in_pix_val[pix_val] if pix_val in samples_in_pix_val else 0)
        total_pixels = map_layer.get_total_pixels_by_value(pix_val)
        table["total_pixels"].append(total_pixels)
        table["total_area"].append(total_pixels * pixel_area_value)

    return table


class SamplingReport(QDialog, FORM_CLASS):
    instance_opened = False
    instances = {}

    def __init__(self, sampling_layer, sampling=None, sampling_conf=None, report=None):
        QDialog.__init__(self)
        self.setupUi(self)
        self.sampling_layer = sampling_layer
        self.sampling = sampling
        self.sampling_conf = sampling_conf
        # fill the area units
        if sampling:
            self.area_unit.clear()
            for area_unit in sorted(QgsUnitTypes.AreaUnit, key=lambda x: x.value):
                self.area_unit.addItem("{} ({})".format(QgsUnitTypes.toString(area_unit),
                                                        QgsUnitTypes.toAbbreviatedString(area_unit)))
            self.area_unit.currentIndexChanged.connect(self.reload)
            self.area_unit.setCurrentIndex(QgsUnitTypes.distanceToAreaUnit(sampling_layer.crs().mapUnits()))
        else:
            self.area_unit.hide()

        if report is not None:
            self.report = report
        else:
            self.generate_sampling_report()

        self.sampling_report.zoomOut()

        SamplingReport.instances[sampling_layer] = self

    def generate_sampling_report(self):

        thematic_map_table = \
            get_samples_distribution_table(self.sampling.thematic_map,
                                           self.sampling.points.values(),
                                           QgsUnitTypes.AreaUnit(self.area_unit.currentIndex()))

        if self.sampling.post_stratification_map and self.sampling.thematic_map.qgs_layer != self.sampling.post_stratification_map.qgs_layer:
            post_stratification_table = \
                get_samples_distribution_table(self.sampling.post_stratification_map,
                                               self.sampling.points.values(),
                                               QgsUnitTypes.AreaUnit(self.area_unit.currentIndex()))
        else:
            post_stratification_table = None

        self.report = {
            "general": {
                "sampling_layer": self.sampling_layer.name(),
                "thematic_map": self.sampling.thematic_map.qgs_layer.name(),
                "total_of_samples": self.sampling.samples_generated,
                "sampling_type": self.sampling_conf["sampling_type"],
                "min_distance": self.sampling_conf["min_distance"] if self.sampling_conf["sampling_type"] in ["simple", "stratified"] else None,
                "points_spacing": self.sampling_conf["points_spacing"] if self.sampling_conf["sampling_type"] == "systematic" else None,
                "initial_inset": self.sampling_conf["initial_inset"] if self.sampling_conf["sampling_type"] == "systematic" else None,
                "max_xy_offset": self.sampling_conf["max_xy_offset"] if self.sampling_conf["sampling_type"] == "systematic" else None,
                "post_stratification_map": self.sampling.post_stratification_map.qgs_layer.name() if self.sampling.post_stratification_map else None,
                "post_stratification_classes": self.sampling_conf["classes_selected"] if self.sampling.post_stratification_map else None,
                "stratified_method": self.sampling.sampling_method if self.sampling_conf["sampling_type"] == "stratified" else None,
                "neighbor_aggregation": self.sampling_conf["neighbor_aggregation"],
                "random_seed": self.sampling_conf["random_seed"] if self.sampling_conf["random_seed"] is not None else "Auto",
                "area_unit": self.area_unit.currentIndex(),
            },
            "stats": {  # TODO
                "mean_distance": 0,
                "density": 0
            },
            "samples": {
                "thematic_map": thematic_map_table,
                "samples_not_in_thematic_map":
                    self.sampling.samples_generated - sum(thematic_map_table["num_samples"]),
                "post_stratification": post_stratification_table,
                "samples_not_in_post_stratification":
                    self.sampling.samples_generated - sum(post_stratification_table["num_samples"])
                    if post_stratification_table else None
            }
        }

    def show(self):
        self.sampling_report.setHtml(self.get_html())
        self.sampling_report.setOpenExternalLinks(True)
        SamplingReport.instance_opened = self

        super(SamplingReport, self).show()

    def reload(self):
        if not self.sampling:
            return
        self.generate_sampling_report()
        self.sampling_report.setHtml(self.get_html())
        self.sampling_report.setOpenExternalLinks(True)

    def get_html(self):
        sampling_type = {"simple": "Simple random sampling", "stratified": "Stratified random sampling",
                         "systematic": "Systematic random sampling"}

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
                <tr>
                    <th>Total of Samples</th>
                    <td>{total_of_samples}</td>
                </tr>
                <tr>
                    <th>Sampling Type</th>
                    <td>{sampling_type}</td>
                </tr>
            """.format(sampling_layer=self.report["general"]["sampling_layer"],
                       thematic_map=self.report["general"]["thematic_map"],
                       total_of_samples=self.report["general"]["total_of_samples"],
                       sampling_type=sampling_type[self.report["general"]["sampling_type"]])

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
            """.format(points_spacing=rf(self.report["general"]["points_spacing"]),
                       initial_inset=rf(self.report["general"]["initial_inset"]),
                       max_xy_offset=rf(self.report["general"]["max_xy_offset"]))
        else:
            html += """
                <tr>
                    <th>Min Distance</th>
                    <td>{min_distance}</td>
                </tr>
            """.format(min_distance=self.report["general"]["min_distance"])

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
                """.format(post_stratification_map=self.report["general"]["post_stratification_map"],
                           post_stratification_classes=self.report["general"]["post_stratification_classes"])

        if self.report["general"]["sampling_type"] == "stratified":
            html += """
                    <tr>
                        <th>Stratified method</th>
                        <td>{stratified_method}</td>
                    </tr>
                """.format(stratified_method=self.report["general"]["stratified_method"].capitalize())

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
            """.format(neighbor_aggregation=self.report["general"]["neighbor_aggregation"],
                       random_seed=self.report["general"]["random_seed"])

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
        """.format(area_unit=QgsUnitTypes.toAbbreviatedString(QgsUnitTypes.AreaUnit(self.report["general"]["area_unit"])))
        for i, pix_val in enumerate(self.report["samples"]["thematic_map"]["pix_val"]):
            html += """
                <tr>
                    <td>{pix_val}</td>
                    <td style="background-color: rgb({r}, {g}, {b})"></td>
                    <td>{num_samples}</td>
                    <td>{total_pixels}</td>
                    <td>{total_area}</td>
                </tr>
            """.format(pix_val=pix_val,
                       r=self.report["samples"]["thematic_map"]["color"][i][0],
                       g=self.report["samples"]["thematic_map"]["color"][i][1],
                       b=self.report["samples"]["thematic_map"]["color"][i][2],
                       num_samples=self.report["samples"]["thematic_map"]["num_samples"][i],
                       total_pixels=self.report["samples"]["thematic_map"]["total_pixels"][i],
                       total_area=rf(self.report["samples"]["thematic_map"]["total_area"][i]))
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
            """.format(area_unit=QgsUnitTypes.toAbbreviatedString(QgsUnitTypes.AreaUnit(self.report["general"]["area_unit"])))
            for i, pix_val in enumerate(self.report["samples"]["post_stratification"]["pix_val"]):
                html += """
                    <tr>
                        <td>{pix_val}</td>
                        <td style="background-color: rgb({r}, {g}, {b})"></td>
                        <td>{num_samples}</td>
                        <td>{total_pixels}</td>
                        <td>{total_area}</td>
                    </tr>
                """.format(pix_val=pix_val,
                           r=self.report["samples"]["post_stratification"]["color"][i][0],
                           g=self.report["samples"]["post_stratification"]["color"][i][1],
                           b=self.report["samples"]["post_stratification"]["color"][i][2],
                           num_samples=self.report["samples"]["post_stratification"]["num_samples"][i],
                           total_pixels=self.report["samples"]["post_stratification"]["total_pixels"][i],
                           total_area=rf(self.report["samples"]["post_stratification"]["total_area"][i]))
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

        html += """
            </body>
        """

        return html

    def export_report(self):
        pass

    def closeEvent(self, event):
        SamplingReport.instance_opened = False
        event.accept()
        self.close()