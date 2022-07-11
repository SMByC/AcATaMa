# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2022 by Xavier C. Llano, SMByC
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
from qgis.core import QgsProject, QgsVectorFileWriter, QgsMapLayerProxyModel, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core import config
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.core.sampling_design import do_simple_random_sampling, do_stratified_random_sampling, Sampling
from AcATaMa.core.map import get_nodata_value
from AcATaMa.gui.about_dialog import AboutDialog
from AcATaMa.gui.response_design_window import ResponseDesignWindow
from AcATaMa.utils.qgis_utils import valid_file_selected_in, load_and_select_filepath_in, get_file_path_of_layer
from AcATaMa.utils.sampling_utils import update_stratified_sampling_table, fill_stratified_sampling_table
from AcATaMa.utils.system_utils import error_handler, block_signals_to

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
        self.setup_gui()
        # tmp dir for all process and intermediate files
        self.tmp_dir = tempfile.mkdtemp()
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
        self.QPBtn_PluginInfo.setText("About")
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

        # ######### simple random sampling ######### #
        self.widget_SimpRSwithCR.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_CategMap_SimpRS.setCurrentIndex(-1)
        self.QCBox_CategMap_SimpRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the categorical map
        self.QPBtn_browseCategMap_SimpRS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_CategMap_SimpRS,
            dialog_title=self.tr("Select the categorical map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        # select and check the categorical map
        self.QCBox_CategMap_SimpRS.layerChanged.connect(self.select_categorical_map_SimpRS)
        # generate and random sampling options
        self.widget_generate_SimpRS.widget_random_sampling_options.setHidden(True)
        # generation options
        self.widget_generate_SimpRS.QPBtn_GenerateSamples.clicked.connect(lambda: do_simple_random_sampling(self))
        # update progress bar limits
        self.numberOfSamples_SimpRS.valueChanged.connect(
            lambda: self.widget_generate_SimpRS.QPBar_GenerateSamples.setValue(0))
        self.numberOfSamples_SimpRS.valueChanged.connect(self.widget_generate_SimpRS.QPBar_GenerateSamples.setMaximum)

        # ######### stratified random sampling ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_CategMap_StraRS.setCurrentIndex(-1)
        self.QCBox_CategMap_StraRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the categorical raster
        self.QPBtn_browseCategMap_StraRS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_CategMap_StraRS,
            dialog_title=self.tr("Select the categorical map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        # select and check the categorical map
        self.QCBox_CategMap_StraRS.layerChanged.connect(self.select_categorical_map_StraRS)
        self.QCBox_band_CategMap_StraRS.currentIndexChanged.connect(self.reset_StraRS_method)
        self.nodata_CategMap_StraRS.valueChanged.connect(self.reset_StraRS_method)
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of categorical map
        self.widget_TotalExpectedSE.setHidden(True)
        self.QCBox_StraRS_Method.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.QTableW_StraRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        # generate and random sampling options
        self.widget_generate_StraRS.widget_random_sampling_options.setHidden(True)
        # generation options
        self.widget_generate_StraRS.QPBtn_GenerateSamples.clicked.connect(lambda: do_stratified_random_sampling(self))

        # disable sampling tab at start
        self.scrollAreaWidgetContents_S.setDisabled(True)

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
        # change grid config
        self.grid_columns.valueChanged.connect(lambda: self.set_grid_setting("column"))
        self.grid_rows.valueChanged.connect(lambda: self.set_grid_setting("row"))
        # disable group box that depends of sampling file
        self.QGBox_ResponseDesignWindow.setDisabled(True)
        self.QGBox_saveSamplingLabeled.setDisabled(True)

        # connect the action to the run method
        self.QPBtn_OpenResponseDesignWindow.clicked.connect(self.open_response_design_window)

        # ######### Analysis tab ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_SamplingFile_A.setCurrentIndex(-1)
        self.QCBox_SamplingFile_A.setFilters(QgsMapLayerProxyModel.PointLayer)
        # set and update the sampling file status in analysis tab
        self.QCBox_SamplingFile_A.layerChanged.connect(self.set_sampling_file_in_analysis)
        # sampling type selection action
        self.QCBox_SamplingType_A.currentIndexChanged[int].connect(self.sampling_type_selection_action)
        # compute the AA and open the result dialog
        self.QPBtn_ComputeTheAccurasyAssessment.clicked.connect(self.open_accuracy_assessment_results)
        # disable group box that depends of sampling file
        self.QLabel_SamplingFileStatus_A.setText("No sampling file selected")
        self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: gray;}")
        self.QGBox_SamplingType_A.setDisabled(True)
        self.QGBox_AccuracyAssessment.setDisabled(True)

    @pyqtSlot()
    def browser_dialog_to_load_file(self, combo_box, dialog_title, file_filters):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", file_filters)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path)

    def select_thematic_map(self, layer):
        def clear_and_unset_the_thematic_map():
            with block_signals_to(self.QCBox_ThematicMap):
                self.QCBox_ThematicMap.setCurrentIndex(-1)
            self.QCBox_band_ThematicMap.clear()
            self.nodata_ThematicMap.setValue(-1)
            # SimpRS
            self.minDistance_SimpRS.setSuffix("")
            self.minDistance_SimpRS.setToolTip("")
            self.minDistance_SimpRS.setValue(0)
            # StraRS
            self.minDistance_StraRS.setSuffix("")
            self.minDistance_StraRS.setToolTip("")
            self.minDistance_StraRS.setValue(0)
            # disable sampling tab
            self.scrollAreaWidgetContents_S.setDisabled(True)
            # unset the thematic classes in response design instance
            sampling_layer = self.QCBox_SamplingFile.currentLayer()
            if sampling_layer and sampling_layer in ResponseDesign.instances:
                ResponseDesign.instances[sampling_layer].with_thematic_classes = False
            # updated state of sampling file selected for accuracy assessment tab
            self.set_sampling_file_in_analysis()

        # first check
        if not layer or not valid_file_selected_in(self.QCBox_ThematicMap, "thematic map"):
            clear_and_unset_the_thematic_map()
            return
        # check if thematic map data type is integer or byte
        if layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            clear_and_unset_the_thematic_map()
            iface.messageBar().pushMessage("AcATaMa", "Error, thematic map must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_ThematicMap.clear()
        self.QCBox_band_ThematicMap.addItems([str(x) for x in range(1, layer.bandCount() + 1)])
        # set nodata value of thematic map in nodata field
        self.nodata_ThematicMap.setValue(int(get_nodata_value(layer)))
        # set/update the units in minimum distance items in sampling tab
        layer_dist_unit = layer.crs().mapUnits()
        str_unit = QgsUnitTypes.toString(layer_dist_unit)
        abbr_unit = QgsUnitTypes.toAbbreviatedString(layer_dist_unit)
        # Set the properties of the QdoubleSpinBox based on the QgsUnitTypes of the thematic map
        # https://qgis.org/api/classQgsUnitTypes.html
        # SimpRS
        self.minDistance_SimpRS.setSuffix(" {}".format(abbr_unit))
        self.minDistance_SimpRS.setToolTip(
            "Minimum distance in {} (units based on thematic map selected)".format(str_unit))
        self.minDistance_SimpRS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.minDistance_SimpRS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_SimpRS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_SimpRS.setValue(0)
        # StraRS
        self.minDistance_StraRS.setSuffix(" {}".format(abbr_unit))
        self.minDistance_StraRS.setToolTip(
            "Minimum distance in {} (units based on thematic map selected)".format(str_unit))
        self.minDistance_StraRS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.minDistance_StraRS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_StraRS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_StraRS.setValue(0)
        # enable sampling tab
        self.scrollAreaWidgetContents_S.setEnabled(True)

    def select_categorical_map_SimpRS(self, layer):
        # first check
        if not valid_file_selected_in(self.QCBox_CategMap_SimpRS, "categorical map"):
            self.QCBox_band_CategMap_SimpRS.clear()
            return
        # check if categorical map data type is integer or byte
        if layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategMap_SimpRS.setCurrentIndex(-1)
            self.QCBox_band_CategMap_SimpRS.clear()
            iface.messageBar().pushMessage("AcATaMa", "Error, categorical map must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_CategMap_SimpRS.clear()
        self.QCBox_band_CategMap_SimpRS.addItems([str(x) for x in range(1, layer.bandCount() + 1)])

    def select_categorical_map_StraRS(self, layer):
        # first deselect/clear sampling method
        self.QCBox_StraRS_Method.setCurrentIndex(-1)
        # check
        if not valid_file_selected_in(self.QCBox_CategMap_StraRS, "categorical map"):
            self.QCBox_band_CategMap_StraRS.clear()
            self.nodata_CategMap_StraRS.setValue(-1)
            self.QGBox_Sampling_Method.setEnabled(False)
            return
        # check if categorical map data type is integer or byte
        if layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategMap_StraRS.setCurrentIndex(-1)
            self.QCBox_band_CategMap_StraRS.clear()
            self.nodata_CategMap_StraRS.setValue(-1)
            self.QGBox_Sampling_Method.setEnabled(False)
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, categorical map must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_CategMap_StraRS.clear()
        self.QCBox_band_CategMap_StraRS.addItems([str(x) for x in range(1, layer.bandCount() + 1)])
        self.QGBox_Sampling_Method.setEnabled(True)
        # set the same nodata value if select the thematic map
        if layer == self.QCBox_ThematicMap.currentLayer():
            self.nodata_CategMap_StraRS.setValue(self.nodata_ThematicMap.value())
            return
        self.nodata_CategMap_StraRS.setValue(int(get_nodata_value(layer)))

    @pyqtSlot()
    def reset_StraRS_method(self):
        # reinit variable for save tables content
        self.srs_tables = {}
        # clear table
        self.QTableW_StraRS.setRowCount(0)
        self.QTableW_StraRS.setColumnCount(0)
        # clear select
        self.QCBox_StraRS_Method.setCurrentIndex(-1)

    @pyqtSlot()
    def update_generated_sampling_list_in(self, combo_box):
        try:
            combo_box.clear()
            layers = QgsProject.instance().mapLayers().values()
            for layer in layers:
                if layer.name() in list(Sampling.samplings.keys()):
                    combo_box.addItem(layer.name())
        except:
            pass

    @pyqtSlot()
    @error_handler
    def file_dialog_save_sampling(self, combo_box):
        if combo_box.currentText() not in Sampling.samplings:
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, please select a valid sampling file", level=Qgis.Warning)
            return
        suggested_filename = os.path.splitext(Sampling.samplings[combo_box.currentText()].thematic_map.file_path)[0] \
                             + "_sampling.gpkg"
        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling file"),
                                                  suggested_filename,
                                                  self.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
        if file_out != '':
            layer = combo_box.currentLayer()
            file_format = \
                "GPKG" if file_out.endswith(".gpkg") else "ESRI Shapefile" if file_out.endswith(".shp") else None
            QgsVectorFileWriter.writeAsVectorFormat(layer, file_out, "System", layer.crs(), file_format)
            iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success)

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
            # check if the response design is completed and update in dockwidget status
            if sampling_layer in ResponseDesign.instances and ResponseDesign.instances[sampling_layer].is_completed:
                self.QLabel_LabelingStatus.setText("Labeling completed")
                self.QLabel_LabelingStatus.setStyleSheet("QLabel {color: green;}")
            else:
                self.QLabel_LabelingStatus.setText("Labeling not completed")
                self.QLabel_LabelingStatus.setStyleSheet("QLabel {color: orange;}")
            # grid settings
            if sampling_layer in ResponseDesign.instances:
                response_design = ResponseDesign.instances[sampling_layer]
                with block_signals_to(self.QGBox_GridSettings):
                    self.grid_columns.setValue(response_design.grid_columns)
                    self.grid_rows.setValue(response_design.grid_rows)
            else:
                with block_signals_to(self.QGBox_GridSettings):
                    self.grid_columns.setValue(2)
                    self.grid_rows.setValue(1)
            if not ResponseDesignWindow.is_opened:
                # enable group box that depends on sampling file
                self.QGBox_ResponseDesignWindow.setEnabled(True)
                self.QGBox_saveSamplingLabeled.setEnabled(True)
        else:
            # return to default values
            self.QPBar_LabelingStatus.setTextVisible(False)
            self.QPBar_LabelingStatus.setValue(0)
            self.QLabel_LabelingStatus.setText("No sampling file selected")
            self.QLabel_LabelingStatus.setStyleSheet("QLabel {color: gray;}")
            self.grid_columns.setValue(2)
            self.grid_rows.setValue(1)
            # disable group box that depends on sampling file
            self.QGBox_ResponseDesignWindow.setDisabled(True)
            self.QGBox_saveSamplingLabeled.setDisabled(True)

        # update state of sampling file selected for accuracy assessment tab
        self.set_sampling_file_in_analysis()

    @pyqtSlot()
    def reload_sampling_file(self):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer:
            # sampling file valid
            if sampling_layer in ResponseDesign.instances:
                response_design = ResponseDesign.instances[sampling_layer]
                response_design.reload_sampling_file()
            else:
                response_design = ResponseDesign(sampling_layer)
                response_design.reload_sampling_file()
            # updated state of sampling file selected for accuracy assessment tab
            self.set_sampling_file_in_analysis()
        else:
            iface.messageBar().pushMessage("AcATaMa", "No sampling file selected",
                                           level=Qgis.Warning)

    @pyqtSlot()
    def set_grid_setting(self, item):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer in ResponseDesign.instances:
            response_design = ResponseDesign.instances[sampling_layer]
            if item == "column":
                response_design.grid_columns = self.grid_columns.value()
            if item == "row":
                response_design.grid_rows = self.grid_rows.value()

    @pyqtSlot()
    @error_handler
    def file_dialog_restore_acatama_state(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Restore to a previous saved of AcATaMa configuration and state"),
                                                   "", self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))

        if file_path != '' and os.path.isfile(file_path):
            # restore configuration and response design state
            config.restore(file_path)
            self.suggested_yml_file = file_path
            iface.messageBar().pushMessage("AcATaMa", "Configuration and state restored successfully", level=Qgis.Success)

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
            suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_acatama.yml" if filename else "_acatama.yml"
        else:
            suggested_filename = "_acatama.yml"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save AcATaMa configuration and state"),
                                                  suggested_filename, self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))
        if file_out != '':
            config.save(file_out)
            self.suggested_yml_file = file_out
            iface.messageBar().pushMessage("AcATaMa", "Configuration file saved successfully", level=Qgis.Success)

    @pyqtSlot()
    @error_handler
    def file_dialog_save_sampling_labeled(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            iface.messageBar().pushMessage("AcATaMa", "Error, please first select a sampling file",
                                           level=Qgis.Warning)
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
                                           level=Qgis.Warning)
            return
        # get file path to suggest where to save but not in tmp directory
        file_path = get_file_path_of_layer(self.QCBox_SamplingFile.currentLayer())
        path, filename = os.path.split(file_path)
        if self.tmp_dir in path:
            path = os.path.split(get_file_path_of_layer(self.QCBox_ThematicMap.currentLayer()))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_labeled.gpkg" if filename else ""

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling file with the response_design"),
                                                  suggested_filename,
                                                  self.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
        if file_out != '':
            response_design.save_sampling_labeled(file_out)
            iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success)

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
                                           level=Qgis.Warning)
            return

        self.response_design_window = \
            ResponseDesignWindow(sampling_layer, self.grid_columns.value(), self.grid_rows.value())
        # open dialog
        self.response_design_window.show()

    def set_sampling_file_in_analysis(self, sampling_layer=None):
        if sampling_layer is None:
            sampling_layer = self.QCBox_SamplingFile_A.currentLayer()

        if sampling_layer:
            # sampling file valid
            if sampling_layer in ResponseDesign.instances:
                # response_design exists for this file
                response_design = ResponseDesign.instances[sampling_layer]
                # define if this response_design was made with thematic classes
                if not response_design.with_thematic_classes:
                    self.QLabel_SamplingFileStatus_A.setText("Labeling was not made with thematic classes")
                    self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: red;}")
                    self.QGBox_SamplingType_A.setDisabled(True)
                    self.QGBox_AccuracyAssessment.setDisabled(True)
                    return
                # check is the response_design is completed and update in dockwidget status
                if response_design.is_completed:
                    self.QLabel_SamplingFileStatus_A.setText("Labeling completed ({}/{})".
                                                              format(response_design.total_labeled,
                                                                     response_design.num_points))
                    self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: green;}")
                else:
                    self.QLabel_SamplingFileStatus_A.setText("Labeling not completed ({}/{})".
                                                              format(response_design.total_labeled,
                                                                     response_design.num_points))
                    self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: orange;}")
                self.QGBox_SamplingType_A.setEnabled(True)
                self.QGBox_AccuracyAssessment.setEnabled(self.QCBox_SamplingType_A.currentIndex() != -1)
                self.QCBox_SamplingType_A.setCurrentIndex(response_design.sampling_type)

            else:
                self.QLabel_SamplingFileStatus_A.setText("Sampling file not labeled")
                self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: red;}")
                self.QGBox_SamplingType_A.setDisabled(True)
                self.QGBox_AccuracyAssessment.setDisabled(True)
        else:
            # not select sampling file
            self.QLabel_SamplingFileStatus_A.setText("No sampling file selected")
            self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: gray;}")
            self.QGBox_SamplingType_A.setDisabled(True)
            self.QGBox_AccuracyAssessment.setDisabled(True)

    @pyqtSlot(int)
    def sampling_type_selection_action(self, type_id):
        if not self.QCBox_SamplingFile_A.currentLayer():
            return
        self.QGBox_AccuracyAssessment.setEnabled(type_id != -1)
        # save the sampling type to response design instance
        if self.QCBox_SamplingFile_A.currentLayer() in ResponseDesign.instances:
            ResponseDesign.instances[self.QCBox_SamplingFile_A.currentLayer()].sampling_type = type_id

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
