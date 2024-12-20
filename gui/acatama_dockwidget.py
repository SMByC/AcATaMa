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
import tempfile
import configparser

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog, QDockWidget
from qgis.core import QgsMapLayerProxyModel, Qgis
from qgis.utils import iface

from AcATaMa.core import config
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.core.map import get_nodata_value
from AcATaMa.gui.response_design_window import ResponseDesignWindow
from AcATaMa.gui.response_design_grid_settings import ResponseDesignGridSettings
from AcATaMa.gui.sampling_design_window import SamplingDesignWindow
from AcATaMa.gui.sampling_report import SamplingReport
from AcATaMa.utils.others_utils import set_nodata_format
from AcATaMa.utils.qgis_utils import valid_file_selected_in, load_and_select_filepath_in, get_file_path_of_layer
from AcATaMa.utils.system_utils import error_handler, block_signals_to, output_file_is_OK
from AcATaMa.gui.about_dialog import AboutDialog

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'acatama_dockwidget.ui'))

cfg = configparser.ConfigParser()
cfg.read(os.path.join(plugin_folder, 'metadata.txt'))
VERSION = cfg.get('general', 'version')
HOMEPAGE = cfg.get('general', 'homepage')


class AcATaMaDockWidget(QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()
    dockwidget = None

    def __init__(self, parent=None):
        """Constructor."""
        super(AcATaMaDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.tmp_dir = tempfile.mkdtemp()
        self.sampling_design_window = SamplingDesignWindow()
        self.setup_gui()

        # save instance
        AcATaMaDockWidget.dockwidget = self
        # remember the latest save/restore configuration file
        self.suggested_yml_file = None

    def closeEvent(self, event):
        # first warn before exit if at least exist one response design instance created
        if ResponseDesign.instances:
            quit_msg = "Are you sure you want close the AcATaMa plugin?"
            reply = QMessageBox.question(None, 'Closing the AcATaMa plugin',
                                         quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                # don't close
                event.ignore()
                return
        # close
        self.closingPlugin.emit()
        event.accept()

    def setup_gui(self):
        # ######### plugin info ######### #
        self.about_dialog = AboutDialog()
        self.QPBtn_PluginInfo.setToolTip("AcATaMa v{}".format(VERSION))
        self.QPBtn_PluginInfo.clicked.connect(self.about_dialog.show)

        # ######### load thematic map image ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_ThematicMap.setCurrentIndex(-1)
        self.QCBox_ThematicMap.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the thematic map file
        self.QPBtn_browseThematicMap.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_ThematicMap,
            dialog_title=self.tr("Select the thematic map to evaluate"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        # select and check the thematic map
        self.QCBox_ThematicMap.layerChanged.connect(self.select_thematic_map)
        self.QCBox_band_ThematicMap.currentIndexChanged[int].connect(self.update_thematic_map_band)
        self.nodata_ThematicMap.textChanged.connect(self.update_thematic_map_nodata)

        # ######### Sampling tab ######### #
        # disable sampling window
        self.QPBtn_OpenSamplingDesignWindow.setDisabled(True)
        self.QCBox_SamplingFile.currentIndexChanged[int].connect(lambda index: self.QPBtn_reloadSamplingFile.setEnabled(index > 0))
        # set and update the sampling file status in analysis tab
        self.QCBox_SamplingFile.layerChanged.connect(self.update_analysis_state)
        # show the sampling design window when press the QPBtn_OpenSamplingDesignWindow
        self.QPBtn_OpenSamplingDesignWindow.clicked.connect(self.open_sampling_design_window)
        self.QPBtn_openSamplingReport.setDisabled(True)
        self.QPBtn_openSamplingReport.clicked.connect(self.open_sampling_report)
        self.QCBox_SamplingFile.layerChanged.connect(self.update_sampling_report_state)

        # ######### Response Design tab ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_SamplingFile.setCurrentIndex(-1)
        self.QCBox_SamplingFile.setFilters(QgsMapLayerProxyModel.PointLayer)
        # show the response design state for the sampling file selected
        self.QCBox_SamplingFile.layerChanged.connect(self.update_response_design_state)
        # call to browse the sampling file
        self.QPBtn_browseSamplingFile.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_SamplingFile,
            dialog_title=self.tr("Select the Sampling points file"),
            file_filters=self.tr("Vector files (*.gpkg *.shp);;All files (*.*)")))
        # call to reload sampling file
        self.QPBtn_reloadSamplingFile.clicked.connect(self.reload_sampling_file)
        # call to load and save Acatama state and config
        self.QPBtn_RestoreAcatamaState.clicked.connect(self.file_dialog_restore_acatama_state)
        self.QPBtn_SaveAcatamaState.clicked.connect(self.file_dialog_save_acatama_state)
        # save sampling + labeling
        self.QPBtn_saveSamplingLabeled.clicked.connect(self.file_dialog_save_sampling_labeled)
        # grid settings
        self.response_design_grid_settings = ResponseDesignGridSettings()
        self.QPBtn_GridSettings.clicked.connect(self.response_design_grid_settings.show)
        # disable group box that depends on sampling file
        self.QGBox_ResponseDesign.setDisabled(True)
        # open response design window
        self.QPBtn_OpenResponseDesignWindow.clicked.connect(self.open_response_design_window)

        # ######### Analysis tab ######### #
        # estimator selection action
        self.QCBox_SamplingEstimator.currentIndexChanged[int].connect(self.estimator_selection_action)
        # compute the AA and open the result dialog
        self.QPBtn_ComputeTheAccurasyAssessment.clicked.connect(self.open_accuracy_assessment_results)
        # disable group box that depends on sampling file
        self.QGBox_Analysis.setDisabled(True)

        self.update_response_design_state()

    @pyqtSlot()
    def browser_dialog_to_load_file(self, combo_box, dialog_title, file_filters):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", file_filters)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path)

    @pyqtSlot("QgsMapLayer*")
    def select_thematic_map(self, thematic_map_layer):

        def clear_and_unset_the_thematic_map():
            with block_signals_to(self.QCBox_ThematicMap):
                self.QCBox_ThematicMap.setCurrentIndex(-1)
            self.QCBox_band_ThematicMap.clear()
            self.nodata_ThematicMap.setText("")
            # sampling window
            self.sampling_design_window.clear()
            # unset the thematic classes in response design instance
            sampling_layer = self.QCBox_SamplingFile.currentLayer()
            if sampling_layer and sampling_layer in ResponseDesign.instances:
                ResponseDesign.instances[sampling_layer].with_thematic_classes = False
            # disable sampling window
            self.QPBtn_OpenSamplingDesignWindow.setDisabled(True)
            # updated state of sampling file selected for accuracy assessment tab
            self.update_analysis_state()

        # first check
        if not thematic_map_layer or not valid_file_selected_in(self.QCBox_ThematicMap, "thematic map"):
            clear_and_unset_the_thematic_map()
            return
        # check if thematic map data type is integer or byte
        if thematic_map_layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            clear_and_unset_the_thematic_map()
            iface.messageBar().pushMessage("AcATaMa", "Error, thematic map must be byte or integer as data type.",
                                           level=Qgis.Warning, duration=10)
            return
        # set band count
        self.QCBox_band_ThematicMap.clear()
        self.QCBox_band_ThematicMap.addItems([str(x) for x in range(1, thematic_map_layer.bandCount() + 1)])
        # set nodata value of thematic map in nodata field
        self.nodata_ThematicMap.setText(set_nodata_format(get_nodata_value(thematic_map_layer)))

        # setup the sampling design window by the thematic map selected
        self.sampling_design_window.setup(thematic_map_layer)
        # enable sampling window
        self.QPBtn_OpenSamplingDesignWindow.setEnabled(True)

        # update the labeling status of the sampling layer for the thematic map selected
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer and sampling_layer in ResponseDesign.instances:
            response_design = ResponseDesign.instances[sampling_layer]
            response_design.reload_labeling_status()
            self.update_response_design_state()
            # define if this response_design was made with thematic classes
            if response_design.buttons_config and True in [bc["thematic_class"] is not None and bc["thematic_class"] != ""
                                                           for bc in response_design.buttons_config.values()]:
                response_design.with_thematic_classes = True
            # reload analysis status in accuracy assessment
            self.update_analysis_state()

    @pyqtSlot(int)
    def update_thematic_map_band(self, band_index):
        if band_index == -1:
            return

        thematic_map_layer = self.QCBox_ThematicMap.currentLayer()
        band = int(self.QCBox_band_ThematicMap.currentText())

        # set nodata value of thematic map in nodata field
        self.nodata_ThematicMap.setText(set_nodata_format(get_nodata_value(thematic_map_layer, band)))

        # update the band selected in the sampling design window
        if thematic_map_layer == self.sampling_design_window.QCBox_PostStratMap_SimpRS.currentLayer():
            self.sampling_design_window.QCBox_band_PostStratMap_SimpRS.setCurrentIndex(band_index)
        if thematic_map_layer == self.sampling_design_window.QCBox_SamplingMap_StraRS.currentLayer():
            self.sampling_design_window.QCBox_band_SamplingMap_StraRS.setCurrentIndex(band_index)
        if thematic_map_layer == self.sampling_design_window.QCBox_PostStratMap_SystS.currentLayer():
            self.sampling_design_window.QCBox_band_PostStratMap_SystS.setCurrentIndex(band_index)

    @pyqtSlot(str)
    def update_thematic_map_nodata(self, nodata):
        thematic_map_layer = self.QCBox_ThematicMap.currentLayer()

        # update the nodata value in the sampling design window
        if thematic_map_layer == self.sampling_design_window.QCBox_PostStratMap_SimpRS.currentLayer():
            self.sampling_design_window.nodata_PostStratMap_SimpRS.setText(nodata)
        if thematic_map_layer == self.sampling_design_window.QCBox_SamplingMap_StraRS.currentLayer():
            self.sampling_design_window.nodata_SamplingMap_StraRS.setText(nodata)
        if thematic_map_layer == self.sampling_design_window.QCBox_PostStratMap_SystS.currentLayer():
            self.sampling_design_window.nodata_PostStratMap_SystS.setText(nodata)

    @pyqtSlot("QgsMapLayer*")
    def update_sampling_report_state(self, sampling_layer=None):
        if sampling_layer is None:
            sampling_layer = self.QCBox_SamplingFile.currentLayer()

        if sampling_layer:
            # sampling file valid
            if sampling_layer in SamplingReport.instances:
                self.QPBtn_openSamplingReport.setEnabled(True)
            else:
                self.QPBtn_openSamplingReport.setDisabled(True)

        if SamplingReport.instance_opened:
            SamplingReport.instance_opened.close()


    @pyqtSlot("QgsMapLayer*")
    def update_response_design_state(self, sampling_layer=None):
        if sampling_layer is None:
            sampling_layer = self.QCBox_SamplingFile.currentLayer()

        if sampling_layer:
            # response design state
            if sampling_layer in ResponseDesign.instances:
                response_design = ResponseDesign.instances[sampling_layer]
                self.QPBar_LabelingStatus.setMaximum(response_design.num_points)
                self.QPBar_LabelingStatus.setValue(response_design.total_labeled)
            else:
                count_samples = len(list(sampling_layer.getFeatures()))
                self.QPBar_LabelingStatus.setMaximum(count_samples)
                self.QPBar_LabelingStatus.setValue(0)
            self.QPBar_LabelingStatus.setTextVisible(True)
            # grid settings
            if sampling_layer in ResponseDesign.instances:
                response_design = ResponseDesign.instances[sampling_layer]
                self.response_design_grid_settings.columns.setValue(response_design.grid_columns)
                self.response_design_grid_settings.rows.setValue(response_design.grid_rows)
            else:
                self.response_design_grid_settings.columns.setValue(2)
                self.response_design_grid_settings.rows.setValue(1)
            if not ResponseDesignWindow.is_opened:
                # enable group box that depends on sampling file
                self.QGBox_ResponseDesign.setEnabled(True)
        else:
            # return to default values
            self.QPBar_LabelingStatus.setTextVisible(False)
            self.QPBar_LabelingStatus.setValue(0)
            self.response_design_grid_settings.columns.setValue(2)
            self.response_design_grid_settings.rows.setValue(1)
            # disable group box that depends on sampling file
            self.QGBox_ResponseDesign.setDisabled(True)

        # update state of sampling file selected for accuracy assessment tab
        self.update_analysis_state()

    @pyqtSlot()
    def reload_sampling_file(self):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer:
            if sampling_layer in ResponseDesign.instances:
                response_design = ResponseDesign.instances[sampling_layer]
            else:
                response_design = ResponseDesign(sampling_layer)

            sampling_file_changed = response_design.reload_sampling_file()
            if sampling_file_changed:
                # if sampling report exists, delete it for this sampling layer TODO: update the report
                if sampling_layer in SamplingReport.instances:
                    del SamplingReport.instances[sampling_layer]
                    self.QPBtn_openSamplingReport.setDisabled(True)

            # updated state of sampling file selected for accuracy assessment tab
            self.update_analysis_state()
        else:
            iface.messageBar().pushMessage("AcATaMa", "No sampling file selected",
                                           level=Qgis.Warning, duration=10)


    @pyqtSlot()
    @error_handler
    def file_dialog_restore_acatama_state(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Restore to a previous saved of AcATaMa configuration and state"),
                                                   "", self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))

        if file_path != '' and os.path.isfile(file_path):
            # restore configuration and response design state
            config.restore(file_path)
            self.suggested_yml_file = file_path
            iface.messageBar().pushMessage("AcATaMa", "Configuration and state restored successfully",
                                           level=Qgis.Success, duration=10)

    @pyqtSlot()
    @error_handler
    def file_dialog_save_acatama_state(self):
        if self.suggested_yml_file:
            suggested_filename = self.suggested_yml_file
        elif valid_file_selected_in(self.QCBox_ThematicMap) or valid_file_selected_in(self.QCBox_SamplingFile):
            # get file path to suggest where to save
            if valid_file_selected_in(self.QCBox_ThematicMap):
                file_path = get_file_path_of_layer(self.QCBox_ThematicMap.currentLayer())
            else:
                file_path = get_file_path_of_layer(self.QCBox_SamplingFile.currentLayer())
            path, filename = os.path.split(file_path)
            suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + " - acatama.yml" if filename else "acatama.yml"
        else:
            suggested_filename = "acatama.yml"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save AcATaMa configuration and state"),
                                                  suggested_filename, self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))
        if output_file_is_OK(file_out):
            config.save(file_out)
            self.suggested_yml_file = file_out
            iface.messageBar().pushMessage("AcATaMa", "Configuration file saved successfully",
                                           level=Qgis.Success, duration=10)

    @pyqtSlot()
    @error_handler
    def file_dialog_save_sampling_labeled(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            iface.messageBar().pushMessage("AcATaMa", "Error, please first select a sampling file",
                                           level=Qgis.Warning, duration=10)
            return
        # get instance
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer in ResponseDesign.instances:
            response_design = ResponseDesign.instances[sampling_layer]
            if not response_design.is_completed:
                quit_msg = "The labeling for this sampling file is not completed, " \
                           "the result will have all sampling partially labeled." \
                           "\nDo you want to continue?"
                reply = QMessageBox.question(None, 'The labeling is not completed',
                                             quit_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.No:
                    return
        else:
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, the response design for the sampling selected has not been initiated",
                                           level=Qgis.Warning, duration=10)
            return
        # get file path to suggest where to save but not in tmp directory
        file_path = get_file_path_of_layer(self.QCBox_SamplingFile.currentLayer())
        path, filename = os.path.split(file_path)
        if self.tmp_dir in path:
            path = os.path.split(get_file_path_of_layer(self.QCBox_ThematicMap.currentLayer()))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + " - labeled.gpkg" if filename else "samples labeled.gpkg"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling file with the response_design"),
                                                  suggested_filename,
                                                  self.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
        if output_file_is_OK(file_out):
            response_design.save_sampling_labeled(file_out)
            iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success, duration=10)

    @pyqtSlot()
    @error_handler
    def open_sampling_design_window(self):
        if SamplingDesignWindow.is_opened:
            # an instance of response design dialog is already created
            # brings that instance to front even if it is minimized
            self.sampling_design_window.setWindowState(self.sampling_design_window.windowState()
                                                       & ~Qt.WindowMinimized | Qt.WindowActive)
            self.sampling_design_window.raise_()
            self.sampling_design_window.activateWindow()
            return

        # open dialog
        self.sampling_design_window.show()

    @pyqtSlot()
    @error_handler
    def open_sampling_report(self):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer and sampling_layer in SamplingReport.instances:
            sampling_report = SamplingReport.instances[sampling_layer]
        else:
            return

        if SamplingReport.instance_opened:
            # an instance of response design dialog is already created
            # brings that instance to front even if it is minimized
            sampling_report.setWindowState(sampling_report.windowState()
                                           & ~Qt.WindowMinimized | Qt.WindowActive)
            sampling_report.raise_()
            sampling_report.activateWindow()
            return

        # open dialog
        sampling_report.show()


    @pyqtSlot()
    @error_handler
    def open_response_design_window(self):
        if ResponseDesignWindow.is_opened:
            # an instance of response design dialog is already created
            # brings that instance to front even if it is minimized
            self.response_design_window.setWindowState(self.response_design_window.windowState()
                                                       & ~Qt.WindowMinimized | Qt.WindowActive)
            self.response_design_window.raise_()
            self.response_design_window.activateWindow()
            return
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if not sampling_layer:
            iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid sampling file.",
                                           level=Qgis.Warning, duration=10)
            return

        # only open the response_design_grid_settings dialog the first time
        if ResponseDesignGridSettings.is_first_open:
            if not self.response_design_grid_settings.exec_():
                return

        self.response_design_window = ResponseDesignWindow(sampling_layer,
                                                           self.response_design_grid_settings.columns.value(),
                                                           self.response_design_grid_settings.rows.value())
        # open dialog
        self.response_design_window.show()

    @pyqtSlot("QgsMapLayer*")
    def update_analysis_state(self, sampling_layer=None):
        if sampling_layer is None:
            sampling_layer = self.QCBox_SamplingFile.currentLayer()

        if sampling_layer:
            # sampling file valid
            if sampling_layer in ResponseDesign.instances:
                # response_design exists for this file
                response_design = ResponseDesign.instances[sampling_layer]
                # define if this response_design was made with thematic classes
                if not response_design.with_thematic_classes:
                    self.QLabel_SamplingFileStatus.setText("Labeling was not made with thematic classes")
                    self.QLabel_SamplingFileStatus.setStyleSheet("QLabel {color: red;font: italic;}")
                    self.QGBox_Analysis.setDisabled(True)
                    return
                # check is the response_design is completed and update in dockwidget status
                if response_design.is_completed:
                    self.QLabel_SamplingFileStatus.setText("Labeling completed!")
                    self.QLabel_SamplingFileStatus.setStyleSheet("QLabel {color: green;font: italic;}")
                else:
                    self.QLabel_SamplingFileStatus.setText("Labeling not completed ({})".
                                                           format("partial" if response_design.total_labeled>0 else "not started"))
                    self.QLabel_SamplingFileStatus.setStyleSheet("QLabel {color: orange;font: italic;}")
                self.QGBox_Analysis.setEnabled(True)
                self.QPBtn_ComputeTheAccurasyAssessment.setEnabled(self.QCBox_SamplingEstimator.currentIndex() != -1)
                self.QCBox_SamplingEstimator.setCurrentIndex(response_design.estimator)

            else:
                self.QLabel_SamplingFileStatus.setText("Sampling file not labeled")
                self.QLabel_SamplingFileStatus.setStyleSheet("QLabel {color: red;font: italic;}")
                self.QGBox_Analysis.setDisabled(True)
                self.QPBtn_ComputeTheAccurasyAssessment.setDisabled(True)
        else:
            # not select sampling file
            self.QLabel_SamplingFileStatus.setText("No sampling file selected")
            self.QLabel_SamplingFileStatus.setStyleSheet("QLabel {color: gray;font: italic;}")
            self.QGBox_Analysis.setDisabled(True)
            self.QPBtn_ComputeTheAccurasyAssessment.setDisabled(True)

    @pyqtSlot(int)
    def estimator_selection_action(self, type_id):
        if not self.QCBox_SamplingFile.currentLayer():
            return
        self.QPBtn_ComputeTheAccurasyAssessment.setEnabled(type_id != -1)
        # save the estimator in response design instance
        if self.QCBox_SamplingFile.currentLayer() in ResponseDesign.instances:
            ResponseDesign.instances[self.QCBox_SamplingFile.currentLayer()].estimator = type_id

    @pyqtSlot()
    def open_accuracy_assessment_results(self):
        if AccuracyAssessmentWindow.is_opened:
            # an instance of Accuracy assessment dialog is already created
            # brings that instance to front even if it is minimized
            self.accuracy_assessment_window.setWindowState(self.accuracy_assessment_window.windowState()
                                                           & ~Qt.WindowMinimized | Qt.WindowActive)
            self.accuracy_assessment_window.raise_()
            self.accuracy_assessment_window.activateWindow()
            return

        self.accuracy_assessment_window = AccuracyAssessmentWindow()
        # open dialog
        self.accuracy_assessment_window.show()
