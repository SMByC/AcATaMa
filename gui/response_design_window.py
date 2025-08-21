# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2025 by Xavier C. Llano, SMByC
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
import uuid

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSlot, QEventLoop, QTimer, QEvent
from qgis.PyQt.QtWidgets import QTableWidgetItem, QSplitter, QColorDialog, QDialog, QDialogButtonBox, QPushButton, \
    QMessageBox, QWidget, QLabel, QShortcut
from qgis.PyQt.QtGui import QColor, QIcon, QKeyEvent
from qgis.PyQt.sip import isdeleted
from qgis.gui import QgsRubberBand
from qgis.utils import iface
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, Qgis, QgsProject, QgsUnitTypes, \
    QgsRectangle, QgsPointXY, QgsGeometry, QgsWkbTypes

from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.qgis_utils import valid_file_selected_in, get_current_file_path_in, \
    load_and_select_filepath_in, get_symbology_table
from AcATaMa.core.map import get_values_and_colors_table
from AcATaMa.utils.system_utils import open_file, block_signals_to, error_handler
from AcATaMa.gui.response_design_view_widget import LabelingViewWidget
from AcATaMa.utils.others_utils import get_nodata_format, get_decimal_places

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'response_design_window.ui'))


class ResponseDesignWindow(QDialog, FORM_CLASS):
    is_opened = False
    view_widgets = []
    current_sample = None
    inst = None
    # Store all active shortcuts for cleanup
    active_shortcuts = {}

    def __init__(self, sampling_layer, columns, rows):
        QDialog.__init__(self)
        self.sampling_layer = sampling_layer
        self.setupUi(self)
        ResponseDesignWindow.inst = self

        # flags
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        # get response design done from sampling layer or init new instance
        if sampling_layer in ResponseDesign.instances:
            self.response_design = ResponseDesign.instances[sampling_layer]
        else:
            self.response_design = ResponseDesign(sampling_layer)
            self.response_design.grid_columns = columns
            self.response_design.grid_rows = rows

        #### setting up the response design window

        # set dialog title
        self.setWindowTitle("Response Design Window - " + sampling_layer.name())
        # resize the response design window
        if self.response_design.dialog_size:
            self.resize(*self.response_design.dialog_size)

        # disable enter action
        self.QPBtn_unlabelSampleButton.setAutoDefault(False)

        # go to sample ID action
        self.GoTo_ID_Button.clicked.connect(self.go_to_sample_id)
        self.GoTo_ID.returnPressed.connect(self.go_to_sample_id)
        self.GoTo_ID.textChanged.connect(lambda: self.GoTo_ID.setStyleSheet(""))

        # set up the Continuous Change Detection widget
        self.QPBtn_CCDPlugin.clicked.connect(self.ccd_plugin_widget)

        # open in Google Earth
        self.QPBtn_OpenInGE.clicked.connect(self.open_current_point_in_google_engine)

        # set properties and default value for zoom to the sample spinBox based on sampling file
        layer_dist_unit = self.sampling_layer.crs().mapUnits()
        str_unit = QgsUnitTypes.toString(layer_dist_unit)
        abbr_unit = QgsUnitTypes.toAbbreviatedString(layer_dist_unit)
        self.radiusFitToSample.setSuffix(" {}".format(abbr_unit))
        self.radiusFitToSample.setToolTip(
            "Set the default zoom radius for samples\n"
            "(units in {} based on sampling file selected)".format(str_unit))
        self.radiusFitToSample.setRange(0, 360 if layer_dist_unit == QgsUnitTypes.DistanceDegrees else 10e6)
        decimal_places = get_decimal_places(for_crs=self.sampling_layer.crs())
        self.radiusFitToSample.setDecimals(decimal_places)
        self.radiusFitToSample.setSingleStep(10**-decimal_places)
        self.radiusFitToSample.setValue(self.response_design.fit_to_sample)

        # set total samples
        self.QPBar_SamplesNavigation.setMaximum(len(self.response_design.points))

        # restore the auto next sample button status
        self.autoNextSample.setChecked(self.response_design.auto_next_sample)

        # actions for fit and go to current sample
        self.radiusFitToSample.valueChanged.connect(lambda: self.show_and_go_to_current_sample(highlight=False))
        self.currentSample.clicked.connect(lambda: self.show_and_go_to_current_sample(highlight=True))

        # move through samples
        self.nextSample.clicked.connect(self.next_sample)
        self.nextSampleNotLabeled.clicked.connect(self.next_sample_not_labeled)
        self.previousSample.clicked.connect(self.previous_sample)
        self.previousSampleNotLabeled.clicked.connect(self.previous_sample_not_labeled)

        # dialog buttons box
        self.closeButton.rejected.connect(self.closing)
        # disable enter action
        self.closeButton.button(QDialogButtonBox.Close).setAutoDefault(False)

        # init current sample
        self.current_sample_idx = self.response_design.current_sample_idx
        self.current_sample = None
        self.pixel_tile = None
        self.sampling_unit = None
        self.SamplingUnit_Size.setCurrentIndex(self.response_design.sampling_unit_pixel_buffer)
        self.set_current_sample()
        self.change_sampling_unit_color(color=self.response_design.sampling_unit_color)
        self.SamplingUnit_Color.clicked.connect(self.change_sampling_unit_color)
        self.SamplingUnit_Size.currentIndexChanged.connect(self.show_the_sampling_unit)
        # set labeling buttons
        self.labeling_btns_config = LabelingButtonsConfig(self.response_design.buttons_config)
        self.create_labeling_buttons(buttons_config=self.response_design.buttons_config)
        self.QPBtn_LabelingSetup.clicked.connect(self.open_labeling_setup_dialog)
        self.QPBtn_unlabelSampleButton.clicked.connect(self.unlabel_sample)

        # create dynamic size of the view render widgets windows
        # inside the grid with columns x rows divide by splitters
        h_splitters = []
        view_widgets = []
        for row in range(self.response_design.grid_rows):
            splitter = QSplitter(Qt.Horizontal)
            for column in range(self.response_design.grid_columns):
                new_view_widget = LabelingViewWidget()
                splitter.addWidget(new_view_widget)
                h_splitters.append(splitter)
                view_widgets.append(new_view_widget)
        v_splitter = QSplitter(Qt.Vertical)
        for splitter in h_splitters:
            v_splitter.addWidget(splitter)
        # add to response design window
        self.widget_view_windows.layout().addWidget(v_splitter)
        # save instances
        ResponseDesignWindow.view_widgets = view_widgets
        # setup view widget
        [view_widget.setup_view_widget(sampling_layer) for view_widget in ResponseDesignWindow.view_widgets]
        for idx, view_widget in enumerate(ResponseDesignWindow.view_widgets): view_widget.id = idx
        # set the label names for each view
        for num_view, view_widget in enumerate(ResponseDesignWindow.view_widgets):
            view_widget.QLabel_ViewName.setPlaceholderText("View {}".format(num_view + 1))
        # restore view widgets status
        for config_id, view_config in self.response_design.view_widgets_config.items():
            for view_widget in ResponseDesignWindow.view_widgets:
                if config_id == view_widget.id:
                    view_widget = ResponseDesignWindow.view_widgets[config_id]
                    # select the file for this view widget if exists and is loaded in Qgis
                    layer_name = view_config["layer_name"]
                    if not layer_name and view_config["render_file_path"]:
                        layer_name = os.path.splitext(os.path.basename(view_config["render_file_path"]))[0]
                    file_index = view_widget.QCBox_RenderFile.findText(layer_name, Qt.MatchFixedString)

                    if file_index != -1:
                        # select layer if exists in Qgis
                        with block_signals_to(view_widget.QCBox_RenderFile):
                            view_widget.QCBox_RenderFile.setCurrentIndex(file_index)
                    elif view_config["render_file_path"] and os.path.isfile(view_config["render_file_path"]):
                        # load file and select in view if this exists and not load in Qgis
                        load_and_select_filepath_in(view_widget.QCBox_RenderFile, view_config["render_file_path"],
                                                    layer_name=layer_name)
                    elif view_config["render_file_path"] and not os.path.isfile(view_config["render_file_path"]):
                        self.MsgBar.pushMessage(
                            "Could not to load the layer '{}' in the view {}: no such file {}".format(
                                layer_name,
                                "'{}'".format(view_config["view_name"]) if view_config["view_name"] else view_widget.id + 1,
                                view_config["render_file_path"]), level=Qgis.Warning, duration=0)
                    else:
                        self.MsgBar.pushMessage(
                            "Could not to load the layer '{}' in the view {} (for network layers use save/load a Qgis project)".format(
                                layer_name,
                                "'{}'".format(view_config["view_name"]) if view_config["view_name"] else view_widget.id + 1),
                            level=Qgis.Warning, duration=0)
                    # TODO: restore size by view widget
                    # view_widget.resize(*view_config["view_size"])
                    view_widget.QLabel_ViewName.setText(view_config["view_name"])
                    view_widget.scaleFactor.setValue(view_config["scale_factor"])
                    # active render layer in canvas
                    view_widget.set_render_layer(view_widget.QCBox_RenderFile.currentLayer())

        #### CCD widget
        self.widget_ccd.setVisible(False)
        ccd_widget_layout = self.widget_ccd.layout()
        try:
            from qgis.PyQt.QtWebKit import QWebSettings  # check first if the QtWebKit is available in QT5 client
            from CCD_Plugin.CCD_Plugin import CCD_Plugin
            from CCD_Plugin.gui.CCD_Plugin_dockwidget import CCD_PluginDockWidget
            from CCD_Plugin.utils.config import get_plugin_config, restore_plugin_config
            self.ccd_plugin_available = True
        except ImportError:
            label = QLabel("\nError: Continuous Change Detection (CCD) plugin is not available in your Qgis instance.\n"
                           "To integrate the CCD inside AcATaMa, go to the plugin managing in Qgis and search\n"
                           "CCD-Plugin, install it and restart the response design window.\n\n"
                           "CCD helps to analyze the trends and breakpoints of change of the samples over multi-year\n"
                           "time series using Landsat and Sentinel.\n", self)
            label.setAlignment(Qt.AlignCenter)
            ccd_widget_layout.addWidget(label)
            ccd_widget_layout.setAlignment(Qt.AlignCenter)
            self.ccd_plugin_available = False
            self.response_design.ccd_plugin_opened = True

        if self.ccd_plugin_available:
            # Remove all widgets from the layout
            for i in reversed(range(ccd_widget_layout.count())):
                ccd_widget_layout.itemAt(i).widget().setParent(None)

            # create the ccd widget
            self.ccd_plugin = CCD_Plugin(iface)
            view_canvas = [view_widget.render_widget.canvas for view_widget in ResponseDesignWindow.view_widgets]
            self.ccd_plugin.widget = CCD_PluginDockWidget(id=self.ccd_plugin.id, canvas=view_canvas, parent=self)
            # adjust the dockwidget (ccd_widget) as a normal widget
            self.ccd_plugin.widget.setWindowFlags(Qt.Widget)
            self.ccd_plugin.widget.setWindowFlag(Qt.WindowCloseButtonHint, False)
            self.ccd_plugin.widget.setFloating(False)
            self.ccd_plugin.widget.setTitleBarWidget(QWidget(None))
            self.ccd_plugin.widget.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
            self.ccd_plugin.widget.setContentsMargins(0, 0, 0, 0)
            self.ccd_plugin.widget.setStyleSheet("QDockWidget { border: 0px; }")
            self.ccd_plugin.widget.MainWidget.layout().setContentsMargins(0, 0, 0, 3)
            self.ccd_plugin.widget.MainWidget.layout().setSpacing(3)
            # other adjustments
            self.ccd_plugin.widget.auto_generate_plot.setToolTip("Automatically generate plot when a new sample/marker is set")
            # init tmp dir for all process and intermediate files
            if self.ccd_plugin.tmp_dir:
                self.ccd_plugin.removes_temporary_files()
            self.ccd_plugin.tmp_dir = tempfile.mkdtemp()
            # replace the "widget_ccd" UI widget inside the response design window with the ccd widget
            ccd_widget_layout.insertWidget(0, self.ccd_plugin.widget)
            ccd_widget_layout.update()

            # restore the configuration of the ccd plugin
            self.QPBtn_CCDPlugin.setChecked(self.response_design.ccd_plugin_opened)
            self.widget_ccd.setVisible(self.response_design.ccd_plugin_opened)
            restore_plugin_config(self.ccd_plugin.id, self.response_design.ccd_plugin_config)

        # Install event filter for keyboard events
        self.installEventFilter(self)
        self.scrollArea.installEventFilter(self)
        for view_widget in ResponseDesignWindow.view_widgets:
            view_widget.render_widget.canvas.installEventFilter(self)

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        ResponseDesignWindow.is_opened = True
        # adjust some objects in the dockwidget while response design window is opened
        AcATaMa.dockwidget.QGBox_ThematicMap.setDisabled(True)
        AcATaMa.dockwidget.QGBox_SamplingDesign.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_GridSettings.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_saveSamplingLabeled.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_OpenResponseDesignWindow.setText("Response design is opened, click to show")

        super(ResponseDesignWindow, self).show()
        self.show_and_go_to_current_sample()

    def set_current_sample(self):
        # clear all message bar
        self.MsgBar.clearWidgets()
        # set the current sample
        if self.current_sample_idx < len(self.response_design.points):
            self.current_sample = self.response_design.points[self.current_sample_idx]
        else:
            self.current_sample = self.response_design.points[-1]
            self.current_sample_idx = len(self.response_design.points) - 1
        ResponseDesignWindow.current_sample = self.current_sample
        self.response_design.current_sample_idx = self.current_sample_idx
        # update progress bar
        self.QPBar_SamplesNavigation.setValue(self.current_sample_idx + 1)
        # show the sample ID
        self.Sample_ID.setText(str(self.current_sample.sample_id))
        # show the label assigned
        self.update_sample_status()
        # show and go to marker
        self.show_and_go_to_current_sample()

    @pyqtSlot()
    def go_to_sample_id(self):
        try:
            sample_id = int(self.GoTo_ID.text())
            # find the sample point with ID
            sample_point = next((x for x in self.response_design.points if x.sample_id == sample_id), None)
            # go to sample
            self.current_sample_idx = self.response_design.points.index(sample_point)
            self.set_current_sample()
        except:
            self.GoTo_ID.setStyleSheet("color: red")

    @pyqtSlot(bool)
    def ccd_plugin_widget(self, checked):
        if checked:
            self.widget_ccd.setVisible(True)
            self.set_current_sample_in_ccd()
        else:
            self.widget_ccd.setVisible(False)

    def set_current_sample_in_ccd(self):
        if not hasattr(self, "ccd_plugin") or not self.ccd_plugin.widget or not self.ccd_plugin_available:
            return

        # get the coordinates of the current sample
        crsSrc = QgsCoordinateReferenceSystem(self.sampling_layer.crs())
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        # forward transformation: src -> dest
        point = xform.transform(self.current_sample.QgsPnt)
        # set the current sample in the CCD plugin
        self.ccd_plugin.widget.longitude.setValue(point.x())
        self.ccd_plugin.widget.latitude.setValue(point.y())

        if self.QPBtn_CCDPlugin.isChecked() and self.ccd_plugin.widget.auto_generate_plot.isChecked():
            from CCD_Plugin.gui.CCD_Plugin_dockwidget import PickerCoordsOnMap
            PickerCoordsOnMap.delete_markers()
            self.ccd_plugin.widget.new_plot()

    @pyqtSlot()
    @error_handler
    def open_current_point_in_google_engine(self):
        # convert coordinates
        crsSrc = QgsCoordinateReferenceSystem(self.sampling_layer.crs())
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        # forward transformation: src -> dest
        point = xform.transform(self.current_sample.QgsPnt)

        # make file and save
        description = "Labeled as: <font color='{color}'><b> {label_name}</b></font><br/>" \
                      "Samp. file: <em> {samp_file} </em><br/>AcATaMa Qgis-plugin".format(
            color=self.response_design.buttons_config[self.current_sample.label_id][
                "color"] if self.current_sample.label_id else "gray",
            label_name=self.response_design.buttons_config[self.current_sample.label_id][
                "name"] if self.current_sample.label_id else "not labeled",
            samp_file=self.sampling_layer.name())
        kml_raw = """<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
              <Placemark>
                <name>{name}</name>
                <description>{desc}</description>
                <Point>
                  <coordinates>{lon},{lat}</coordinates>
                </Point>
              </Placemark>
            </kml>""".format(name="Sampling Point ID {}".format(self.current_sample.sample_id),
                             desc=description, lon=point.x(), lat=point.y())
        # create temp file
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        kml_file = os.path.join(AcATaMa.dockwidget.tmp_dir, "point_id_{}_{}.kml".format(self.current_sample.sample_id,
                                                                                        uuid.uuid4().hex[0:7]))
        with open(kml_file, "w") as f:
            f.writelines(kml_raw)
        open_file(kml_file)

    @pyqtSlot(int)
    def label_sample(self, label_id):
        if label_id:
            self.response_design.label_the_current_sample(int(label_id))
            self.update_sample_status()
            self.highlight_thematic_pixel()
            if self.autoNextSample.isChecked():
                # automatically follows the next sample
                self.next_sample()

    @pyqtSlot()
    def unlabel_sample(self):
        self.response_design.label_the_current_sample(False)
        self.update_sample_status()
        self.highlight_thematic_pixel()
        if self.autoNextSample.isChecked():
            # automatically follows the next sample
            self.next_sample()

    def update_labeling_button_activation(self):
        # restore labeling button checked status based on the label of the current sample
        if self.current_sample.label_id is None or self.current_sample.label_id not in self.response_design.buttons_config:
            for i in range(self.Grid_LabelingButtons.count()):
                self.Grid_LabelingButtons.itemAtPosition(i, 0).widget().setChecked(False)
            return

        label_name = self.response_design.buttons_config[self.current_sample.label_id]["name"]
        for i in range(self.Grid_LabelingButtons.count()):
            if self.Grid_LabelingButtons.itemAtPosition(i, 0):
                self.Grid_LabelingButtons.itemAtPosition(i, 0).widget().setChecked(
                    label_name == self.Grid_LabelingButtons.itemAtPosition(i, 0).widget().text())

    def update_sample_status(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        if self.current_sample.is_labeled:
            if self.current_sample.label_id in self.response_design.buttons_config:
                label_name = self.response_design.buttons_config[self.current_sample.label_id]["name"]
                self.statusCurrentSample.setText(label_name)
                self.statusCurrentSample.setStyleSheet(
                    'QLabel {color: ' + self.response_design.buttons_config[self.current_sample.label_id]["color"] + ';}')
                # clear all message bar
                self.MsgBar.clearWidgets()
            else:
                self.statusCurrentSample.setText("Invalid button {}".format(self.current_sample.label_id))
                self.statusCurrentSample.setStyleSheet('QLabel {color: red;}')
                self.MsgBar.pushMessage(
                    "This sample was labeled with invalid/deleted item, fix the labeling buttons "
                    "or relabel the sample", level=Qgis.Critical, duration=20)
        else:
            self.statusCurrentSample.setText("not labeled")
            self.statusCurrentSample.setStyleSheet('QLabel {color: gray;}')
        # update labeling status bar
        self.QPBar_LabelingStatus.setMaximum(self.response_design.num_points)
        self.QPBar_LabelingStatus.setValue(self.response_design.total_labeled)
        # update checked status of the labeling button
        self.update_labeling_button_activation()
        # update plugin with the current sampling status
        AcATaMa.dockwidget.update_response_design_state()

    def highlight_thematic_pixel(self):
        # highlight thematic pixel respectively of the current sampling point
        thematic_pixel = self.current_sample.get_thematic_pixel_edges()
        if thematic_pixel and self.current_sample.label_id:
            fill_color = QColor(self.response_design.buttons_config[self.current_sample.label_id]["color"])
            highlight_pixel_tile = \
                Tile(*thematic_pixel, QColor("black"), fill_color=fill_color)
            highlight_pixel_tile.show()
        # wait
        loop = QEventLoop()
        QTimer.singleShot(300, loop.quit)
        loop.exec_()
        # delete
        if thematic_pixel and self.current_sample.label_id:
            highlight_pixel_tile.hide()
        # wait
        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec_()

    @pyqtSlot()
    def change_sampling_unit_color(self, color=None):
        if not color:
            color = QColorDialog.getColor(self.response_design.sampling_unit_color, self)
        if color.isValid():
            self.response_design.sampling_unit_color = color
            self.SamplingUnit_Color.setStyleSheet("QToolButton{{background-color:{};}}".format(color.name()))
            self.show_the_sampling_unit()

    @pyqtSlot()
    def show_the_sampling_unit(self):
        if self.sampling_unit:
            self.sampling_unit.hide()
        pixel_buffer = int(self.SamplingUnit_Size.currentText())
        self.response_design.sampling_unit_pixel_buffer = pixel_buffer
        if pixel_buffer > 0:
            sampling_unit = self.current_sample.get_thematic_pixel_edges(with_buffer=pixel_buffer)
            if sampling_unit:
                self.sampling_unit = Tile(*sampling_unit, self.response_design.sampling_unit_color)
                self.sampling_unit.show()

    @pyqtSlot()
    def show_the_current_pixel(self):
        # show the edges of the thematic pixel of the current sample
        if self.pixel_tile:
            self.pixel_tile.hide()
        thematic_pixel = self.current_sample.get_thematic_pixel_edges()
        if thematic_pixel:
            self.pixel_tile = Tile(*thematic_pixel, QColor("black"))
            self.pixel_tile.show()

    @pyqtSlot(bool)
    def show_and_go_to_current_sample(self, highlight=True):
        for view_widget in ResponseDesignWindow.view_widgets:
            if view_widget.is_active:
                # fit to current point
                self.current_sample.fit_to(view_widget, self.radiusFitToSample.value())
                # create the marker
                view_widget.render_widget.marker.show(self.current_sample)
                if highlight and view_widget.render_widget.canvas.renderFlag():
                    # highlight to marker
                    view_widget.render_widget.marker.highlight()

        self.show_the_current_pixel()
        self.show_the_sampling_unit()
        # set the current sample in the CCD plugin
        self.set_current_sample_in_ccd()

    @pyqtSlot()
    def next_sample(self):
        if self.current_sample_idx >= len(self.response_design.points) - 1:
            return
        self.current_sample_idx += 1
        self.set_current_sample()

    @pyqtSlot()
    def next_sample_not_labeled(self):
        tmp_sample_idx = self.current_sample_idx + 1
        while tmp_sample_idx < len(self.response_design.points) and \
                self.response_design.points[tmp_sample_idx].is_labeled:
            tmp_sample_idx += 1
        if tmp_sample_idx < len(self.response_design.points) and \
                not self.response_design.points[tmp_sample_idx].is_labeled:
            self.current_sample_idx = tmp_sample_idx
            self.set_current_sample()

    @pyqtSlot()
    def previous_sample(self):
        if self.current_sample_idx < 1:
            return
        self.current_sample_idx -= 1
        self.set_current_sample()

    @pyqtSlot()
    def previous_sample_not_labeled(self):
        tmp_sample_idx = self.current_sample_idx - 1
        while self.response_design.points[tmp_sample_idx].is_labeled \
                and tmp_sample_idx >= 0:
            tmp_sample_idx -= 1
        if not self.response_design.points[tmp_sample_idx].is_labeled and tmp_sample_idx >= 0:
            self.current_sample_idx = tmp_sample_idx
            self.set_current_sample()

    def eventFilter(self, obj, event):
        """Event filter to handle keyboard events."""
        if event.type() == QEvent.KeyPress:
            # Check for Ctrl modifier key combinations
            if event.modifiers() == Qt.ControlModifier:
                if event.key() == Qt.Key_Left:  # Ctrl+Left arrow key
                    self.previous_sample_not_labeled()
                    return True
                elif event.key() == Qt.Key_Right:  # Ctrl+Right arrow key
                    self.next_sample_not_labeled()
                    return True
            # Handle regular key press without modifiers
            elif event.modifiers() == Qt.NoModifier:
                if event.key() == Qt.Key_Left:  # Left arrow key
                    self.previous_sample()
                    return True
                elif event.key() == Qt.Key_Right:  # Right arrow key
                    self.next_sample()
                    return True
                elif event.key() == Qt.Key_Up:  # Up arrow key - zoom out
                    self.zoom_out_canvas()
                    return True
                elif event.key() == Qt.Key_Down:  # Down arrow key - zoom in
                    self.zoom_in_canvas()
                    return True

        # For any other event, pass it to the parent's event filter
        return super().eventFilter(obj, event)

    def zoom_in_canvas(self):
        """Zoom in all active view widget canvases."""
        zoom_factor = 1.2  # 20% zoom in
        for view_widget in ResponseDesignWindow.view_widgets:
            if view_widget.is_active:
                view_widget.render_widget.canvas.zoomByFactor(zoom_factor)

    def zoom_out_canvas(self):
        """Zoom out all active view widget canvases."""
        zoom_factor = 0.8  # 20% zoom out
        for view_widget in ResponseDesignWindow.view_widgets:
            if view_widget.is_active:
                view_widget.render_widget.canvas.zoomByFactor(zoom_factor)

    @pyqtSlot()
    def open_labeling_setup_dialog(self):
        # show a warning dialog about the problem of editing the labeling buttons when some samples are labeled
        if self.response_design.total_labeled > 0:
            msg = ("Some samples are already labeled, so editing the labeling buttons could affect the labeled samples.<br><br>"
                   "<b>Risky edits:</b> Changing thematic classes, removing, or moving buttons<br><br>"
                   "<b>Safe edits:</b> Renaming, changing colors or shortcuts, and adding new buttons.")
            QMessageBox.warning(self, 'Edit the labeling buttons with caution!', msg, QMessageBox.Ok)
        # open the labeling setup dialog
        self.labeling_btns_config.create_table()
        if self.labeling_btns_config.exec_():
            # ok button -> accept the new buttons config
            self.create_labeling_buttons(tableBtnsConfig=self.labeling_btns_config.tableBtnsConfig)
        else:
            # cancel button -> restore the old button config
            self.labeling_btns_config = LabelingButtonsConfig(self.response_design.buttons_config)

    @error_handler
    def create_labeling_buttons(self, tableBtnsConfig=None, buttons_config=None):
        if not tableBtnsConfig and not buttons_config:
            return
            
        # Clean up all existing shortcuts first
        self.cleanup_shortcuts()
        
        # clear layout
        for i in reversed(range(self.Grid_LabelingButtons.count())):
            if self.Grid_LabelingButtons.itemAt(i).widget():
                self.Grid_LabelingButtons.itemAt(i).widget().setParent(None)
            else:
                self.Grid_LabelingButtons.removeItem(self.Grid_LabelingButtons.itemAt(i))

        buttons = {}

        def create_button(item_num, item_name, item_color, item_thematic_class, item_shortcut=None):
            # save button config
            buttons[int(item_num)] = {"name": item_name, "color": item_color,
                                      "thematic_class": item_thematic_class, "shortcut": item_shortcut}
            # create button
            QPButton = QPushButton(item_name)
            QPButton.setStyleSheet('QPushButton {color: ' + item_color + '}')
            QPButton.clicked.connect(lambda state, label_id=item_num: self.label_sample(label_id))
            QPButton.setAutoDefault(False)
            QPButton.setCheckable(True)
            QPButton.setFocusPolicy(Qt.NoFocus)
            self.Grid_LabelingButtons.addWidget(QPButton, len(buttons) - 1, 0)

            # create keyboard shortcut for the labeling button
            if item_shortcut:
                shortcut = QShortcut(item_shortcut, self)
                shortcut.activated.connect(lambda label_id=item_num: self.label_sample(label_id))
                # Store the shortcut
                self.active_shortcuts[item_num] = shortcut

        # from tableBtnsConfig
        if tableBtnsConfig:
            label_id = 1
            for row in range(self.labeling_btns_config.tableBtnsConfig.rowCount()):
                item_name = self.labeling_btns_config.tableBtnsConfig.item(row, 0).text()
                item_color = self.labeling_btns_config.tableBtnsConfig.item(row, 1).background().color().name()
                item_thematic_class = self.labeling_btns_config.tableBtnsConfig.item(row, 2).text()
                item_thematic_class = None if item_thematic_class == "none" else item_thematic_class
                item_shortcut = self.labeling_btns_config.tableBtnsConfig.item(row, 3).text()
                item_shortcut = None if item_shortcut == "" else item_shortcut
                if item_name != "":
                    create_button(label_id, item_name, item_color, item_thematic_class, item_shortcut)
                    label_id += 1
                    # define if this labeling was made with thematic classes
                    if item_thematic_class is not None and item_thematic_class != "":
                        self.response_design.with_thematic_classes = True
            # save btns config
            self.response_design.buttons_config = buttons
            self.labeling_btns_config.buttons_config = buttons

        # from buttons_config
        if buttons_config:
            for row in sorted(buttons_config.keys()):
                create_button(row, buttons_config[row]["name"], buttons_config[row]["color"],
                              buttons_config[row]["thematic_class"], buttons_config[row].get("shortcut", None))
                # define if this labeling was made with thematic classes
                if buttons_config[row]["thematic_class"] is not None and buttons_config[row]["thematic_class"] != "":
                    self.response_design.with_thematic_classes = True

        # reload analysis status in accuracy assessment
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.update_analysis_state()
        # reload the current sample status
        self.update_sample_status()

    def cleanup_shortcuts(self):
        """Clean up all active labeling button shortcuts"""
        for shortcut_id, shortcut in self.active_shortcuts.items():
            if shortcut:
                shortcut.deleteLater()
        self.active_shortcuts.clear()

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the response design window
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # save some config of response design window for this sampling file
        self.response_design.fit_to_sample = self.radiusFitToSample.value()
        # save view widgets status
        view_widgets_config = {}
        for view_widget in ResponseDesignWindow.view_widgets:
            # {N: {"view_name", "layer_name", "render_file_path", "scale_factor"}, ...}
            view_widgets_config[view_widget.id] = \
                {"view_name": view_widget.QLabel_ViewName.text(),
                 "layer_name": view_widget.QCBox_RenderFile.currentLayer().name() if view_widget.QCBox_RenderFile.currentLayer() else None,
                 "render_file_path": get_current_file_path_in(view_widget.QCBox_RenderFile, show_message=False),
                 # "view_size": (view_widget.size().width(), view_widget.size().height()),
                 "scale_factor": view_widget.current_scale_factor}

        self.response_design.view_widgets_config = view_widgets_config
        self.response_design.dialog_size = (self.size().width(), self.size().height())
        self.response_design.auto_next_sample = self.autoNextSample.isChecked()

        # close the ccd widget
        if self.ccd_plugin_available:
            from CCD_Plugin.utils.config import get_plugin_config
            self.response_design.ccd_plugin_config = get_plugin_config(self.ccd_plugin.id)
            self.response_design.ccd_plugin_opened = self.QPBtn_CCDPlugin.isChecked()
            self.ccd_plugin.removes_temporary_files()
            self.ccd_plugin.widget.close()
            self.ccd_plugin.widget = None

        # Clean up shortcuts before closing
        self.cleanup_shortcuts()
        
        ResponseDesignWindow.is_opened = False
        # restore the states for some objects in the dockwidget
        from AcATaMa.gui.sampling_design_window import SamplingDesignWindow
        from AcATaMa.core.analysis import AccuracyAssessmentWindow
        if not SamplingDesignWindow.is_opened and not AccuracyAssessmentWindow.is_opened:
            AcATaMa.dockwidget.QGBox_ThematicMap.setEnabled(True)
        if not AccuracyAssessmentWindow.is_opened:
            AcATaMa.dockwidget.QGBox_SamplingDesign.setEnabled(True)
        AcATaMa.dockwidget.QPBtn_GridSettings.setEnabled(True)
        AcATaMa.dockwidget.QPBtn_saveSamplingLabeled.setEnabled(True)
        AcATaMa.dockwidget.QPBtn_OpenResponseDesignWindow.setText("Response design window")
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(ResponseDesignWindow, self).reject()


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'labeling_buttons_config.ui'))


class LabelingButtonsConfig(QDialog, FORM_CLASS):
    def __init__(self, buttons_config):
        QDialog.__init__(self)
        self.setupUi(self)
        self.buttons_config = buttons_config if buttons_config is not None else {}
        # init with empty table
        self.table_buttons = dict(zip(range(1, 1001), [""] * 1000))
        self.create_table()
        #
        self.tableBtnsConfig.itemClicked.connect(self.table_item_clicked)
        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.check_before_accept)
        self.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.QPBtn_AutoFillLabels.clicked.connect(self.apply_auto_fill_from_thematic_map)

    @error_handler
    def create_table(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        header = ["Label Name", "Color", "Thematic Class", "Shortcut", ""]
        # clear table
        self.tableBtnsConfig.clear()
        # init table
        self.tableBtnsConfig.setRowCount(len(self.table_buttons))
        self.tableBtnsConfig.setColumnCount(5)
        # hidden row labels
        self.tableBtnsConfig.verticalHeader().setVisible(False)
        # add Header
        self.tableBtnsConfig.setHorizontalHeaderLabels(header)
        # insert items
        for n, h in enumerate(header):
            if h == "Label Name":
                for m, (key, item) in enumerate(self.table_buttons.items()):
                    if m + 1 in self.buttons_config:
                        item_table = QTableWidgetItem(self.buttons_config[m + 1]["name"])
                    else:
                        item_table = QTableWidgetItem(str(item))
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    item_table.setToolTip("Label button (ID: {})".format(key))
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Color":
                for m, item in enumerate(self.table_buttons.values()):
                    item_table = QTableWidgetItem()
                    if m + 1 in self.buttons_config:
                        item_table.setBackground(QColor(self.buttons_config[m + 1]["color"]))
                    item_table.setFlags(Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    item_table.setToolTip("Click to set/change the color of this label button")
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Thematic Class":
                for m, item in enumerate(self.table_buttons.values()):
                    if valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap):
                        if m + 1 in self.buttons_config and self.buttons_config[m + 1]["thematic_class"] is not None:
                            item_table = QTableWidgetItem(self.buttons_config[m + 1]["thematic_class"])
                        else:
                            item_table = QTableWidgetItem(str(item))
                        item_table.setToolTip("Click to set/change the pixel color/value from the thematic map")
                    else:
                        item_table = QTableWidgetItem("none")
                        item_table.setForeground(QColor("lightGrey"))
                        item_table.setToolTip("No thematic map selected, if you want enable the\n"
                                              "thematic classes, select first a valid thematic map file")
                        item_h = QTableWidgetItem(h)
                        item_h.setForeground(QColor("lightGrey"))
                        self.tableBtnsConfig.setHorizontalHeaderItem(2, item_h)

                    item_table.setFlags(Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Shortcut":
                for m, item in enumerate(self.table_buttons.values()):
                    if m + 1 in self.buttons_config and "shortcut" in self.buttons_config[m + 1] and self.buttons_config[m + 1]["shortcut"]:
                        item_table = QTableWidgetItem(self.buttons_config[m + 1]["shortcut"])
                    else:
                        item_table = QTableWidgetItem("")
                    item_table.setFlags(Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    item_table.setToolTip("Click to set/change the keyboard shortcut for this button")
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "":
                for m, item in enumerate(self.table_buttons.values()):
                    item_table = QTableWidgetItem()
                    path = ':/plugins/AcATaMa/icons/trash.svg'
                    icon = QIcon(path)
                    item_table.setIcon(icon)
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    item_table.setToolTip("Clean this row")
                    self.tableBtnsConfig.setItem(m, n, item_table)

        # check if the thematic map is loaded to show the auto fill button
        if valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap):
            self.QPBtn_AutoFillLabels.setEnabled(True)
        else:
            self.QPBtn_AutoFillLabels.setDisabled(True)
        # set the minimum width to 0 for headers
        self.tableBtnsConfig.horizontalHeader().setMinimumSectionSize(0)
        # adjust size of Table
        self.tableBtnsConfig.resizeColumnsToContents()
        self.tableBtnsConfig.resizeRowsToContents()
        # adjust the dialog based on table content
        dialog_width = self.tableBtnsConfig.horizontalHeader().length() + 50
        self.resize(dialog_width, self.height())

    @pyqtSlot(QTableWidgetItem)
    def table_item_clicked(self, tableItem):
        if tableItem.text() == "none":
            return
        # set color
        if tableItem.column() == 1:
            remember_color = tableItem.background().color()
            remember_color = QColor("white") if remember_color.name() == QColor("black").name() else remember_color
            color = QColorDialog.getColor(remember_color, self)
            if color.isValid():
                tableItem.setBackground(color)
                self.tableBtnsConfig.clearSelection()
        # set the thematic class
        if tableItem.column() == 2:
            thematic_map_class = ThematicMapClasses()
            if thematic_map_class.exec_():
                tableItem.setText(thematic_map_class.pix_value)
                self.tableBtnsConfig.item(tableItem.row(), 1).setBackground(thematic_map_class.color)
        # set the shortcut
        if tableItem.column() == 3:
            current_shortcut = tableItem.text()
            # Get the button name from the first column of the same row
            button_name = self.tableBtnsConfig.item(tableItem.row(), 0).text()
            shortcut_dialog = ShortcutDialog(self, current_shortcut, button_name)
            if shortcut_dialog.exec_():
                tableItem.setText(shortcut_dialog.shortcut)
                self.tableBtnsConfig.clearSelection()
        # clean the current row clicked in the trash icon
        if tableItem.column() == 4:
            self.tableBtnsConfig.item(tableItem.row(), 0).setText("")
            self.tableBtnsConfig.item(tableItem.row(), 1).setBackground(QColor(255, 255, 255, 0))
            if not self.tableBtnsConfig.item(tableItem.row(), 2).text() == "none":
                self.tableBtnsConfig.item(tableItem.row(), 2).setText("")
            self.tableBtnsConfig.item(tableItem.row(), 3).setText("")

    @pyqtSlot()
    def check_before_accept(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # check if all buttons are associated to thematic classes if it is working with thematic classes
        if valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
            items_with_classes = [self.tableBtnsConfig.item(row, 2).text() != "" for row in
                                  range(self.tableBtnsConfig.rowCount()) if self.tableBtnsConfig.item(row, 0).text() != ""]
            if False in items_with_classes:
                msg = "Invalid configuration:\n\nA) If you are labeling with thematic classes, then " \
                      "you must configure the thematic class value for all buttons. \n\nB) Or if you are " \
                      "labeling the sampling without pairing with thematic classes, then deselect the " \
                      "thematic map."
                QMessageBox.warning(self, 'Error with the labeling buttons', msg, QMessageBox.Ok)
                return
        # check if all button configured have a valid name
        items_with_valid_names = [self.tableBtnsConfig.item(row, 0).text() != "" for row in
                                  range(self.tableBtnsConfig.rowCount()) if
                                  self.tableBtnsConfig.item(row, 1).background().color().name() not in ["#ffffff", '#000000'] or
                                  self.tableBtnsConfig.item(row, 2).text() not in ["none", ""]]
        if False in items_with_valid_names:
            msg = "Invalid configuration:\n\nTo create the buttons for labeling, they must have a valid name."
            QMessageBox.warning(self, 'Error with the labeling buttons', msg, QMessageBox.Ok)
            return
        # check if button name exist (not allow duplicate labels with the same names)
        items_with_valid_names = [self.tableBtnsConfig.item(row, 0).text() for row in
                                  range(self.tableBtnsConfig.rowCount()) if
                                  self.tableBtnsConfig.item(row, 0).text() != ""]
        if len(items_with_valid_names) != len(set(items_with_valid_names)):
            msg = "Invalid configuration:\n\nTo create the buttons for labeling, the labeling names must be unique."
            QMessageBox.warning(self, 'Error with the labeling buttons', msg, QMessageBox.Ok)
            return
        # check if exists a duplicate thematic class
        items_with_valid_names = [self.tableBtnsConfig.item(row, 2).text() for row in
                                    range(self.tableBtnsConfig.rowCount()) if
                                    self.tableBtnsConfig.item(row, 2).text() not in ["", "none"]]
        if len(items_with_valid_names) != len(set(items_with_valid_names)):
            msg = "Invalid configuration:\n\nTo create the buttons for labeling, the thematic class values must be unique."
            QMessageBox.warning(self, 'Error with the labeling buttons', msg, QMessageBox.Ok)
            return
        # check if exists a duplicate shortcut
        shortcuts_with_valid_names = [self.tableBtnsConfig.item(row, 3).text() for row in
                                     range(self.tableBtnsConfig.rowCount()) if
                                     self.tableBtnsConfig.item(row, 3).text() != "" and
                                     self.tableBtnsConfig.item(row, 0).text() != ""]
        if len(shortcuts_with_valid_names) != len(set(shortcuts_with_valid_names)):
            msg = "Invalid configuration:\n\nTo create the buttons for labeling, the keyboard shortcuts must be unique."
            QMessageBox.warning(self, 'Error with the labeling buttons', msg, QMessageBox.Ok)
            return
        # pass all checks
        self.accept()

    @pyqtSlot()
    def apply_auto_fill_from_thematic_map(self):
        # check if the table tableBtnsConfig is not empty
        if not all([self.tableBtnsConfig.item(row, 0).text() == "" and
                    self.tableBtnsConfig.item(row, 2).text() == "" for row in range(self.tableBtnsConfig.rowCount())]):
            # first prompt
            quit_msg = ("This action will set up the labeling buttons based on the current thematic map symbology. "
                        "This will replace the currently configured one. Do you want to continue?")
            reply = QMessageBox.question(None, 'Apply auto fill from thematic map',
                                         quit_msg, QMessageBox.Apply | QMessageBox.Cancel, QMessageBox.Cancel)
            if reply != QMessageBox.Apply:
                return

        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # clean the table
        self.create_table()

        # get the symbology table; pixel values, labels and colors from thematic map
        symbology_table = get_symbology_table(AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer(),
                                              band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()))
        nodata_value = get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text())

        # create the buttons
        for item_idx, symbology_item in enumerate(symbology_table):
            value, label, color = symbology_item
            if value == nodata_value:
                continue
            try:
                label = str(int(float(label)))
            except ValueError:
                pass
            self.tableBtnsConfig.item(item_idx, 0).setText(label)
            self.tableBtnsConfig.item(item_idx, 1).setBackground(color)
            self.tableBtnsConfig.item(item_idx, 2).setText(str(value))


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'labeling_shortcut_dialog.ui'))


class ShortcutDialog(QDialog, FORM_CLASS):
    """Dialog for setting keyboard shortcuts with live key capture."""
    
    def __init__(self, parent=None, current_shortcut="", button_name=""):
        super().__init__(parent)
        self.setupUi(self)
        self.current_shortcut = current_shortcut
        self.shortcut_text = current_shortcut
        
        # Setup the UI
        self.shortcut_label.setText(f"Shortcut for <b>{button_name}</b>:" if button_name else "Shortcut:")
        self.shortcut_edit.setText(self.current_shortcut)
        self.shortcut_edit.installEventFilter(self)
        self.shortcut_edit.setFocus()
        
        # Update clear button tooltip and icon
        self.clear_shortcut.setToolTip("Clear shortcut")
        self.clear_shortcut.setEnabled(bool(self.current_shortcut))
        
        # Setup connections
        self.clear_shortcut.clicked.connect(self.clear_shortcut_action)
        
    def eventFilter(self, obj, event):
        """Event filter to handle keyboard events."""
        # Use integer value for KeyPress if attribute is missing
        KEY_PRESS = getattr(QEvent, 'KeyPress', 6)
        if obj == self.shortcut_edit and event.type() == KEY_PRESS:
            return self.handle_key_press(event)
        return super().eventFilter(obj, event)

    def handle_key_press(self, event):
        """Handle key press events to capture shortcuts."""
        # Use integer values for modifier keys if linter complains
        KEY_CONTROL = getattr(Qt, 'Key_Control', 0x01000021)
        KEY_ALT = getattr(Qt, 'Key_Alt', 0x01000023)
        KEY_SHIFT = getattr(Qt, 'Key_Shift', 0x01000020)
        KEY_META = getattr(Qt, 'Key_Meta', 0x01000022)
        MOD_CONTROL = getattr(Qt, 'ControlModifier', 0x04000000)
        MOD_ALT = getattr(Qt, 'AltModifier', 0x08000000)
        MOD_SHIFT = getattr(Qt, 'ShiftModifier', 0x02000000)
        MOD_META = getattr(Qt, 'MetaModifier', 0x10000000)
        
        if event.key() in [KEY_CONTROL, KEY_ALT, KEY_SHIFT, KEY_META]:
            return True
            
        # Build the shortcut string
        modifiers = []
        if event.modifiers() & MOD_CONTROL:
            modifiers.append("Ctrl")
        if event.modifiers() & MOD_ALT:
            modifiers.append("Alt")
        if event.modifiers() & MOD_SHIFT:
            modifiers.append("Shift")
        if event.modifiers() & MOD_META:
            modifiers.append("Meta")
            
        # Get the key name
        key_name = self.get_key_name(event.key())
        if key_name:
            if modifiers:
                self.shortcut_text = "+".join(modifiers) + "+" + key_name
            else:
                self.shortcut_text = key_name
                
            self.shortcut_edit.setText(self.shortcut_text)
            self.clear_shortcut.setEnabled(True)
            return True
        return False
            
    def get_key_name(self, key):
        """Convert Qt key to readable name."""
        # Use getattr for all Qt key enums with fallback values
        qt_keys = {
            'Key_F1': 0x01000030, 'Key_F2': 0x01000031, 'Key_F3': 0x01000032, 'Key_F4': 0x01000033,
            'Key_F5': 0x01000034, 'Key_F6': 0x01000035, 'Key_F7': 0x01000036, 'Key_F8': 0x01000037,
            'Key_F9': 0x01000038, 'Key_F10': 0x01000039, 'Key_F11': 0x0100003A, 'Key_F12': 0x0100003B,
            'Key_Left': 0x01000012, 'Key_Right': 0x01000014, 'Key_Up': 0x01000013, 'Key_Down': 0x01000015,
            'Key_Home': 0x01000010, 'Key_End': 0x01000011, 'Key_PageUp': 0x01000016, 'Key_PageDown': 0x01000017,
            'Key_Insert': 0x01000006, 'Key_Delete': 0x01000007, 'Key_Backspace': 0x01000003,
            'Key_Tab': 0x01000001, 'Key_Return': 0x01000004, 'Key_Enter': 0x01000005, 'Key_Escape': 0x01000000,
            'Key_Space': 0x20
        }
        key_names = {getattr(Qt, k, v): k.split('_', 1)[1] for k, v in qt_keys.items()}
        
        if key in key_names:
            return key_names[key]
        elif getattr(Qt, 'Key_A', 0x41) <= key <= getattr(Qt, 'Key_Z', 0x5A):
            return chr(key)
        elif getattr(Qt, 'Key_0', 0x30) <= key <= getattr(Qt, 'Key_9', 0x39):
            return chr(key)
        else:
            return None
            
    def clear_shortcut_action(self):
        """Clear the current shortcut."""
        self.shortcut_text = ""
        self.shortcut_edit.setText("")
        self.clear_shortcut.setEnabled(False)
        
    @property
    def shortcut(self):
        """Get the final shortcut text."""
        return self.shortcut_text

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'labeling_thematic_map_classes.ui'))


class ThematicMapClasses(QDialog, FORM_CLASS):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        # init with empty table
        self.create_table()

    @error_handler
    def create_table(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        header = ["Pix Val", "Color", "Select"]
        # get color table from raster
        thematic_table = {"values_and_colors_table": get_values_and_colors_table(
            AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer(),
            band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
            nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()))}

        if not thematic_table["values_and_colors_table"]:
            # clear table
            self.tableOfClasses.setRowCount(0)
            self.tableOfClasses.setColumnCount(0)
            return
        thematic_table["row_count"] = len(list(thematic_table["values_and_colors_table"].values())[0])
        # init table
        self.tableOfClasses.setRowCount(thematic_table["row_count"])
        self.tableOfClasses.setColumnCount(3)
        # hidden row labels
        self.tableOfClasses.verticalHeader().setVisible(False)
        # add Header
        self.tableOfClasses.setHorizontalHeaderLabels(header)

        # insert items
        for n, h in enumerate(header):
            if h == "Pix Val":
                for m, item in enumerate(thematic_table["values_and_colors_table"]["Pixel Value"]):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Color":
                for m in range(thematic_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setBackground(QColor(thematic_table["values_and_colors_table"]["Red"][m],
                                                    thematic_table["values_and_colors_table"]["Green"][m],
                                                    thematic_table["values_and_colors_table"]["Blue"][m],
                                                    thematic_table["values_and_colors_table"]["Alpha"][m]))
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Select":
                for m in range(thematic_table["row_count"]):
                    item_table = QPushButton("Select this")
                    item_table.clicked.connect(self.select_clicked)
                    self.tableOfClasses.setCellWidget(m, n, item_table)

        # adjust size of Table
        self.tableOfClasses.resizeColumnsToContents()
        self.tableOfClasses.resizeRowsToContents()
        # adjust the dialog based on table content
        dialog_width = self.tableOfClasses.horizontalHeader().length() + 50
        self.resize(dialog_width, self.height())

    @pyqtSlot()
    def select_clicked(self):
        button = self.sender()
        row = self.tableOfClasses.indexAt(button.pos()).row()

        self.pix_value = self.tableOfClasses.item(row, 0).text()
        self.color = self.tableOfClasses.item(row, 1).background().color()

        self.accept()


class Tile(object):
    def __init__(self, xmin, xmax, ymin, ymax, tile_color, fill_color=None):
        self.rbs_in_response_design_window = []
        self.extent = QgsRectangle(xmin, ymin, xmax, ymax)
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.tile_color = tile_color
        self.fill_color = fill_color

    def create(self, canvas, line_width=1):
        """Create the tile as a rubber band inside the canvas given"""
        if isdeleted(canvas):
            del self
            return
        rubber_band = QgsRubberBand(canvas)
        points = [QgsPointXY(self.xmin, self.ymax), QgsPointXY(self.xmax, self.ymax),
                  QgsPointXY(self.xmax, self.ymin), QgsPointXY(self.xmin, self.ymin)]
        rubber_band.setToGeometry(QgsGeometry.fromPolygonXY([points]), None)
        rubber_band.setColor(self.tile_color)
        rubber_band.setFillColor(self.fill_color if self.fill_color else QColor(0, 0, 0, 0))
        rubber_band.setWidth(line_width)
        rubber_band.show()
        self.rbs_in_response_design_window.append(rubber_band)

    def show(self):
        """Show/draw the tile in all view widgets in main dialog"""
        self.hide()
        for view_widget in ResponseDesignWindow.view_widgets:
            if view_widget.is_active:
                self.create(view_widget.render_widget.canvas)

    def hide(self):
        [rubber_band.reset(QgsWkbTypes.PolygonGeometry) for rubber_band in self.rbs_in_response_design_window if not isdeleted(rubber_band)]
