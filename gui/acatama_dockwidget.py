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
from qgis.core import QgsMapLayerProxyModel, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core import config
from AcATaMa.core.analysis import AccuracyAssessmentWindow
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.core.sampling_design import do_simple_random_sampling, do_stratified_random_sampling, do_systematic_sampling
from AcATaMa.core.map import get_nodata_value
from AcATaMa.gui.about_dialog import AboutDialog
from AcATaMa.gui.generate_sampling_widget import SelectCategoricalMapClasses
from AcATaMa.gui.response_design_window import ResponseDesignWindow
from AcATaMa.utils.others_utils import set_nodata_format
from AcATaMa.utils.qgis_utils import valid_file_selected_in, load_and_select_filepath_in, get_file_path_of_layer
from AcATaMa.utils.sampling_utils import update_stratified_sampling_table, fill_stratified_sampling_table, \
    reload_StraRS_table
from AcATaMa.utils.system_utils import error_handler, block_signals_to, output_file_is_OK

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
        self.QCBox_band_CategMap_SimpRS.currentIndexChanged.connect(self.select_categorical_map_SimpRS)
        self.QPBtn_CategMapClassesSelection_SimpRS.setEnabled(False)
        self.QPBtn_CategMapClassesSelection_SimpRS.clicked.connect(lambda: self.select_categorical_map_classes("simple"))
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
        self.nodata_CategMap_StraRS.textChanged.connect(self.reset_StraRS_method)
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of categorical map
        self.widget_TotalExpectedSE.setHidden(True)
        self.QCBox_StraRS_Method.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        self.QPBtn_reloadSrsTable.clicked.connect(lambda: reload_StraRS_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.QTableW_StraRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        # generation options
        self.widget_generate_StraRS.QPBtn_GenerateSamples.clicked.connect(lambda: do_stratified_random_sampling(self))

        # disable sampling tab at start
        self.scrollAreaWidgetContents_S.setDisabled(True)

        # ######### Systematic Sampling ######### #
        # generation options
        self.widget_generate_SystS.QPBtn_GenerateSamples.clicked.connect(lambda: do_systematic_sampling(self))
        self.PointsSpacing_SystS.valueChanged.connect(self.update_systematic_sampling_progressbar)
        self.QCBox_InitialInsetMode_SystS.currentIndexChanged[int].connect(lambda index: self.InitialInsetFixed_SystS.setVisible(True if index == 1 else False))
        self.InitialInsetFixed_SystS.setHidden(True)
        self.InitialInsetFixed_SystS.valueChanged.connect(self.update_systematic_sampling_progressbar)
        # select and check the categorical map
        self.widget_SystSwithCR.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_CategMap_SystS.setCurrentIndex(-1)
        self.QCBox_CategMap_SystS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # post-stratify sampling
        self.QPBtn_browseCategMap_SystS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_CategMap_SystS,
            dialog_title=self.tr("Select the categorical map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        self.QCBox_CategMap_SystS.layerChanged.connect(self.select_categorical_map_SystS)
        self.QCBox_band_CategMap_SystS.currentIndexChanged.connect(self.select_categorical_map_SystS)
        self.QPBtn_CategMapClassesSelection_SystS.setEnabled(False)
        self.QPBtn_CategMapClassesSelection_SystS.clicked.connect(lambda: self.select_categorical_map_classes("systematic"))
        # others
        self.widget_generate_SystS.QPBar_GenerateSamples.setMaximum(1)
        self.widget_generate_SystS.QPBar_GenerateSamples.setFormat("%v / %m* samples")
        self.widget_generate_SystS.QPBar_GenerateSamples.setToolTip(
            "The total of samples (*) is an estimation based only by\n"
            "the grid definition; the nodata value, the post-stratify\n"
            "and neighborhood aggregation filters make the generated\n"
            "samples less than the total.")

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
        self.widget_saveSamplingLabeled.setHidden(True)
        self.QPBtn_saveSamplingLabeled.clicked.connect(self.file_dialog_save_sampling_labeled)
        # change grid config
        self.grid_columns.valueChanged.connect(lambda: self.set_grid_setting("column"))
        self.grid_rows.valueChanged.connect(lambda: self.set_grid_setting("row"))
        # disable group box that depends on sampling file
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
        # estimator selection action
        self.QCBox_SamplingEstimator_A.currentIndexChanged[int].connect(self.estimator_selection_action)
        # compute the AA and open the result dialog
        self.QPBtn_ComputeTheAccurasyAssessment.clicked.connect(self.open_accuracy_assessment_results)
        # disable group box that depends on sampling file
        self.QLabel_SamplingFileStatus_A.setText("No sampling file selected")
        self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: gray;}")
        self.QGBox_SamplingEstimator_A.setDisabled(True)
        self.QGBox_AccuracyAssessment.setDisabled(True)

    @pyqtSlot()
    def browser_dialog_to_load_file(self, combo_box, dialog_title, file_filters):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", file_filters)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path)

    @pyqtSlot("QgsMapLayer*")
    def select_thematic_map(self, layer):
        def clear_and_unset_the_thematic_map():
            with block_signals_to(self.QCBox_ThematicMap):
                self.QCBox_ThematicMap.setCurrentIndex(-1)
            self.QCBox_band_ThematicMap.clear()
            self.nodata_ThematicMap.setText("")
            # SimpRS
            self.minDistance_SimpRS.setSuffix("")
            self.minDistance_SimpRS.setToolTip("")
            self.minDistance_SimpRS.setValue(0)
            self.widget_generate_SimpRS.QPBar_GenerateSamples.setMaximum(1)
            self.widget_generate_SimpRS.QPBar_GenerateSamples.setValue(0)
            # StraRS
            self.minDistance_StraRS.setSuffix("")
            self.minDistance_StraRS.setToolTip("")
            self.minDistance_StraRS.setValue(0)
            self.widget_generate_StraRS.QPBar_GenerateSamples.setMaximum(1)
            self.widget_generate_StraRS.QPBar_GenerateSamples.setValue(0)
            # SystS
            self.PointsSpacing_SystS.setSuffix("")
            self.PointsSpacing_SystS.setToolTip("")
            self.PointsSpacing_SystS.setValue(0)
            self.InitialInsetFixed_SystS.setSuffix("")
            self.InitialInsetFixed_SystS.setToolTip("")
            self.InitialInsetFixed_SystS.setValue(0)
            self.MaxXYoffset_SystS.setSuffix("")
            self.MaxXYoffset_SystS.setToolTip("")
            self.MaxXYoffset_SystS.setValue(0)
            self.widget_generate_SystS.QPBar_GenerateSamples.setMaximum(1)
            self.widget_generate_SystS.QPBar_GenerateSamples.setValue(0)
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
        self.nodata_ThematicMap.setText(set_nodata_format(get_nodata_value(layer)))
        # set/update the units in minimum distance items in sampling tab
        layer_dist_unit = layer.crs().mapUnits()
        str_unit = QgsUnitTypes.toString(layer_dist_unit)
        # Set the properties of the QdoubleSpinBox based on the QgsUnitTypes of the thematic map
        # https://qgis.org/api/classQgsUnitTypes.html
        # SimpRS
        self.minDistance_SimpRS.setSuffix(" {}".format(str_unit))
        self.minDistance_SimpRS.setToolTip("Minimum distance\n(units based on thematic map selected)")
        self.minDistance_SimpRS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.minDistance_SimpRS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_SimpRS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_SimpRS.setValue(0)
        # StraRS
        self.minDistance_StraRS.setSuffix(" {}".format(str_unit))
        self.minDistance_StraRS.setToolTip("Minimum distance\n(units based on thematic map selected)")
        self.minDistance_StraRS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.minDistance_StraRS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_StraRS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.minDistance_StraRS.setValue(0)
        # SystS
        self.PointsSpacing_SystS.setSuffix(" {}".format(str_unit))
        self.PointsSpacing_SystS.setToolTip(
            "Space between grid points\n(units based on thematic map selected)")
        self.PointsSpacing_SystS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.PointsSpacing_SystS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.PointsSpacing_SystS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.PointsSpacing_SystS.setValue(0)
        #
        self.InitialInsetFixed_SystS.setSuffix(" {}".format(str_unit))
        self.InitialInsetFixed_SystS.setToolTip(
            "Initial inset distance from left-top\n(units based on thematic map selected)")
        self.InitialInsetFixed_SystS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.InitialInsetFixed_SystS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.InitialInsetFixed_SystS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.InitialInsetFixed_SystS.setValue(0)
        #
        self.MaxXYoffset_SystS.setSuffix(" {}".format(str_unit))
        self.MaxXYoffset_SystS.setToolTip(
            "Maximum XY distance from the center to generate the random offset\n(units based on thematic map selected)")
        self.MaxXYoffset_SystS.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        self.MaxXYoffset_SystS.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.MaxXYoffset_SystS.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.MaxXYoffset_SystS.setValue(0)

        # enable sampling tab
        self.scrollAreaWidgetContents_S.setEnabled(True)

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
            # reload sampling file status in accuracy assessment tab
            self.set_sampling_file_in_analysis()

    def select_categorical_map_SimpRS(self):
        self.QPBtn_CategMapClassesSelection_SimpRS.setText("click to select")
        # first check
        if not valid_file_selected_in(self.QCBox_CategMap_SimpRS, "categorical map"):
            self.QCBox_band_CategMap_SimpRS.clear()
            self.QPBtn_CategMapClassesSelection_SimpRS.setEnabled(False)
            return
        categorical_map_layer = self.QCBox_CategMap_SimpRS.currentLayer()
        categorical_map_band = self.QCBox_band_CategMap_SimpRS.currentText()
        categorical_map_band = int(categorical_map_band) if categorical_map_band else 1
        categorical_map_band = 1 if categorical_map_band > categorical_map_layer.bandCount() else categorical_map_band
        # check if categorical map data type is integer or byte
        if categorical_map_layer.dataProvider().dataType(categorical_map_band) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategMap_SimpRS.setCurrentIndex(-1)
            self.QCBox_band_CategMap_SimpRS.clear()
            self.QPBtn_CategMapClassesSelection_SimpRS.setEnabled(False)
            iface.messageBar().pushMessage("AcATaMa", "Error, categorical map must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # fill band list
        if self.QCBox_band_CategMap_SimpRS.count() != categorical_map_layer.bandCount():
            with block_signals_to(self.QCBox_band_CategMap_SimpRS):
                self.QCBox_band_CategMap_SimpRS.clear()
                self.QCBox_band_CategMap_SimpRS.addItems([str(x) for x in range(1, categorical_map_layer.bandCount() + 1)])
        # enable pixel value selection
        self.QPBtn_CategMapClassesSelection_SimpRS.setEnabled(True)
        # update button categorical classes selection
        if (categorical_map_layer, categorical_map_band) in SelectCategoricalMapClasses.instances:
            classes_selection_dialog = SelectCategoricalMapClasses.instances[(categorical_map_layer, categorical_map_band)]
            pixel_values_selected = classes_selection_dialog.classes_selected
            if pixel_values_selected:
                self.QPBtn_CategMapClassesSelection_SimpRS.setText(", ".join(classes_selection_dialog.classes_selected))

    @pyqtSlot("QgsMapLayer*")
    def select_categorical_map_StraRS(self, layer):
        # first deselect/clear sampling method
        self.QCBox_StraRS_Method.setCurrentIndex(-1)
        # check
        if not valid_file_selected_in(self.QCBox_CategMap_StraRS, "categorical map"):
            self.QCBox_band_CategMap_StraRS.clear()
            self.nodata_CategMap_StraRS.setText("")
            self.QGBox_Sampling_Method.setEnabled(False)
            return
        # check if categorical map data type is integer or byte
        if layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategMap_StraRS.setCurrentIndex(-1)
            self.QCBox_band_CategMap_StraRS.clear()
            self.nodata_CategMap_StraRS.setText("")
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
            self.nodata_CategMap_StraRS.setText(set_nodata_format(self.nodata_ThematicMap.text()))
            return
        self.nodata_CategMap_StraRS.setText(set_nodata_format(get_nodata_value(layer)))

    def select_categorical_map_SystS(self):
        self.QPBtn_CategMapClassesSelection_SystS.setText("click to select")
        # first check
        if not valid_file_selected_in(self.QCBox_CategMap_SystS, "categorical map"):
            self.QCBox_band_CategMap_SystS.clear()
            self.QPBtn_CategMapClassesSelection_SystS.setEnabled(False)
            return
        categorical_map_layer = self.QCBox_CategMap_SystS.currentLayer()
        categorical_map_band = self.QCBox_band_CategMap_SystS.currentText()
        categorical_map_band = int(categorical_map_band) if categorical_map_band else 1
        categorical_map_band = 1 if categorical_map_band > categorical_map_layer.bandCount() else categorical_map_band
        # check if categorical map data type is integer or byte
        if categorical_map_layer.dataProvider().dataType(categorical_map_band) not in [1, 2, 3, 4, 5]:
            self.QCBox_CategMap_SystS.setCurrentIndex(-1)
            self.QCBox_band_CategMap_SystS.clear()
            self.QPBtn_CategMapClassesSelection_SystS.setEnabled(False)
            iface.messageBar().pushMessage("AcATaMa", "Error, categorical map must be byte or integer as data type.",
                                           level=Qgis.Warning)
            return
        # fill band list
        if self.QCBox_band_CategMap_SystS.count() != categorical_map_layer.bandCount():
            with block_signals_to(self.QCBox_band_CategMap_SystS):
                self.QCBox_band_CategMap_SystS.clear()
                self.QCBox_band_CategMap_SystS.addItems([str(x) for x in range(1, categorical_map_layer.bandCount() + 1)])
        # enable pixel value selection
        self.QPBtn_CategMapClassesSelection_SystS.setEnabled(True)
        # update button categorical classes selection
        if (categorical_map_layer, categorical_map_band) in SelectCategoricalMapClasses.instances:
            classes_selection_dialog = SelectCategoricalMapClasses.instances[(categorical_map_layer, categorical_map_band)]
            pixel_values_selected = classes_selection_dialog.classes_selected
            if pixel_values_selected:
                self.QPBtn_CategMapClassesSelection_SystS.setText(", ".join(classes_selection_dialog.classes_selected))

    def select_categorical_map_classes(self, sampling_design_type):
        if sampling_design_type == "simple":
            categorical_map_layer = self.QCBox_CategMap_SimpRS.currentLayer()
            categorical_map_band = int(self.QCBox_band_CategMap_SimpRS.currentText())
            QPBtn_CategMapClassesSelection = self.QPBtn_CategMapClassesSelection_SimpRS
        if sampling_design_type == "systematic":
            categorical_map_layer = self.QCBox_CategMap_SystS.currentLayer()
            categorical_map_band = int(self.QCBox_band_CategMap_SystS.currentText())
            QPBtn_CategMapClassesSelection = self.QPBtn_CategMapClassesSelection_SystS

        # check if instance already exists
        if (categorical_map_layer, categorical_map_band) in SelectCategoricalMapClasses.instances:
            classes_selection_dialog = SelectCategoricalMapClasses.instances[(categorical_map_layer, categorical_map_band)]
        else:
            classes_selection_dialog = SelectCategoricalMapClasses(categorical_map_layer, categorical_map_band,
                                                                   QPBtn_CategMapClassesSelection.text())
        # get classes picked by user
        classes_selection_dialog.exec_()
        classes_selected = classes_selection_dialog.classes_selected
        # update button text
        if classes_selected:
            QPBtn_CategMapClassesSelection.setText(", ".join(classes_selection_dialog.classes_selected))
        else:
            QPBtn_CategMapClassesSelection.setText("click to select")

    @pyqtSlot()
    def reset_StraRS_method(self):
        # reinit variable for save tables content
        self.srs_tables = {}
        # clear table
        self.QTableW_StraRS.setRowCount(0)
        self.QTableW_StraRS.setColumnCount(0)
        # clear select
        self.QCBox_StraRS_Method.setCurrentIndex(-1)

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

    def update_systematic_sampling_progressbar(self):
        if not self.QCBox_ThematicMap.currentLayer() or not self.QCBox_ThematicMap.currentLayer().isValid():
            return
        extent = self.QCBox_ThematicMap.currentLayer().extent()
        points_spacing = float(self.PointsSpacing_SystS.value())
        initial_inset = float(self.InitialInsetFixed_SystS.value())
        try:
            max_samples = (int((extent.width()-initial_inset)/points_spacing) + 1) * \
                          (int((extent.height()-initial_inset)/points_spacing) + 1)
        except ZeroDivisionError:
            return
        if max_samples < 2147483647:
            self.widget_generate_SystS.QPBar_GenerateSamples.setMaximum(max_samples)

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
            suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + " - acatama.yml" if filename else "acatama.yml"
        else:
            suggested_filename = "acatama.yml"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save AcATaMa configuration and state"),
                                                  suggested_filename, self.tr("Yaml (*.yaml *.yml);;All files (*.*)"))
        if output_file_is_OK(file_out):
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
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + " - labeled.gpkg" if filename else "samples labeled.gpkg"

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Save sampling file with the response_design"),
                                                  suggested_filename,
                                                  self.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
        if output_file_is_OK(file_out):
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

    @pyqtSlot("QgsMapLayer*")
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
                    self.QGBox_SamplingEstimator_A.setDisabled(True)
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
                self.QGBox_SamplingEstimator_A.setEnabled(True)
                self.QGBox_AccuracyAssessment.setEnabled(self.QCBox_SamplingEstimator_A.currentIndex() != -1)
                self.QCBox_SamplingEstimator_A.setCurrentIndex(response_design.estimator)

            else:
                self.QLabel_SamplingFileStatus_A.setText("Sampling file not labeled")
                self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: red;}")
                self.QGBox_SamplingEstimator_A.setDisabled(True)
                self.QGBox_AccuracyAssessment.setDisabled(True)
        else:
            # not select sampling file
            self.QLabel_SamplingFileStatus_A.setText("No sampling file selected")
            self.QLabel_SamplingFileStatus_A.setStyleSheet("QLabel {color: gray;}")
            self.QGBox_SamplingEstimator_A.setDisabled(True)
            self.QGBox_AccuracyAssessment.setDisabled(True)

    @pyqtSlot(int)
    def estimator_selection_action(self, type_id):
        if not self.QCBox_SamplingFile_A.currentLayer():
            return
        self.QGBox_AccuracyAssessment.setEnabled(type_id != -1)
        # save the estimator in response design instance
        if self.QCBox_SamplingFile_A.currentLayer() in ResponseDesign.instances:
            ResponseDesign.instances[self.QCBox_SamplingFile_A.currentLayer()].estimator = type_id

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
