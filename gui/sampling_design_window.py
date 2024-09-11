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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from qgis.core import QgsMapLayerProxyModel, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.sampling_design import do_simple_random_sampling, do_stratified_random_sampling, do_systematic_sampling
from AcATaMa.utils.sampling_utils import update_stratified_sampling_table, fill_stratified_sampling_table, \
    reload_StraRS_table
from AcATaMa.gui.post_stratification_classes_dialog import PostStratificationClassesDialog
from AcATaMa.utils.qgis_utils import valid_file_selected_in, load_and_select_filepath_in
from AcATaMa.utils.system_utils import block_signals_to
from AcATaMa.utils.others_utils import set_nodata_format, get_nodata_format
from AcATaMa.core.map import get_nodata_value

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'sampling_design_window.ui'))


class SamplingDesignWindow(QDialog, FORM_CLASS):
    is_opened = False
    inst = None

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.thematic_map = None
        SamplingDesignWindow.inst = self

        # flags
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        # ######### simple random sampling ######### #
        self.widget_SimpRSwithPS.setHidden(True)
        self.widget_neighbour_aggregation_SimpRS.setHidden(True)
        self.widget_random_sampling_options_SimpRS.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_PostStratMap_SimpRS.setCurrentIndex(-1)
        self.QCBox_PostStratMap_SimpRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the post-stratification map
        self.QPBtn_browsePostStratMap_SimpRS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_PostStratMap_SimpRS,
            dialog_title=self.tr("Select the post-stratification map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        # select and check the post-stratification map
        self.QCBox_PostStratMap_SimpRS.layerChanged.connect(lambda: self.update_post_stratification_map_SimpRS("layer"))
        self.QCBox_band_PostStratMap_SimpRS.currentIndexChanged.connect(lambda: self.update_post_stratification_map_SimpRS("band"))
        self.nodata_PostStratMap_SimpRS.textChanged.connect(lambda: self.update_post_stratification_map_SimpRS("nodata"))
        self.QPBtn_PostStratMapClasses_SimpRS.setEnabled(False)
        self.QPBtn_PostStratMapClasses_SimpRS.clicked.connect(lambda: self.select_post_stratification_classes("simple"))
        # number of neighbors aggregation
        self.fill_same_class_of_neighbors(self.QCBox_NumberOfNeighbors_SimpRS, self.QCBox_SameClassOfNeighbors_SimpRS)
        self.QCBox_NumberOfNeighbors_SimpRS.currentIndexChanged.connect(lambda: self.fill_same_class_of_neighbors(
            self.QCBox_NumberOfNeighbors_SimpRS, self.QCBox_SameClassOfNeighbors_SimpRS))
        # generation options
        self.QPBtn_GenerateSamples_SimpRS.clicked.connect(do_simple_random_sampling)
        # update progress bar limits
        self.numberOfSamples_SimpRS.valueChanged.connect(
            lambda: self.QPBar_GenerateSamples_SimpRS.setValue(0))
        self.numberOfSamples_SimpRS.valueChanged.connect(self.QPBar_GenerateSamples_SimpRS.setMaximum)

        # ######### stratified random sampling ######### #
        self.widget_neighbour_aggregation_StraRS.setHidden(True)
        self.widget_random_sampling_options_StraRS.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_StratMap_StraRS.setCurrentIndex(-1)
        self.QCBox_StratMap_StraRS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # call to browse the post-stratification raster
        self.QPBtn_browseStratMap_StraRS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_StratMap_StraRS,
            dialog_title=self.tr("Select the post-stratification map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        # select and check the post-stratification map
        self.QCBox_StratMap_StraRS.layerChanged.connect(self.update_stratification_map_StraRS)
        self.QCBox_band_StratMap_StraRS.currentIndexChanged.connect(self.reset_StraRS_method)
        self.nodata_StratMap_StraRS.textChanged.connect(self.reset_StraRS_method)
        # init variable for save tables content
        self.srs_tables = {}
        # fill table of post-stratification map
        self.widget_TotalExpectedSE.setHidden(True)
        self.QCBox_StraRS_Method.currentIndexChanged.connect(lambda: fill_stratified_sampling_table(self))
        self.QPBtn_reloadSrsTable.clicked.connect(lambda: reload_StraRS_table(self))
        # for each item changed in table, save and update it
        self.TotalExpectedSE.valueChanged.connect(lambda: update_stratified_sampling_table(self, "TotalExpectedSE"))
        self.QTableW_StraRS.itemChanged.connect(lambda: update_stratified_sampling_table(self, "TableContent"))
        self.MinimumSamplesPerStratum.valueChanged.connect(lambda: update_stratified_sampling_table(self, "MinimumSamplesPerStratum"))
        # number of neighbors aggregation
        self.fill_same_class_of_neighbors(self.QCBox_NumberOfNeighbors_StraRS, self.QCBox_SameClassOfNeighbors_StraRS)
        self.QCBox_NumberOfNeighbors_StraRS.currentIndexChanged.connect(lambda: self.fill_same_class_of_neighbors(
            self.QCBox_NumberOfNeighbors_StraRS, self.QCBox_SameClassOfNeighbors_StraRS))
        # generation options
        self.QPBtn_GenerateSamples_StraRS.clicked.connect(do_stratified_random_sampling)

        # ######### Systematic Sampling ######### #
        self.widget_neighbour_aggregation_SystS.setHidden(True)
        self.widget_random_sampling_options_SystS.setHidden(True)
        # generation options
        self.QPBtn_GenerateSamples_SystS.clicked.connect(do_systematic_sampling)
        self.PointsSpacing_SystS.valueChanged.connect(self.update_systematic_sampling_progressbar)
        self.QCBox_InitialInsetMode_SystS.currentIndexChanged[int].connect(
            lambda index: self.InitialInsetFixed_SystS.setVisible(True if index == 1 else False))
        self.InitialInsetFixed_SystS.setHidden(True)
        self.InitialInsetFixed_SystS.valueChanged.connect(self.update_systematic_sampling_progressbar)
        # select and check the post-stratification map
        self.widget_SystSwithPS.setHidden(True)
        # set properties to QgsMapLayerComboBox
        self.QCBox_PostStratMap_SystS.setCurrentIndex(-1)
        self.QCBox_PostStratMap_SystS.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # post-stratification sampling
        self.QPBtn_browsePostStratMap_SystS.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_PostStratMap_SystS,
            dialog_title=self.tr("Select the post-stratification map"),
            file_filters=self.tr("Raster files (*.tif *.img);;All files (*.*)")))
        self.QCBox_PostStratMap_SystS.layerChanged.connect(lambda: self.update_post_stratification_map_SystS("layer"))
        self.QCBox_band_PostStratMap_SystS.currentIndexChanged.connect(lambda: self.update_post_stratification_map_SystS("band"))
        self.nodata_PostStratMap_SystS.textChanged.connect(lambda: self.update_post_stratification_map_SystS("nodata"))
        self.QPBtn_PostStratMapClasses_SystS.setEnabled(False)
        self.QPBtn_PostStratMapClasses_SystS.clicked.connect(lambda: self.select_post_stratification_classes("systematic"))
        # number of neighbors aggregation
        self.fill_same_class_of_neighbors(self.QCBox_NumberOfNeighbors_SystS, self.QCBox_SameClassOfNeighbors_SystS)
        self.QCBox_NumberOfNeighbors_SystS.currentIndexChanged.connect(lambda: self.fill_same_class_of_neighbors(
            self.QCBox_NumberOfNeighbors_SystS, self.QCBox_SameClassOfNeighbors_SystS))

        # dialog buttons box
        self.closeButton.rejected.connect(self.closing)
        # disable enter action
        self.closeButton.button(QDialogButtonBox.Close).setAutoDefault(False)

    def setup(self, thematic_map_layer):
        self.thematic_map = thematic_map_layer
        # set/update the units in minimum distance items in sampling tab
        layer_dist_unit = self.thematic_map.crs().mapUnits()
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
            "Initial inset distance\n(units based on thematic map selected)")
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

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.QGBox_ThematicMap.setEnabled(False)
        AcATaMa.dockwidget.widget_sampling_file.setEnabled(False)
        SamplingDesignWindow.is_opened = True
        AcATaMa.dockwidget.QPBtn_OpenSamplingDesignWindow.setText("Sampling design is opened, click to show")

        super(SamplingDesignWindow, self).show()

    @pyqtSlot()
    def browser_dialog_to_load_file(self, combo_box, dialog_title, file_filters):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", file_filters)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path)

    def fill_same_class_of_neighbors(self, QCBox_NumberOfNeighbors, QCBox_SameClassOfNeighbors):
        QCBox_SameClassOfNeighbors.clear()
        number_of_neighbor = int(QCBox_NumberOfNeighbors.currentText())
        QCBox_SameClassOfNeighbors.addItems([str(x) for x in range(1, number_of_neighbor + 1)])

    def update_post_stratification_map_SimpRS(self, item_changed):
        self.QPBtn_PostStratMapClasses_SimpRS.setText("click to select")
        # first check
        if not valid_file_selected_in(self.QCBox_PostStratMap_SimpRS, "post-stratification map"):
            self.QCBox_band_PostStratMap_SimpRS.clear()
            self.nodata_PostStratMap_SimpRS.setText("")
            self.QPBtn_PostStratMapClasses_SimpRS.setEnabled(False)
            return

        post_stratification_map_layer = self.QCBox_PostStratMap_SimpRS.currentLayer()

        if item_changed == "layer":
            # fill band list
            if self.QCBox_band_PostStratMap_SimpRS.count() != post_stratification_map_layer.bandCount():
                with block_signals_to(self.QCBox_band_PostStratMap_SimpRS):
                    self.QCBox_band_PostStratMap_SimpRS.clear()
                    self.QCBox_band_PostStratMap_SimpRS.addItems(
                        [str(x) for x in range(1, post_stratification_map_layer.bandCount() + 1)])
            # fill nodata value
            with block_signals_to(self.nodata_PostStratMap_SimpRS):
                self.nodata_PostStratMap_SimpRS.setText(set_nodata_format(get_nodata_value(post_stratification_map_layer)))

        post_stratification_map_band = int(self.QCBox_band_PostStratMap_SimpRS.currentText())

        # set the nodata value
        if item_changed == "band":
            with block_signals_to(self.nodata_PostStratMap_SimpRS):
                self.nodata_PostStratMap_SimpRS.setText(set_nodata_format(get_nodata_value(post_stratification_map_layer,
                                                                                           post_stratification_map_band)))

        post_stratification_map_nodata = get_nodata_format(self.nodata_PostStratMap_SimpRS.text())

        # check if post-stratification map data type is integer or byte
        if item_changed in ["layer", "band"]:
            if post_stratification_map_layer.dataProvider().dataType(post_stratification_map_band) not in [1, 2, 3, 4, 5]:
                self.QCBox_PostStratMap_SimpRS.setCurrentIndex(-1)
                self.QCBox_band_PostStratMap_SimpRS.clear()
                self.nodata_PostStratMap_SimpRS.setText("")
                self.QPBtn_PostStratMapClasses_SimpRS.setEnabled(False)
                iface.messageBar().pushMessage("AcATaMa", "Error, post-stratification map must be byte or integer as data type.",
                                               level=Qgis.Warning, duration=10)
                return

        # enable pixel value selection
        self.QPBtn_PostStratMapClasses_SimpRS.setEnabled(True)
        # update button post-stratification classes selection
        if (post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata) in PostStratificationClassesDialog.instances:
            classes_selection_dialog = PostStratificationClassesDialog.instances[(post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata)]
            pixel_values_selected = classes_selection_dialog.classes_selected
            if pixel_values_selected:
                self.QPBtn_PostStratMapClasses_SimpRS.setText(", ".join(classes_selection_dialog.classes_selected))

    @pyqtSlot("QgsMapLayer*")
    def update_stratification_map_StraRS(self, layer):
        # first deselect/clear sampling method
        self.QCBox_StraRS_Method.setCurrentIndex(-1)
        # check
        if not valid_file_selected_in(self.QCBox_StratMap_StraRS, "stratification map"):
            self.QCBox_band_StratMap_StraRS.clear()
            self.nodata_StratMap_StraRS.setText("")
            self.QGBox_Sampling_Method.setEnabled(False)
            return
        # check if stratification map data type is integer or byte
        if layer.dataProvider().dataType(1) not in [1, 2, 3, 4, 5]:
            self.QCBox_StratMap_StraRS.setCurrentIndex(-1)
            self.QCBox_band_StratMap_StraRS.clear()
            self.nodata_StratMap_StraRS.setText("")
            self.QGBox_Sampling_Method.setEnabled(False)
            iface.messageBar().pushMessage("AcATaMa",
                                           "Error, stratification map must be byte or integer as data type.",
                                           level=Qgis.Warning, duration=10)
            return
        # set band count
        self.QCBox_band_StratMap_StraRS.clear()
        self.QCBox_band_StratMap_StraRS.addItems([str(x) for x in range(1, layer.bandCount() + 1)])
        self.QGBox_Sampling_Method.setEnabled(True)
        # set the same nodata value if select the thematic map
        if layer == self.thematic_map:
            from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
            self.nodata_StratMap_StraRS.setText(set_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()))
            return
        self.nodata_StratMap_StraRS.setText(set_nodata_format(get_nodata_value(layer)))

    def update_post_stratification_map_SystS(self, item_changed):
        self.QPBtn_PostStratMapClasses_SystS.setText("click to select")
        # first check
        if not valid_file_selected_in(self.QCBox_PostStratMap_SystS, "post-stratification map"):
            self.QCBox_band_PostStratMap_SystS.clear()
            self.nodata_PostStratMap_SystS.setText("")
            self.QPBtn_PostStratMapClasses_SystS.setEnabled(False)
            return

        post_stratification_map_layer = self.QCBox_PostStratMap_SystS.currentLayer()

        if item_changed == "layer":
            # fill band list
            if self.QCBox_band_PostStratMap_SystS.count() != post_stratification_map_layer.bandCount():
                with block_signals_to(self.QCBox_band_PostStratMap_SystS):
                    self.QCBox_band_PostStratMap_SystS.clear()
                    self.QCBox_band_PostStratMap_SystS.addItems(
                        [str(x) for x in range(1, post_stratification_map_layer.bandCount() + 1)])
            # fill nodata value
            with block_signals_to(self.nodata_PostStratMap_SystS):
                self.nodata_PostStratMap_SystS.setText(set_nodata_format(get_nodata_value(post_stratification_map_layer)))

        post_stratification_map_band = int(self.QCBox_band_PostStratMap_SystS.currentText())

        # set the nodata value
        if item_changed == "band":
            with block_signals_to(self.nodata_PostStratMap_SystS):
                self.nodata_PostStratMap_SystS.setText(set_nodata_format(get_nodata_value(post_stratification_map_layer,
                                                                                           post_stratification_map_band)))

        post_stratification_map_nodata = get_nodata_format(self.nodata_PostStratMap_SystS.text())

        # check if post-stratification map data type is integer or byte
        if item_changed in ["layer", "band"]:
            if post_stratification_map_layer.dataProvider().dataType(post_stratification_map_band) not in [1, 2, 3, 4, 5]:
                self.QCBox_PostStratMap_SystS.setCurrentIndex(-1)
                self.QCBox_band_PostStratMap_SystS.clear()
                self.nodata_PostStratMap_SystS.setText("")
                self.QPBtn_PostStratMapClasses_SystS.setEnabled(False)
                iface.messageBar().pushMessage("AcATaMa", "Error, post-stratification map must be byte or integer as data type.",
                                               level=Qgis.Warning, duration=10)
                return

        # enable pixel value selection
        self.QPBtn_PostStratMapClasses_SystS.setEnabled(True)
        # update button post-stratification classes selection
        if (post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata) in PostStratificationClassesDialog.instances:
            classes_selection_dialog = PostStratificationClassesDialog.instances[(post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata)]
            pixel_values_selected = classes_selection_dialog.classes_selected
            if pixel_values_selected:
                self.QPBtn_PostStratMapClasses_SystS.setText(", ".join(classes_selection_dialog.classes_selected))

    def select_post_stratification_classes(self, sampling_design_type):
        if sampling_design_type == "simple":
            post_stratification_map_layer = self.QCBox_PostStratMap_SimpRS.currentLayer()
            post_stratification_map_band = int(self.QCBox_band_PostStratMap_SimpRS.currentText())
            post_stratification_map_nodata = get_nodata_format(self.nodata_PostStratMap_SimpRS.text())
            QPBtn_PostStratMapClasses = self.QPBtn_PostStratMapClasses_SimpRS
        if sampling_design_type == "systematic":
            post_stratification_map_layer = self.QCBox_PostStratMap_SystS.currentLayer()
            post_stratification_map_band = int(self.QCBox_band_PostStratMap_SystS.currentText())
            post_stratification_map_nodata = get_nodata_format(self.nodata_PostStratMap_SystS.text())
            QPBtn_PostStratMapClasses = self.QPBtn_PostStratMapClasses_SystS

        # check if instance already exists
        if (post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata) \
                in PostStratificationClassesDialog.instances:
            classes_selection_dialog = PostStratificationClassesDialog.instances[(post_stratification_map_layer,
                                                                                  post_stratification_map_band,
                                                                                  post_stratification_map_nodata)]
        else:
            classes_selection_dialog = PostStratificationClassesDialog(post_stratification_map_layer,
                                                                       post_stratification_map_band,
                                                                       post_stratification_map_nodata,
                                                                       QPBtn_PostStratMapClasses.text())
        # get classes picked by user
        classes_selection_dialog.exec_()
        classes_selected = classes_selection_dialog.classes_selected
        # update button text
        if classes_selected:
            QPBtn_PostStratMapClasses.setText(", ".join(classes_selection_dialog.classes_selected))
        else:
            QPBtn_PostStratMapClasses.setText("click to select")

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
    def update_systematic_sampling_progressbar(self):
        if not self.thematic_map or not self.thematic_map.isValid():
            return
        extent = self.thematic_map.extent()
        points_spacing = float(self.PointsSpacing_SystS.value())
        initial_inset = float(self.InitialInsetFixed_SystS.value())
        try:
            max_samples = (int((extent.width()-initial_inset)/points_spacing) + 1) * \
                          (int((extent.height()-initial_inset)/points_spacing) + 1)
        except ZeroDivisionError:
            return
        if max_samples < 2147483647:
            self.QPBar_GenerateSamples_SystS.setMaximum(max_samples)

    @pyqtSlot()
    def clear(self):
        # SimpRS
        self.minDistance_SimpRS.setSuffix("")
        self.minDistance_SimpRS.setToolTip("")
        self.minDistance_SimpRS.setValue(0)
        self.QPBar_GenerateSamples_SimpRS.setMaximum(1)
        self.QPBar_GenerateSamples_SimpRS.setValue(0)
        # StraRS
        self.minDistance_StraRS.setSuffix("")
        self.minDistance_StraRS.setToolTip("")
        self.minDistance_StraRS.setValue(0)
        self.QPBar_GenerateSamples_StraRS.setMaximum(1)
        self.QPBar_GenerateSamples_StraRS.setValue(0)
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
        self.QPBar_GenerateSamples_SystS.setMaximum(1)
        self.QPBar_GenerateSamples_SystS.setValue(0)

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the response design window
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        from AcATaMa.core.analysis import AccuracyAssessmentWindow
        from AcATaMa.gui.response_design_window import ResponseDesignWindow
        AcATaMa.dockwidget.QPBtn_OpenSamplingDesignWindow.setText("Sampling design window")
        AcATaMa.dockwidget.widget_sampling_file.setEnabled(True)
        if not ResponseDesignWindow.is_opened and not AccuracyAssessmentWindow.is_opened:
            AcATaMa.dockwidget.QGBox_ThematicMap.setEnabled(True)
        SamplingDesignWindow.is_opened = False
        self.thematic_map = None
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(SamplingDesignWindow, self).reject()