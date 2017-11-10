# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017 by Xavier Corredor Llano, SMBYC
        email                : xcorredorl@ideam.gov.co
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
import ConfigParser

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal, pyqtSlot
from PyQt4.QtGui import QMessageBox
from qgis.core import QgsMapLayerRegistry, QgsVectorFileWriter
from qgis.gui import QgsMessageBar

from AcATaMa.core.accuracy_assessment import AccuracyAssessment, AccuracyAssessmentDialog
from AcATaMa.core.classification import Classification
from AcATaMa.core.sampling import do_random_sampling, do_stratified_random_sampling, Sampling
from AcATaMa.core.dockwidget import get_current_file_path_in, update_layers_list, \
    unload_layer_in_qgis, get_current_layer_in, fill_stratified_sampling_table, valid_file_selected_in, \
    update_stratified_sampling_table, load_and_select_filepath_in
from AcATaMa.core.utils import wait_process, error_handler, block_signals_to
from AcATaMa.core.raster import do_clipping_with_shape, get_nodata_value
from AcATaMa.gui.about_dialog import AboutDialog
from AcATaMa.gui.classification_dialog import ClassificationDialog

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'acatama_dockwidget.ui'))

cfg = ConfigParser.SafeConfigParser()
cfg.read(os.path.join(plugin_folder, 'metadata.txt'))
VERSION = cfg.get('general', 'version')
HOMEPAGE = cfg.get('general', 'homepage')


class AcATaMaDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    dockwidget = None

    def __init__(self, parent, iface):
        """Constructor."""
        super(AcATaMaDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.setupUi(self)
        self.setup_gui()
        # tmp dir for all process and intermediate files
        self.tmp_dir = tempfile.mkdtemp()
        # save instance
        AcATaMaDockWidget.dockwidget = self

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def setup_gui(self):
        # ######### plugin about ######### #
        self.about_dialog = AboutDialog()
        self.plugin_version.setText(self.tr(u"AcATaMa v{}".format(VERSION)))
        self.button_about.clicked.connect(self.about_dialog.show)

        # ######### load thematic raster image ######### #
        update_layers_list(self.QCBox_ThematicRaster, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_ThematicRaster, "raster"))
        # call to browse the thematic raster file
        self.QPBtn_browseThematicRaster.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_ThematicRaster,
            dialog_title=self.tr(u"Select the thematic raster image to evaluate"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # set the nodata value of the thematic raster
        self.QCBox_ThematicRaster.currentIndexChanged.connect(self.set_nodata_value_thematic_raster)

        # ######### shape area of interest ######### #
        self.widget_AreaOfInterest.setHidden(True)
        update_layers_list(self.QCBox_AreaOfInterest, "vector")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_AreaOfInterest, "vector"))
        # call to browse the shape area
        self.QPBtn_browseAreaOfInterest.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_AreaOfInterest,
            dialog_title=self.tr(u"Select the shape file"),
            dialog_types=self.tr(u"Shape files (*.shp);;All files (*.*)"),
            layer_type="vector"))
        # do clip
        self.QPBtn_ClippingThematic.clicked.connect(self.clipping_thematic_raster)

        # ######### create categorical  ######### # TODO
        #self.widget_CategRaster.setHidden(True)
        # update_layers_list(self.selectCategRaster, "raster")
        # # handle connect when the list of layers changed
        # self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectCategRaster, "raster"))
        # # call to browse the categorical raster
        # self.browseCategRaster.clicked.connect(lambda: self.fileDialog_browse(
        #     self.selectCategRaster,
        #     dialog_title=self.tr(u"Select the categorical raster file"),
        #     dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
        #     layer_type="raster"))

        # ######### random sampling ######### #
        self.widget_RSwithCR.setHidden(True)
        update_layers_list(self.QCBox_CategRaster_RS, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_CategRaster_RS, "raster"))
        # call to browse the categorical raster
        self.QPBtn_browseCategRaster_RS.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_CategRaster_RS,
            dialog_title=self.tr(u"Select the categorical raster file"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # set the nodata value of the categorical raster
        self.QCBox_CategRaster_SRS.currentIndexChanged.connect(self.set_nodata_value_categorical_raster)
        self.nodata_CategRaster_SRS.valueChanged.connect(self.reset_nodata_to_categorical_raster)
        # generate sampling options
        self.widget_generate_RS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_RS.widget_save_sampling.setHidden(True)
        self.canvas.layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_RS.QCBox_SamplingToSave))
        self.widget_generate_RS.QPBtn_SaveSampling.clicked.connect(
            lambda: self.fileDialog_saveSampling(self.widget_generate_RS.QCBox_SamplingToSave))
        self.widget_generate_RS.QPBtn_SaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_RS.QCBox_SamplingToSave))
        # generate sampling
        self.widget_generate_RS.QPBtn_GenerateSampling.clicked.connect(lambda: do_random_sampling(self))
        # update progress bar limits
        self.numberOfSamples_RS.valueChanged.connect(lambda: self.widget_generate_RS.QPBar_GenerateSampling.setValue(0))
        self.numberOfSamples_RS.valueChanged.connect(self.widget_generate_RS.QPBar_GenerateSampling.setMaximum)

        # ######### stratified random sampling ######### #
        update_layers_list(self.QCBox_CategRaster_SRS, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_CategRaster_SRS, "raster"))
        # call to browse the categorical raster
        self.QPBtn_browseCategRaster_SRS.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_CategRaster_SRS,
            dialog_title=self.tr(u"Select the categorical raster file"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of categorical raster
        self.widget_TotalExpectedSE.setHidden(True)
        self.QCBox_CategRaster_SRS.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        self.QCBox_SRS_Method.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.QTableW_SRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        # generate sampling options
        self.widget_generate_SRS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_SRS.widget_save_sampling.setHidden(True)
        self.canvas.layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_SRS.QCBox_SamplingToSave))
        self.widget_generate_SRS.QPBtn_SaveSampling.clicked.connect(
            lambda: self.fileDialog_saveSampling(self.widget_generate_SRS.QCBox_SamplingToSave))
        self.widget_generate_SRS.QPBtn_SaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_SRS.QCBox_SamplingToSave))
        # generate sampling
        self.widget_generate_SRS.QPBtn_GenerateSampling.clicked.connect(lambda: do_stratified_random_sampling(self))

        # ######### Classification sampling tab ######### #
        update_layers_list(self.QCBox_SamplingFile, "vector", "points")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_SamplingFile, "vector", "points"))
        # show the classification file settings in plugin when it is selected
        self.QCBox_SamplingFile.currentIndexChanged.connect(self.set_classification_file_settings)
        # call to browse the sampling file
        self.QPBtn_browseSamplingFile.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_SamplingFile,
            dialog_title=self.tr(u"Select the Sampling points file to classify"),
            dialog_types=self.tr(u"Shape files (*.shp);;All files (*.*)"),
            layer_type="vector"))
        # call to load and save classification config
        self.QPBtn_loadClassificationConfig.clicked.connect(self.fileDialog_loadClassificationConfig)
        self.QPBtn_saveClassificationConfig.clicked.connect(self.fileDialog_saveClassificationConfig)
        # save sampling + classification
        self.QPBtn_saveSamplingClassification.clicked.connect(self.fileDialog_saveSamplingClassification)
        # change grid config
        self.grid_columns.valueChanged.connect(lambda: self.set_grid_setting("column"))
        self.grid_rows.valueChanged.connect(lambda: self.set_grid_setting("row"))

        # connect the action to the run method
        self.QPBtn_OpenClassificationDialog.clicked.connect(self.open_classification_dialog)

        # ######### Accuracy Assessment tab ######### #
        update_layers_list(self.QCBox_SamplingFile_AA, "vector", "points")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.QCBox_SamplingFile_AA, "vector", "points"))
        # set and show the classification file status in AA
        self.QCBox_SamplingFile_AA.currentIndexChanged.connect(self.set_sampling_file_accuracy_assessment)
        # compute the AA and open the result dialog
        self.QPBtn_ComputeViewAccurasyAssessment.clicked.connect(self.open_accuracy_assessment_results)

    @pyqtSlot()
    def fileDialog_browse(self, combo_box, dialog_title, dialog_types, layer_type):
        file_path = QtGui.QFileDialog.getOpenFileName(self, dialog_title, "", dialog_types)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path, layer_type)

    @pyqtSlot()
    def set_nodata_value_thematic_raster(self):
        current_layer = get_current_layer_in(self.QCBox_ThematicRaster)
        if not current_layer:
            return

        self.nodata_ThematicRaster.setValue(get_nodata_value(current_layer))

    @pyqtSlot()
    def set_nodata_value_categorical_raster(self):
        current_layer = get_current_layer_in(self.QCBox_CategRaster_SRS)
        if not current_layer:
            return
        # set the same nodata value if select the thematic raster
        if current_layer == get_current_layer_in(self.QCBox_ThematicRaster):
            self.nodata_CategRaster_SRS.setValue(self.nodata_ThematicRaster.value())
            return

        self.nodata_CategRaster_SRS.setValue(get_nodata_value(current_layer))

    @pyqtSlot()
    def reset_nodata_to_categorical_raster(self):
        # reinit variable for save tables content
        self.srs_tables = {}
        # clear table
        self.QTableW_SRS.setRowCount(0)
        self.QTableW_SRS.setColumnCount(0)
        # clear select
        self.QCBox_SRS_Method.setCurrentIndex(-1)

    @pyqtSlot()
    @error_handler()
    @wait_process("QPBtn_ClippingThematic")
    def clipping_thematic_raster(self):
        # first check input files requirements
        if not valid_file_selected_in(self.QCBox_ThematicRaster, "thematic raster"):
            return
        if not valid_file_selected_in(self.QCBox_AreaOfInterest, "area of interest shape"):
            return

        clip_file = do_clipping_with_shape(
            get_current_file_path_in(self.QCBox_ThematicRaster),
            get_current_file_path_in(self.QCBox_AreaOfInterest), self.tmp_dir)
        # unload old thematic file
        unload_layer_in_qgis(get_current_file_path_in(self.QCBox_ThematicRaster))
        # load to qgis and update combobox list
        load_and_select_filepath_in(self.QCBox_ThematicRaster, clip_file, "raster")

        self.iface.messageBar().pushMessage("AcATaMa", "Clipping the thematic raster with shape, completed",
                                            level=QgsMessageBar.SUCCESS)

    @pyqtSlot()
    def update_generated_sampling_list_in(self, combo_box):
        combo_box.clear()
        layers = QgsMapLayerRegistry.instance().mapLayers().values()

        for layer in layers:
            if layer.name() in Sampling.samplings.keys():
                combo_box.addItem(layer.name())

    @pyqtSlot()
    def fileDialog_saveSampling(self, combo_box):
        if combo_box.currentText() not in Sampling.samplings:
            self.iface.messageBar().pushMessage("AcATaMa",
                                                "Error, please select a valid sampling file", level=QgsMessageBar.WARNING)
            return
        suggested_filename = os.path.splitext(Sampling.samplings[combo_box.currentText()].ThematicR.file_path)[0] \
                             + "_sampling.shp"
        file_out = QtGui.QFileDialog.getSaveFileName(self, self.tr(u"Save sampling file"),
                                                     suggested_filename,
                                                     self.tr(u"Shape files (*.shp);;All files (*.*)"))
        if file_out != '':
            layer = get_current_layer_in(combo_box)
            QgsVectorFileWriter.writeAsVectorFormat(layer, file_out, "utf-8", layer.crs(), "ESRI Shapefile")
            self.iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=QgsMessageBar.SUCCESS)

    @pyqtSlot()
    def fileDialog_saveSamplingConf(self, combo_box):
        if combo_box.currentText() not in Sampling.samplings:
            self.iface.messageBar().pushMessage("AcATaMa",
                                                "Error, please select a valid sampling file", level=QgsMessageBar.WARNING)
            return
        sampling_selected = Sampling.samplings[combo_box.currentText()]
        suggested_filename = os.path.splitext(sampling_selected.ThematicR.file_path)[0] \
                             + "_sampling.ini"
        file_out = QtGui.QFileDialog.getSaveFileName(self, self.tr(u"Save sampling configuration"),
                                                     suggested_filename,
                                                     self.tr(u"Ini files (*.ini);;All files (*.*)"))
        if file_out != '':
            sampling_selected.save_config(file_out)
            self.iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=QgsMessageBar.SUCCESS)

    @pyqtSlot()
    def set_classification_file_settings(self):
        sampling_layer = get_current_layer_in(self.QCBox_SamplingFile)
        if sampling_layer:
            # classification status
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                total_classified = sum(sample.is_classified for sample in classification.points)
                self.QPBar_ClassificationStatus.setMaximum(len(classification.points))
                self.QPBar_ClassificationStatus.setValue(total_classified)
            else:
                count_samples = len(list(sampling_layer.getFeatures()))
                self.QPBar_ClassificationStatus.setMaximum(count_samples)
                self.QPBar_ClassificationStatus.setValue(0)
            self.QPBar_ClassificationStatus.setTextVisible(True)
            # check is the classification is completed and update in dockwidget status
            if sampling_layer in Classification.instances and Classification.instances[sampling_layer].is_completed:
                self.QLabel_ClassificationStatus.setText("Classification completed")
                self.QLabel_ClassificationStatus.setStyleSheet("QLabel {color: green;}")
            else:
                self.QLabel_ClassificationStatus.setText("Classification not completed")
                self.QLabel_ClassificationStatus.setStyleSheet("QLabel {color: orange;}")
            # grid settings
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                with block_signals_to(self.QGBox_GridSettings):
                    self.grid_columns.setValue(classification.grid_columns)
                    self.grid_rows.setValue(classification.grid_rows)
            else:
                with block_signals_to(self.QGBox_GridSettings):
                    self.grid_columns.setValue(3)
                    self.grid_rows.setValue(2)
        else:
            # return to default values
            self.QPBar_ClassificationStatus.setTextVisible(False)
            self.QPBar_ClassificationStatus.setValue(0)
            self.QLabel_ClassificationStatus.setText("No sampling file selected")
            self.QLabel_ClassificationStatus.setStyleSheet("QLabel {color: gray;}")
            self.grid_columns.setValue(3)
            self.grid_rows.setValue(2)

        # updated state of sampling file selected for accuracy assessment tab
        self.set_sampling_file_accuracy_assessment()

    @pyqtSlot()
    def set_grid_setting(self, item):
        sampling_layer = get_current_layer_in(self.QCBox_SamplingFile)
        if sampling_layer in Classification.instances:
            classification = Classification.instances[sampling_layer]
            if item == "column":
                classification.grid_columns = self.grid_columns.value()
            if item == "row":
                classification.grid_rows = self.grid_rows.value()

    @pyqtSlot()
    def fileDialog_loadClassificationConfig(self):
        file_path = QtGui.QFileDialog.getOpenFileName(self, self.tr(u"Save settings and classification status"),
                                                     "", self.tr(u"Yaml (*.yaml *.yml);;All files (*.*)"))

        if file_path != '' and os.path.isfile(file_path):
            # load classification status from yaml file
            import yaml
            with open(file_path, 'r') as yaml_file:
                try:
                    yaml_config = yaml.load(yaml_file)
                except yaml.YAMLError as err:
                    self.iface.messageBar().pushMessage("AcATaMa","Error while read the yaml file classification config",
                                                        level=QgsMessageBar.CRITICAL)
                    return
            # load the sampling file save in yaml config
            sampling_filepath = yaml_config["sampling_layer"]
            if not os.path.isfile(sampling_filepath):
                self.iface.messageBar().pushMessage("AcATaMa", "Error the sampling file saved in this config file, not exists",
                                                    level=QgsMessageBar.CRITICAL)
                # TODO: ask for new location of the sampling file
                return

            sampling_layer = load_and_select_filepath_in(self.QCBox_SamplingFile, sampling_filepath, "vector", "points")

            classification = Classification(sampling_layer)
            classification.load_config(yaml_config)
            self.iface.messageBar().pushMessage("AcATaMa", "File loaded successfully", level=QgsMessageBar.SUCCESS)

    @pyqtSlot()
    def fileDialog_saveClassificationConfig(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            self.iface.messageBar().pushMessage("AcATaMa",
                                                "Error, please select a sampling file to save configuration",
                                                level=QgsMessageBar.WARNING)
            return
        # get file path to suggest to save but not in tmp directory
        path, filename = os.path.split(get_current_file_path_in(self.QCBox_SamplingFile))
        if self.tmp_dir in path:
            path = os.path.split(get_current_file_path_in(self.QCBox_ThematicRaster))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_config.yml"

        file_out = QtGui.QFileDialog.getSaveFileName(self, self.tr(u"Save settings and classification status"),
                                                     suggested_filename, self.tr(u"Yaml (*.yaml *.yml);;All files (*.*)"))
        if file_out != '':
            sampling_layer = get_current_layer_in(self.QCBox_SamplingFile)
            if sampling_layer in Classification.instances:
                Classification.instances[sampling_layer].save_config(file_out)
                self.iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=QgsMessageBar.SUCCESS)
            else:
                self.iface.messageBar().pushMessage("AcATaMa",
                                                    "Failed to save, there isn't any configuration to save",
                                                    level=QgsMessageBar.WARNING)

    @pyqtSlot()
    def fileDialog_saveSamplingClassification(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            self.iface.messageBar().pushMessage("AcATaMa", "Error, please first select a sampling file",
                                                level=QgsMessageBar.WARNING)
            return
        # get instance
        sampling_layer = get_current_layer_in(self.QCBox_SamplingFile)
        if sampling_layer in Classification.instances:
            classification = Classification.instances[sampling_layer]
            if not classification.is_completed:
                quit_msg = "The classification for this sampling file is not completed, " \
                            "do you want to continue anyway?"
                reply = QMessageBox.question(self, 'The classification is not completed',
                                             quit_msg,QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.No:
                    return
        else:
            self.iface.messageBar().pushMessage("AcATaMa",
                                                "Error, the classification for the sampling selected has not been initiated",
                                                level=QgsMessageBar.WARNING)
            return
        # get file path to suggest to save but not in tmp directory
        path, filename = os.path.split(get_current_file_path_in(self.QCBox_SamplingFile))
        if self.tmp_dir in path:
            path = os.path.split(get_current_file_path_in(self.QCBox_ThematicRaster))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_classified.shp"
        file_out = QtGui.QFileDialog.getSaveFileName(self, self.tr(u"Save sampling file with the classification"),
                                                     suggested_filename,
                                                     self.tr(u"Shape files (*.shp);;All files (*.*)"))
        if file_out != '':
            classification.save_sampling_classification(file_out)
            self.iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=QgsMessageBar.SUCCESS)

    @pyqtSlot()
    def open_classification_dialog(self):
        if ClassificationDialog.is_opened:
            self.classification_dialog.activateWindow()
            return
        sampling_layer = get_current_layer_in(self.QCBox_SamplingFile)
        if not sampling_layer:
            self.iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid sampling file to classify",
                                                level=QgsMessageBar.WARNING)
            return

        self.classification_dialog = \
            ClassificationDialog(sampling_layer, self.grid_columns.value(), self.grid_rows.value())
        # open dialog
        self.classification_dialog.show()

    @pyqtSlot()
    def set_sampling_file_accuracy_assessment(self):
        sampling_layer = get_current_layer_in(self.QCBox_SamplingFile_AA)
        if sampling_layer:
            # sampling file valid
            if sampling_layer in Classification.instances:
                # classification exists for this file
                classification = Classification.instances[sampling_layer]
                total_classified = sum(sample.is_classified for sample in classification.points)
                # check is the classification is completed and update in dockwidget status
                if classification.is_completed:
                    self.QLabel_SamplingFileStatus_AA.setText("Classification completed ({}/{})".
                                                              format(total_classified, len(classification.points)))
                    self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: green;}")
                else:
                    self.QLabel_SamplingFileStatus_AA.setText("Classification not completed ({}/{})".
                                                              format(total_classified, len(classification.points)))
                    self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: orange;}")
                self.QGBox_AccuracyAssessment.setEnabled(True)
            else:
                self.QLabel_SamplingFileStatus_AA.setText("Sampling file not classified")
                self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: red;}")
                self.QGBox_AccuracyAssessment.setDisabled(True)
        else:
            # not select sampling file
            self.QLabel_SamplingFileStatus_AA.setText("No sampling file selected")
            self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: gray;}")
            self.QGBox_AccuracyAssessment.setDisabled(True)

    @pyqtSlot()
    def open_accuracy_assessment_results(self):
        if AccuracyAssessmentDialog.is_opened:
            self.accuracy_assessment_dialog.activateWindow()
            return

        self.accuracy_assessment_dialog = AccuracyAssessmentDialog()
        # open dialog
        self.accuracy_assessment_dialog.show()


