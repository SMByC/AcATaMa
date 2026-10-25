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

import os

from qgis.core import Qgis, QgsUnitTypes
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QApplication, QDialog, QDialogButtonBox
from qgis.utils import iface

from AcATaMa.core import estimators
from AcATaMa.core.map import Map
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.gui import accuracy_assessment_results
from AcATaMa.utils.others_utils import get_nodata_format
from AcATaMa.utils.qgis_utils import get_source_from
from AcATaMa.utils.system_utils import get_save_file_name, output_file_is_OK, wait_process


class Analysis:
    def __init__(self, response_design):
        self.values = None
        self.labels = None
        self.error_matrix = None
        self.samples_outside_the_thematic = None
        self.pixel_area_base = None
        self.pixel_area_value = None
        self.pixel_area_unit = None

        self.response_design = response_design
        self.estimator = None
        self.thematic_map = None
        self.thematic_pixels_count = {}
        self.map_classes_without_samples = {}
        # dialog settings
        self.area_unit = None
        self.z_score = 1.96
        self.csv_separator = ";"
        self.csv_decimal = "."

        self.update_thematic_map()

    def update_thematic_map(self):
        """Use the thematic map, band and nodata currently set in the dockwidget, they can
        change between computations of the same analysis instance"""
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        self.thematic_map = Map(
            file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
            band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
            if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()
            else None,
            nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()),
        )

        # define the base area unit based on the thematic map distance unit
        self.dist_unit = self.thematic_map.qgs_layer.crs().mapUnits()
        if self.dist_unit == Qgis.DistanceUnit.Unknown:
            # thematic map with unknown map unit
            self.dist_unit = Qgis.DistanceUnit.Meters
        self.base_area_unit = QgsUnitTypes.distanceToAreaUnit(self.dist_unit)

    @wait_process
    def compute(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Processing, please wait ...")
        QApplication.processEvents()

        # the results of a previous computation are no longer valid, also if this one fails
        self.values = None
        self.error_matrix = None

        self.update_thematic_map()

        # get labels from labeling buttons
        labels = {}
        for button_config in self.response_design.buttons_config.values():
            labels[button_config["thematic_class"]] = button_config["name"]

        # labeled samples without a valid thematic class can't be paired with the map
        points_labeled = [point for point in self.response_design.points if point.is_labeled]
        invalid_samples = [
            point.sample_id
            for point in points_labeled
            if point.label_id not in self.response_design.buttons_config
            or self.response_design.buttons_config[point.label_id]["thematic_class"] in (None, "")
        ]
        if invalid_samples:
            raise ValueError(
                "The samples with ID {} are labeled with a labeling button that no longer exists or has no "
                "thematic class, fix the labeling buttons or relabel these samples".format(
                    ", ".join(str(sample_id) for sample_id in sorted(invalid_samples))
                )
            )

        # get the labeled thematic map classes and validation values
        thematic_map = []  # map values for the sampling points
        validation = []  # user validation - labeling
        samples_outside_the_thematic = []
        points_ordered = sorted(points_labeled, key=lambda p: p.sample_id)
        for point in points_ordered:
            # response design labeling from the pixel values in the thematic map
            thematic_map_in_sample = self.thematic_map.get_pixel_value_from_pnt(point.QgsPnt)
            if thematic_map_in_sample is None or int(thematic_map_in_sample) == self.thematic_map.nodata:
                samples_outside_the_thematic.append(point)
                continue
            thematic_map.append(int(thematic_map_in_sample))
            # thematic classes used in buttons
            validation_in_sample = self.response_design.buttons_config[point.label_id]["thematic_class"]
            validation.append(int(validation_in_sample))

        # the population of the simple estimator is the whole thematic map, so its map classes without
        # samples are included, while the (post-)stratified estimators exclude the strata without samples
        mapped_classes = self.thematic_map.get_pixel_counts()
        sampled_classes = set(thematic_map)
        self.map_classes_without_samples = {
            value: count for value, count in sorted(mapped_classes.items()) if value not in sampled_classes
        }
        # all unique and sorted values
        values = sampled_classes | set(validation)
        if self.estimator == estimators.SIMPLE:
            values |= set(mapped_classes)
        values = sorted(values)
        # Construct a value->index dictionary
        indices = {val: i for (i, val) in enumerate(values)}

        # calculate the error/confusion matrix
        # https://github.com/nltk/nltk/blob/develop/nltk/metrics/confusionmatrix.py
        #
        #                validation
        #     |    | L1 | L2 | L3 | L4 |
        #   m | L1 |    |    |    |    |
        #   a | L2 |    |    |    |    |
        #   p | L3 |    |    |    |    |
        #     | L4 |    |    |    |    |
        #
        error_matrix = [[0 for column in values] for row in values]
        for thematic_map_in_sample, validation_in_sample in zip(thematic_map, validation, strict=True):
            error_matrix[indices[thematic_map_in_sample]][indices[validation_in_sample]] += 1

        # the total number of pixels in the thematic map by each class (zero for the classes only used as
        # labels and for the nodata value)
        self.thematic_pixels_count = {value: mapped_classes.get(value, 0) for value in values}

        # check that the estimator can be computed with these data before setting the results
        if any(any(row) for row in error_matrix):
            estimators.estimate(
                error_matrix, [self.thematic_pixels_count[value] for value in values], self.estimator, values
            )

        # values necessary for results
        self.values = values
        self.labels = labels
        self.error_matrix = error_matrix
        self.samples_outside_the_thematic = samples_outside_the_thematic
        # set area by pixel
        self.pixel_area_base = (
            self.thematic_map.qgs_layer.rasterUnitsPerPixelX() * self.thematic_map.qgs_layer.rasterUnitsPerPixelY()
        )
        self.pixel_area_value = self.pixel_area_base * QgsUnitTypes.fromUnitToUnitFactor(
            self.base_area_unit, self.area_unit
        )
        self.pixel_area_unit = QgsUnitTypes.toAbbreviatedString(self.area_unit)
        return True


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(plugin_folder, "ui", "accuracy_assessment_window.ui"))


class AccuracyAssessmentWindow(QDialog, FORM_CLASS):
    is_opened = False

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        # dialog buttons box
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Save).setText("Export to CSV")
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.export_to_csv)
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.settingsWidget.setVisible(False)

        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()

        # get AccuracyAssessment or init new instance
        if sampling_layer:
            # sampling file valid
            if sampling_layer in ResponseDesign.instances:
                # response design exists for this file
                response_design = ResponseDesign.instances[sampling_layer]
                if response_design.analysis:
                    self.analysis = response_design.analysis
                    # restore config to window
                    self.z_score.setValue(self.analysis.z_score)
                    self.csvSeparator.setText(self.analysis.csv_separator)
                    self.csvDecimal.setText(self.analysis.csv_decimal)
                else:
                    self.analysis = Analysis(response_design)
                    response_design.analysis = self.analysis

        # fill the area units
        self.area_unit.clear()
        for area_unit in sorted(Qgis.AreaUnit, key=lambda x: x.value):
            if area_unit == Qgis.AreaUnit.Unknown:
                continue
            self.area_unit.addItem(
                f"{QgsUnitTypes.toString(area_unit)} ({QgsUnitTypes.toAbbreviatedString(area_unit)})"
            )
        # set the area unit saved or based on the sampling file by default
        if self.analysis.area_unit is not None:
            self.area_unit.setCurrentIndex(self.analysis.area_unit)
        else:
            self.analysis.area_unit = QgsUnitTypes.distanceToAreaUnit(self.analysis.dist_unit)
            self.area_unit.setCurrentIndex(self.analysis.area_unit)
            # thematic map with unknown map unit
            if self.analysis.thematic_map.qgs_layer.crs().mapUnits() == Qgis.DistanceUnit.Unknown:
                self.MsgBar.pushMessage(
                    f'The thematic map "{self.analysis.thematic_map.qgs_layer.name()}" does not have a valid map unit, '
                    f'considering "{QgsUnitTypes.toString(self.analysis.dist_unit)}" as the base unit!',
                    level=Qgis.MessageLevel.Warning,
                    duration=0,
                )

        self.area_unit.currentIndexChanged.connect(lambda: self.reload(msg_bar=False))
        self.z_score.valueChanged.connect(lambda: self.reload(msg_bar=False))
        self.csvSeparator.textChanged.connect(lambda value: setattr(self.analysis, "csv_separator", value))
        self.csvDecimal.textChanged.connect(lambda value: setattr(self.analysis, "csv_decimal", value))
        self.reloadButton.clicked.connect(lambda: self.reload(msg_bar=True))

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        # first check
        if self.analysis.response_design.total_labeled == 0:
            iface.messageBar().pushMessage(
                "AcATaMa",
                "The accuracy assessment needs at least one sample labeled",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return

        # first, set the estimator for accuracy assessment from dropdown selected
        self.analysis.estimator = AcATaMa.dockwidget.QCBox_SamplingEstimator.currentText()
        # second, compute the accuracy assessment
        if not self.analysis.compute():
            AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Compute the accuracy assessment")
            return
        AccuracyAssessmentWindow.is_opened = True
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.analysis))
        self.ResultsHTML.zoomOut()

        AcATaMa.dockwidget.QGBox_ThematicMap.setDisabled(True)
        AcATaMa.dockwidget.QGBox_SamplingDesign.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        super().show()

    def reload(self, msg_bar=True):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        # set adjust variables from window
        self.analysis.z_score = self.z_score.value()
        self.analysis.area_unit = Qgis.AreaUnit(self.area_unit.currentIndex())
        # first compute the accuracy assessment
        computed = self.analysis.compute()
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        if not computed:
            # don't keep showing the results of a previous computation
            self.ResultsHTML.setHtml(
                "<p>The accuracy assessment could not be computed, fix the error reported and reload.</p>"
            )
            return
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.analysis))
        if msg_bar:
            self.MsgBar.pushMessage(
                f"Reload successfully from response design state for"
                f' "{AcATaMa.dockwidget.QCBox_SamplingFile.currentText()}"',
                level=Qgis.MessageLevel.Success,
                duration=5,
            )

    def export_to_csv(self):
        # get file path to suggest where to save but not in tmp directory
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        if self.analysis.values is None:
            self.MsgBar.pushMessage(
                "There are no results to export, the accuracy assessment could not be computed",
                level=Qgis.MessageLevel.Warning,
                duration=10,
            )
            return

        file_path = get_source_from(AcATaMa.dockwidget.QCBox_SamplingFile)
        path, filename = os.path.split(file_path)
        if AcATaMa.dockwidget.tmp_dir in path:
            path = os.path.split(get_source_from(AcATaMa.dockwidget.QCBox_ThematicMap))[0]
        suggested_filename = (
            os.path.splitext(os.path.join(path, filename))[0] + " - results.csv" if filename else "acatama results.csv"
        )

        output_file = get_save_file_name(
            self, "Export accuracy assessment results to csv", suggested_filename, "CSV files (*.csv);;All files (*.*)"
        )

        if output_file_is_OK(output_file):
            try:
                # the errors are reported by the export function, that returns None
                if accuracy_assessment_results.export_to_csv(
                    self.analysis, output_file, self.analysis.csv_separator, self.analysis.csv_decimal
                ):
                    self.MsgBar.pushMessage(
                        f'File saved successfully "{os.path.basename(output_file)}"',
                        level=Qgis.MessageLevel.Success,
                        duration=5,
                    )
            except Exception as err:
                self.MsgBar.pushMessage(
                    f"Failed saving the csv file: {err}", level=Qgis.MessageLevel.Critical, duration=10
                )

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the accuracy assessment windows
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        from AcATaMa.gui.response_design_window import ResponseDesignWindow
        from AcATaMa.gui.sampling_design_window import SamplingDesignWindow

        if not SamplingDesignWindow.is_opened and not ResponseDesignWindow.is_opened:
            AcATaMa.dockwidget.QGBox_ThematicMap.setEnabled(True)
        if not ResponseDesignWindow.is_opened:
            AcATaMa.dockwidget.QGBox_SamplingDesign.setEnabled(True)
        AccuracyAssessmentWindow.is_opened = False
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Compute the accuracy assessment")
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super().reject()
