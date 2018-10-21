# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2018 by Xavier Corredor Llano, SMByC
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
import configparser
import webbrowser
from shutil import copyfile

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog, QDockWidget
from qgis.core import QgsProject, QgsVectorFileWriter, QgsMapLayerProxyModel, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.accuracy_assessment import AccuracyAssessmentDialog
from AcATaMa.core.classification import Classification
from AcATaMa.core.sampling import do_simple_random_sampling, do_stratified_random_sampling, Sampling
from AcATaMa.core.raster import do_clipping_with_shape, get_nodata_value
from AcATaMa.gui.about_dialog import AboutDialog
from AcATaMa.gui.classification_dialog import ClassificationDialog
from AcATaMa.utils.qgis_utils import get_current_file_path_in, \
    unload_layer_in_qgis, valid_file_selected_in, load_and_select_filepath_in
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

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def setup_gui(self):
        # ######### plugin info ######### #
        self.about_dialog = AboutDialog()
        self.QPBtn_PluginInfo.setText("v{}".format(VERSION))
        self.QPBtn_PluginInfo.clicked.connect(self.about_dialog.show)
        self.QPBtn_PluginDocs.clicked.connect(lambda: webbrowser.open("https://smbyc.bitbucket.io/qgisplugins/acatama"))

        # ######### load thematic raster image ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_ThematicRaster.setCurrentIndex(-1)
        self.QCBox_ThematicRaster.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the thematic raster file
        self.QPBtn_browseThematicRaster.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_ThematicRaster,
            dialog_title=self.tr("Select the thematic raster image to evaluate"),
            dialog_types=self.tr("Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # select and check the thematic raster
        self.QCBox_ThematicRaster.currentIndexChanged.connect(self.select_thematic_raster)

        # ######### shape area of interest ######### #
        self.widget_AreaOfInterest.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_AreaOfInterest.setCurrentIndex(-1)
        self.QCBox_AreaOfInterest.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        # call to browse the shape area
        self.QPBtn_browseAreaOfInterest.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_AreaOfInterest,
            dialog_title=self.tr("Select the vector file"),
            dialog_types=self.tr("Vector files (*.gpkg *.shp);;All files (*.*)"),
            layer_type="vector"))
        # do clip
        self.QPBtn_ClippingThematic.clicked.connect(self.clipping_thematic_raster)

        # ######### create categorical  ######### # TODO
        # self.widget_CategRaster.setHidden(True)
        # # handle connect when the list of layers changed
        # # call to browse the categorical raster
        # self.browseCategRaster.clicked.connect(lambda: self.fileDialog_browse(
        #     self.selectCategRaster,
        #     dialog_title=self.tr("Select the categorical raster file"),
        #     dialog_types=self.tr("Raster files (*.tif *.img);;All files (*.*)"),
        #     layer_type="raster"))

        # ######### simple random sampling ######### #
        self.widget_SimpRSwithCR.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_CategRaster_SimpRS.setCurrentIndex(-1)
        self.QCBox_CategRaster_SimpRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the categorical raster
        self.QPBtn_browseCategRaster_SimpRS.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_CategRaster_SimpRS,
            dialog_title=self.tr("Select the categorical raster file"),
            dialog_types=self.tr("Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # select and check the categorical raster
        self.QCBox_CategRaster_SimpRS.currentIndexChanged.connect(self.select_categorical_raster_SimpRS)
        # generate sampling options
        self.widget_generate_SimpRS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_SimpRS.widget_save_sampling_config.setHidden(True)
        iface.mapCanvas().layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_SimpRS.QCBox_SamplingToSave))
        self.widget_generate_SimpRS.QPBtn_SaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_SimpRS.QCBox_SamplingToSave))
        # generate sampling
        self.widget_generate_SimpRS.QPBtn_GenerateSampling.clicked.connect(lambda: do_simple_random_sampling(self))
        # update progress bar limits
        self.numberOfSamples_SimpRS.valueChanged.connect(
            lambda: self.widget_generate_SimpRS.QPBar_GenerateSampling.setValue(0))
        self.numberOfSamples_SimpRS.valueChanged.connect(self.widget_generate_SimpRS.QPBar_GenerateSampling.setMaximum)

        # ######### stratified random sampling ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_CategRaster_StraRS.setCurrentIndex(-1)
        self.QCBox_CategRaster_StraRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the categorical raster
        self.QPBtn_browseCategRaster_StraRS.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_CategRaster_StraRS,
            dialog_title=self.tr("Select the categorical raster file"),
            dialog_types=self.tr("Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))
        # select and check the categorical raster
        self.QCBox_CategRaster_StraRS.currentIndexChanged.connect(self.select_categorical_raster_StraRS)
        self.QCBox_band_CategRaster_StraRS.currentIndexChanged.connect(self.reset_StraRS_method)
        self.nodata_CategRaster_StraRS.valueChanged.connect(self.reset_StraRS_method)
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of categorical raster
        self.widget_TotalExpectedSE.setHidden(True)
        self.QCBox_CategRaster_StraRS.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        self.QCBox_StraRS_Method.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.QTableW_StraRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        # generate sampling options
        self.widget_generate_StraRS.generate_sampling_widget_options.setHidden(True)
        # save config
        self.widget_generate_StraRS.widget_save_sampling_config.setHidden(True)
        iface.mapCanvas().layersChanged.connect(
            lambda: self.update_generated_sampling_list_in(self.widget_generate_StraRS.QCBox_SamplingToSave))
        self.widget_generate_StraRS.QPBtn_SaveSamplingConf.clicked.connect(
            lambda: self.fileDialog_saveSamplingConf(self.widget_generate_StraRS.QCBox_SamplingToSave))
        # generate sampling
        self.widget_generate_StraRS.QPBtn_GenerateSampling.clicked.connect(lambda: do_stratified_random_sampling(self))

        # disable sampling tab at start
        self.scrollAreaWidgetContents_S.setDisabled(True)

        # ######### Classification sampling tab ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_SamplingFile.setCurrentIndex(-1)
        self.QCBox_SamplingFile.setFilters(QgsMapLayerProxyModel.PointLayer)
        # show the classification file settings in plugin when it is selected
        self.QCBox_SamplingFile.currentIndexChanged.connect(self.update_the_status_of_classification)
        # call to browse the sampling file
        self.QPBtn_browseSamplingFile.clicked.connect(lambda: self.fileDialog_browse(
            self.QCBox_SamplingFile,
            dialog_title=self.tr("Select the Sampling points file to classify"),
            dialog_types=self.tr("Vector files (*.gpkg *.shp);;All files (*.*)"),
            layer_type="vector"))
        # call to reload sampling file
        self.QPBtn_reloadSamplingFile.clicked.connect(self.reload_sampling_file)
        # call to load and save classification config
        self.QPBtn_loadClassificationConfig.clicked.connect(self.fileDialog_loadClassificationConfig)
        self.QPBtn_saveClassificationConfig.clicked.connect(self.fileDialog_saveClassificationConfig)
        # save sampling + classification
        self.QPBtn_saveSamplingClassification.clicked.connect(self.fileDialog_saveSamplingClassification)
        # change grid config
        self.grid_columns.valueChanged.connect(lambda: self.set_grid_setting("column"))
        self.grid_rows.valueChanged.connect(lambda: self.set_grid_setting("row"))
        # disable group box that depends of sampling file
        self.QGBox_SamplingClassification.setDisabled(True)
        self.QGBox_saveSamplingClassified.setDisabled(True)

        # connect the action to the run method
        self.QPBtn_OpenClassificationDialog.clicked.connect(self.open_classification_dialog)

        # ######### Accuracy Assessment tab ######### #
        # set properties to QgsMapLayerComboBox
        self.QCBox_SamplingFile_AA.setCurrentIndex(-1)
        self.QCBox_SamplingFile_AA.setFilters(QgsMapLayerProxyModel.PointLayer)
        # set and show the classification file status in AA
        self.QCBox_SamplingFile_AA.currentIndexChanged.connect(self.set_sampling_file_accuracy_assessment)
        # compute the AA and open the result dialog
        self.QPBtn_ComputeViewAccurasyAssessment.clicked.connect(self.open_accuracy_assessment_results)

    @pyqtSlot()
    def fileDialog_browse(self, combo_box, dialog_title, dialog_types, layer_type):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", dialog_types)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path, layer_type)

    @pyqtSlot()
    def select_thematic_raster(self):
        def clear_and_unset_the_thematic_raster():
            self.QCBox_ThematicRaster.setCurrentIndex(-1)
            self.QCBox_band_ThematicRaster.clear()
            self.nodata_ThematicRaster.setValue(-1)
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
        # first check
        if not valid_file_selected_in(self.QCBox_ThematicRaster, "thematic raster"):
            clear_and_unset_the_thematic_raster()
            return
        current_layer = self.QCBox_ThematicRaster.currentLayer()
        # check if thematic raster data type is integer or byte
        if current_layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            clear_and_unset_the_thematic_raster()
            iface.messageBar().pushMessage("AcATaMa", "Error, thematic raster must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_ThematicRaster.clear()
        self.QCBox_band_ThematicRaster.addItems([str(x) for x in range(1, current_layer.bandCount() + 1)])
        # set nodata value of thematic raster in nodata field
        self.nodata_ThematicRaster.setValue(get_nodata_value(current_layer))
        # set/update the units in minimum distance items in sampling tab
        layer_dist_unit = current_layer.crs().mapUnits()
        str_unit = QgsUnitTypes.toString(layer_dist_unit)
        abbr_unit = QgsUnitTypes.toAbbreviatedString(layer_dist_unit)
        # Set the properties of the QdoubleSpinBox based on the QgsUnitTypes of the thematic raster
        # https://qgis.org/api/classQgsUnitTypes.html
        # SimpRS
        self.minDistance_SimpRS.setSuffix(" {}".format(abbr_unit))
        self.minDistance_SimpRS.setToolTip(
            "Minimum distance in {} (units based on thematic raster selected)".format(str_unit))
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
            "Minimum distance in {} (units based on thematic raster selected)".format(str_unit))
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

    @pyqtSlot()
    def select_categorical_raster_SimpRS(self):
        # first check
        if not valid_file_selected_in(self.QCBox_CategRaster_SimpRS, "categorical raster"):
            self.QCBox_band_CategRaster_SimpRS.clear()
            return
        current_layer = self.QCBox_CategRaster_SimpRS.currentLayer()
        # check if categorical raster data type is integer or byte
        if current_layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategRaster_SimpRS.setCurrentIndex(-1)
            self.QCBox_band_CategRaster_SimpRS.clear()
            iface.messageBar().pushMessage("AcATaMa", "Error, categorical raster must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_CategRaster_SimpRS.clear()
        self.QCBox_band_CategRaster_SimpRS.addItems([str(x) for x in range(1, current_layer.bandCount() + 1)])

    @pyqtSlot()
    def select_categorical_raster_StraRS(self):
        # first check
        if not valid_file_selected_in(self.QCBox_CategRaster_StraRS, "categorical raster"):
            self.QCBox_band_CategRaster_StraRS.clear()
            self.nodata_CategRaster_StraRS.setValue(-1)
            return
        current_layer = self.QCBox_CategRaster_StraRS.currentLayer()
        # check if categorical raster data type is integer or byte
        if current_layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategRaster_StraRS.setCurrentIndex(-1)
            self.QCBox_band_CategRaster_StraRS.clear()
            self.nodata_CategRaster_StraRS.setValue(-1)
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, categorical raster must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # set band count
        self.QCBox_band_CategRaster_StraRS.clear()
        self.QCBox_band_CategRaster_StraRS.addItems([str(x) for x in range(1, current_layer.bandCount() + 1)])
        # set the same nodata value if select the thematic raster
        if current_layer == self.QCBox_ThematicRaster.currentLayer():
            self.nodata_CategRaster_StraRS.setValue(self.nodata_ThematicRaster.value())
            return
        self.nodata_CategRaster_StraRS.setValue(get_nodata_value(current_layer))

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
    @error_handler
    def clipping_thematic_raster(self):
        # first check input files requirements
        if not valid_file_selected_in(self.QCBox_ThematicRaster, "thematic raster"):
            return
        if not valid_file_selected_in(self.QCBox_AreaOfInterest, "area of interest shape"):
            return

        # first select the target dir for save the clipping file
        filename, ext = os.path.splitext(get_current_file_path_in(self.QCBox_ThematicRaster))
        ext = ext if ext in [".tif", ".TIF", ".img", ".IMG"] else ".tif"
        suggested_filename = filename + "_clip" + ext

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Select the output file to save the clipping file"),
                                                  suggested_filename,
                                                  self.tr("Tiff files (*.tif);;Img files (*.img);;All files (*.*)"))
        if file_out == '':
            return

        # clipping
        clip_file = do_clipping_with_shape(
            self.QCBox_ThematicRaster.currentLayer(),
            self.QCBox_AreaOfInterest.currentLayer(), file_out,
            get_nodata_value(self.QCBox_ThematicRaster.currentLayer()))
        # copy the style
        thematic_basename = os.path.splitext(get_current_file_path_in(self.QCBox_ThematicRaster))[0]
        if os.path.isfile(thematic_basename + ".qml"):
            copyfile(thematic_basename + ".qml", os.path.splitext(file_out)[0] + ".qml")
        # unload old thematic file
        unload_layer_in_qgis(get_current_file_path_in(self.QCBox_ThematicRaster))
        # load to qgis and update combobox list
        load_and_select_filepath_in(self.QCBox_ThematicRaster, clip_file, "raster")
        self.select_thematic_raster()

        iface.messageBar().pushMessage("AcATaMa", "Clipping the thematic raster with shape, completed",
                                       level=Qgis.Success)

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
    def fileDialog_saveSampling(self, combo_box):
        if combo_box.currentText() not in Sampling.samplings:
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, please select a valid sampling file", level=Qgis.Warning)
            return
        suggested_filename = os.path.splitext(Sampling.samplings[combo_box.currentText()].ThematicR.file_path)[0] \
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

    @pyqtSlot()
    def fileDialog_saveSamplingConf(self, combo_box):
        if combo_box.currentText() not in Sampling.samplings:
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, please select a valid sampling file", level=Qgis.Warning)
            return
        sampling_selected = Sampling.samplings[combo_box.currentText()]
        suggested_filename = os.path.splitext(sampling_selected.ThematicR.file_path)[0] \
                             + "_sampling.ini"
        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling configuration"),
                                                  suggested_filename,
                                                  self.tr("Ini files (*.ini);;All files (*.*)"))
        if file_out != '':
            sampling_selected.save_config(file_out)
            iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success)

    @pyqtSlot()
    def update_the_status_of_classification(self):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer:
            # classification status
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                self.QPBar_ClassificationStatus.setMaximum(classification.num_points)
                self.QPBar_ClassificationStatus.setValue(classification.total_classified)
            else:
                count_samples = len(list(sampling_layer.getFeatures()))
                self.QPBar_ClassificationStatus.setMaximum(count_samples)
                self.QPBar_ClassificationStatus.setValue(0)
            self.QPBar_ClassificationStatus.setTextVisible(True)
            # check if the classification is completed and update in dockwidget status
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
                    self.grid_columns.setValue(2)
                    self.grid_rows.setValue(2)
            if not ClassificationDialog.is_opened:
                # enable group box that depends of sampling file
                self.QGBox_SamplingClassification.setEnabled(True)
                self.QGBox_saveSamplingClassified.setEnabled(True)
        else:
            # return to default values
            self.QPBar_ClassificationStatus.setTextVisible(False)
            self.QPBar_ClassificationStatus.setValue(0)
            self.QLabel_ClassificationStatus.setText("No sampling file selected")
            self.QLabel_ClassificationStatus.setStyleSheet("QLabel {color: gray;}")
            self.grid_columns.setValue(2)
            self.grid_rows.setValue(2)
            # disable group box that depends of sampling file
            self.QGBox_SamplingClassification.setDisabled(True)
            self.QGBox_saveSamplingClassified.setDisabled(True)

        # updated state of sampling file selected for accuracy assessment tab
        self.set_sampling_file_accuracy_assessment()

    @pyqtSlot()
    def reload_sampling_file(self):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer:
            # sampling file valid
            if sampling_layer in Classification.instances:
                classification = Classification.instances[sampling_layer]
                classification.reload_sampling_file()
            else:
                classification = Classification(sampling_layer)
                classification.reload_sampling_file()
            # updated state of sampling file selected for accuracy assessment tab
            self.set_sampling_file_accuracy_assessment()
        else:
            iface.messageBar().pushMessage("AcATaMa", "No sampling file selected",
                                           level=Qgis.Warning)

    @pyqtSlot()
    def set_grid_setting(self, item):
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer in Classification.instances:
            classification = Classification.instances[sampling_layer]
            if item == "column":
                classification.grid_columns = self.grid_columns.value()
            if item == "row":
                classification.grid_rows = self.grid_rows.value()

    @pyqtSlot()
    def fileDialog_loadClassificationConfig(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Restore the configuration and classification status"),
                                                   "", self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))

        if file_path != '' and os.path.isfile(file_path):
            # load classification status from yaml file
            import yaml
            with open(file_path, 'r') as yaml_file:
                try:
                    yaml_config = yaml.load(yaml_file)
                except yaml.YAMLError as err:
                    iface.messageBar().pushMessage("AcATaMa", "Error while read the yaml file classification config",
                                                   level=Qgis.Critical)
                    return
            # load the sampling file save in yaml config
            sampling_filepath = yaml_config["sampling_layer"]
            if not os.path.isfile(sampling_filepath):
                iface.messageBar().pushMessage("AcATaMa",
                                               "Error the sampling file saved in this config file, not exists",
                                               level=Qgis.Critical)
                # TODO: ask for new location of the sampling file
                return

            sampling_layer = load_and_select_filepath_in(self.QCBox_SamplingFile, sampling_filepath, "vector")

            # restore configuration and classification status
            classification = Classification(sampling_layer)
            classification.load_config(yaml_config)

            # reload sampling file status in accuracy assessment
            self.set_sampling_file_accuracy_assessment()

            iface.messageBar().pushMessage("AcATaMa", "File loaded successfully", level=Qgis.Success)

    @pyqtSlot()
    def fileDialog_saveClassificationConfig(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, please select a sampling file to save configuration",
                                           level=Qgis.Warning)
            return
        # get file path to suggest to save but not in tmp directory
        path, filename = os.path.split(get_current_file_path_in(self.QCBox_SamplingFile))
        if self.tmp_dir in path:
            path = os.path.split(get_current_file_path_in(self.QCBox_ThematicRaster))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_config.yml"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save settings and classification status"),
                                                  suggested_filename, self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))
        if file_out != '':
            sampling_layer = self.QCBox_SamplingFile.currentLayer()
            if sampling_layer in Classification.instances:
                Classification.instances[sampling_layer].save_config(file_out)
                iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success)
            else:
                iface.messageBar().pushMessage("AcATaMa",
                                               "Failed to save, there isn't any configuration to save",
                                               level=Qgis.Warning)

    @pyqtSlot()
    def fileDialog_saveSamplingClassification(self):
        if not valid_file_selected_in(self.QCBox_SamplingFile):
            iface.messageBar().pushMessage("AcATaMa", "Error, please first select a sampling file",
                                           level=Qgis.Warning)
            return
        # get instance
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if sampling_layer in Classification.instances:
            classification = Classification.instances[sampling_layer]
            if not classification.is_completed:
                quit_msg = "The classification for this sampling file is not completed, " \
                           "the result will have all sampling partially classified." \
                           "\nDo you want to continue?"
                reply = QMessageBox.question(None, 'The classification is not completed',
                                             quit_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.No:
                    return
        else:
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, the classification for the sampling selected has not been initiated",
                                           level=Qgis.Warning)
            return
        # get file path to suggest to save but not in tmp directory
        path, filename = os.path.split(get_current_file_path_in(self.QCBox_SamplingFile))
        if self.tmp_dir in path:
            path = os.path.split(get_current_file_path_in(self.QCBox_ThematicRaster))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_classified.gpkg"
        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling file with the classification"),
                                                  suggested_filename,
                                                  self.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
        if file_out != '':
            classification.save_sampling_classification(file_out)
            iface.messageBar().pushMessage("AcATaMa", "File saved successfully", level=Qgis.Success)

    @pyqtSlot()
    def open_classification_dialog(self):
        if ClassificationDialog.is_opened:
            self.classification_dialog.activateWindow()
            return
        sampling_layer = self.QCBox_SamplingFile.currentLayer()
        if not sampling_layer:
            iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid sampling file to classify",
                                           level=Qgis.Warning)
            return

        self.classification_dialog = \
            ClassificationDialog(sampling_layer, self.grid_columns.value(), self.grid_rows.value())
        # open dialog
        self.classification_dialog.show()

    @pyqtSlot()
    def set_sampling_file_accuracy_assessment(self):
        sampling_layer = self.QCBox_SamplingFile_AA.currentLayer()
        if sampling_layer:
            # sampling file valid
            if sampling_layer in Classification.instances:
                # classification exists for this file
                classification = Classification.instances[sampling_layer]
                # define if this classification was made with thematic classes
                if not classification.with_thematic_classes:
                    self.QLabel_SamplingFileStatus_AA.setText("Classification was not made with thematic classes")
                    self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: red;}")
                    self.QGBox_AccuracyAssessment.setDisabled(True)
                    return
                # check is the classification is completed and update in dockwidget status
                if classification.is_completed:
                    self.QLabel_SamplingFileStatus_AA.setText("Classification completed ({}/{})".
                                                              format(classification.total_classified,
                                                                     classification.num_points))
                    self.QLabel_SamplingFileStatus_AA.setStyleSheet("QLabel {color: green;}")
                else:
                    self.QLabel_SamplingFileStatus_AA.setText("Classification not completed ({}/{})".
                                                              format(classification.total_classified,
                                                                     classification.num_points))
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
