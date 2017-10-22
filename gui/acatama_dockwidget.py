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
from PyQt4.QtCore import pyqtSignal, Qt, pyqtSlot
from qgis.core import QgsMapLayerRegistry, QgsVectorFileWriter
from qgis.gui import QgsMessageBar

from AcATaMa.core.classification import Classification
from AcATaMa.core.sampling import do_random_sampling, do_stratified_random_sampling, Sampling
from AcATaMa.core.dockwidget import get_current_file_path_in, load_layer_in_qgis, update_layers_list, unload_layer_in_qgis, get_current_layer_in, \
    fill_stratified_sampling_table, valid_file_selected_in, update_stratified_sampling_table
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

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def setup_gui(self):
        # ######### plugin about ######### #
        self.about_dialog = AboutDialog()
        self.plugin_version.setText(self.tr(u"AcATaMa v{}".format(VERSION)))
        self.button_about.clicked.connect(self.about_dialog.show)

        # ######### load thematic raster image ######### #
        update_layers_list(self.selectThematicRaster, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectThematicRaster, "raster"))
        # call to browse the thematic raster file
        self.browseThematicRaster.clicked.connect(lambda: self.fileDialog_browse(
            self.selectThematicRaster,
            dialog_title=self.tr(u"Select the thematic raster image to evaluate"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # set the nodata value of the thematic raster
        self.selectThematicRaster.currentIndexChanged.connect(self.set_nodata_value_thematic_raster)

        # ######### shape study area ######### #
        self.widget_ShapeArea.setHidden(True)
        update_layers_list(self.selectShapeArea, "vector")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectShapeArea, "vector"))
        # call to browse the shape area
        self.browseShapeArea.clicked.connect(lambda: self.fileDialog_browse(
            self.selectShapeArea,
            dialog_title=self.tr(u"Select the shape file"),
            dialog_types=self.tr(u"Shape files (*.shp);;All files (*.*)"),
            layer_type="vector"))
        # do clip
        self.buttonClipping.clicked.connect(self.clipping_thematic_raster)

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
        update_layers_list(self.selectCategRaster_RS, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectCategRaster_RS, "raster"))
        # call to browse the categorical raster
        self.browseCategRaster_RS.clicked.connect(lambda: self.fileDialog_browse(
            self.selectCategRaster_RS,
            dialog_title=self.tr(u"Select the categorical raster file"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # set the nodata value of the categorical raster
        self.selectCategRaster_SRS.currentIndexChanged.connect(self.set_nodata_value_categorical_raster)
        self.nodata_CategRaster_SRS.valueChanged.connect(self.reset_nodata_to_categorical_raster)
        # generate sampling options
        self.widget_generate_RS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_RS.widget_save_sampling.setHidden(True)
        self.canvas.layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_RS.selectSamplingToSave))
        self.widget_generate_RS.buttonSaveSampling.clicked.connect(
            lambda: self.fileDialog_saveSampling(self.widget_generate_RS.selectSamplingToSave))
        self.widget_generate_RS.buttonSaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_RS.selectSamplingToSave))
        # generate sampling
        self.widget_generate_RS.buttonGenerateSampling.clicked.connect(lambda: do_random_sampling(self))
        # update progress bar limits
        self.numberOfSamples_RS.valueChanged.connect(lambda: self.widget_generate_RS.progressGenerateSampling.setValue(0))
        self.numberOfSamples_RS.valueChanged.connect(self.widget_generate_RS.progressGenerateSampling.setMaximum)

        # ######### stratified random sampling ######### #
        update_layers_list(self.selectCategRaster_SRS, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectCategRaster_SRS, "raster"))
        # call to browse the categorical raster
        self.browseCategRaster_SRS.clicked.connect(lambda: self.fileDialog_browse(
            self.selectCategRaster_SRS,
            dialog_title=self.tr(u"Select the categorical raster file"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of categorical raster
        self.widget_TotalExpectedSE.setHidden(True)
        self.selectCategRaster_SRS.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        self.StratifieSamplingMethod.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.TableWidget_SRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        # generate sampling options
        self.widget_generate_SRS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_SRS.widget_save_sampling.setHidden(True)
        self.canvas.layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_SRS.selectSamplingToSave))
        self.widget_generate_SRS.buttonSaveSampling.clicked.connect(
            lambda: self.fileDialog_saveSampling(self.widget_generate_SRS.selectSamplingToSave))
        self.widget_generate_SRS.buttonSaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_SRS.selectSamplingToSave))
        # generate sampling
        self.widget_generate_SRS.buttonGenerateSampling.clicked.connect(lambda: do_stratified_random_sampling(self))

        # ######### Classification sampling tab ######### #
        update_layers_list(self.selectSamplingFile, "vector", "points")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectSamplingFile, "vector", "points"))
        # show the classification file settings in plugin when it is selected
        self.selectSamplingFile.currentIndexChanged.connect(self.set_classification_file_settings)
        # call to browse the sampling file
        self.browseSamplingFile.clicked.connect(lambda: self.fileDialog_browse(
            self.selectSamplingFile,
            dialog_title=self.tr(u"Select the Sampling points file to classify"),
            dialog_types=self.tr(u"Shape files (*.shp);;All files (*.*)"),
            layer_type="vector"))
        # change grid config
        self.grid_columns.valueChanged.connect(lambda: self.set_grid_setting("column"))
        self.grid_rows.valueChanged.connect(lambda: self.set_grid_setting("row"))

        # connect the action to the run method
        self.buttonOpenClassificationDialog.clicked.connect(self.open_classification_dialog)

    @pyqtSlot()
    def fileDialog_browse(self, combo_box, dialog_title, dialog_types, layer_type):
        file_path = QtGui.QFileDialog.getOpenFileName(self, dialog_title, "", dialog_types)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            filename = load_layer_in_qgis(file_path, layer_type)
            update_layers_list(combo_box, layer_type)
            selected_index = combo_box.findText(filename, Qt.MatchFixedString)
            combo_box.setCurrentIndex(selected_index)

    @pyqtSlot()
    def set_nodata_value_thematic_raster(self):
        current_layer = get_current_layer_in(self.selectThematicRaster)
        if not current_layer:
            return

        self.nodata_ThematicRaster.setValue(get_nodata_value(current_layer))

    @pyqtSlot()
    def set_nodata_value_categorical_raster(self):
        current_layer = get_current_layer_in(self.selectCategRaster_SRS)
        if not current_layer:
            return
        # set the same nodata value if select the thematic raster
        if current_layer == get_current_layer_in(self.selectThematicRaster):
            self.nodata_CategRaster_SRS.setValue(self.nodata_ThematicRaster.value())
            return

        self.nodata_CategRaster_SRS.setValue(get_nodata_value(current_layer))

    @pyqtSlot()
    def reset_nodata_to_categorical_raster(self):
        # reinit variable for save tables content
        self.srs_tables = {}
        # clear table
        self.TableWidget_SRS.setRowCount(0)
        self.TableWidget_SRS.setColumnCount(0)
        # clear select
        self.StratifieSamplingMethod.setCurrentIndex(-1)

    @pyqtSlot()
    @error_handler()
    @wait_process("buttonClipping")
    def clipping_thematic_raster(self):
        # first check input files requirements
        if not valid_file_selected_in(self.selectThematicRaster, "thematic raster"):
            return
        if not valid_file_selected_in(self.selectShapeArea, "shape study area"):
            return

        clip_file = do_clipping_with_shape(
            get_current_file_path_in(self.selectThematicRaster),
            get_current_file_path_in(self.selectShapeArea), self.tmp_dir)
        # unload old thematic file
        unload_layer_in_qgis(get_current_file_path_in(self.selectThematicRaster))
        # load to qgis and update combobox list
        filename = load_layer_in_qgis(clip_file, "raster")
        update_layers_list(self.selectThematicRaster, "raster")
        selected_index = self.selectThematicRaster.findText(filename, Qt.MatchFixedString)
        self.selectThematicRaster.setCurrentIndex(selected_index)

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

    @pyqtSlot()
    def set_classification_file_settings(self):
        sampling_layer = get_current_layer_in(self.selectSamplingFile)
        if sampling_layer:
            # classification status
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                total_classified = sum(sample.is_classified for sample in classification.points)
                self.ClassificationStatusPB.setMaximum(len(classification.points))
                self.ClassificationStatusPB.setValue(total_classified)
            else:
                count_samples = len(list(sampling_layer.getFeatures()))
                self.ClassificationStatusPB.setMaximum(count_samples)
                self.ClassificationStatusPB.setValue(0)
            self.ClassificationStatusPB.setTextVisible(True)
            # grid settings
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                with block_signals_to(self.grid_settings):
                    self.grid_columns.setValue(classification.grid_columns)
                    self.grid_rows.setValue(classification.grid_rows)
            else:
                with block_signals_to(self.grid_settings):
                    self.grid_columns.setValue(3)
                    self.grid_rows.setValue(2)

    @pyqtSlot()
    def set_grid_setting(self, item):
        sampling_layer = get_current_layer_in(self.selectSamplingFile)
        if sampling_layer in Classification.instances:
            classification = Classification.instances[sampling_layer]
            if item == "column":
                classification.grid_columns = self.grid_columns.value()
            if item == "row":
                classification.grid_rows = self.grid_rows.value()

    @pyqtSlot()
    def open_classification_dialog(self):
        if ClassificationDialog.is_opened:
            self.classification_dialog.activateWindow()
            return
        sampling_layer = get_current_layer_in(self.selectSamplingFile)
        if not sampling_layer:
            self.iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid sampling file to classify",
                                                level=QgsMessageBar.WARNING)
            return

        self.classification_dialog = \
            ClassificationDialog(self, sampling_layer, self.grid_columns.value(), self.grid_rows.value())
        # adjust some objects in the dockwidget while is classifying
        self.selectSamplingFile.setDisabled(True)
        self.browseSamplingFile.setDisabled(True)
        self.buttonOpenClassificationDialog.setText(u"Classification in progress, click to show")
        # open dialog
        self.classification_dialog.show()

