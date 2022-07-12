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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSlot, QEventLoop, QTimer
from qgis.PyQt.QtWidgets import QTableWidgetItem, QSplitter, QColorDialog, QDialog, QDialogButtonBox, QPushButton, \
    QMessageBox
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.gui import QgsRubberBand
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, Qgis, QgsProject, QgsUnitTypes, \
    QgsRectangle, QgsPointXY, QgsGeometry

from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.qgis_utils import valid_file_selected_in, get_current_file_path_in, \
    load_and_select_filepath_in
from AcATaMa.core.map import get_values_and_colors_table
from AcATaMa.utils.system_utils import open_file, block_signals_to, error_handler
from AcATaMa.gui.response_design_view_widget import LabelingViewWidget

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'response_design_window.ui'))


class ResponseDesignWindow(QDialog, FORM_CLASS):
    is_opened = False
    view_widgets = []
    current_sample = None
    instance = None

    def __init__(self, sampling_layer, columns, rows):
        QDialog.__init__(self)
        self.sampling_layer = sampling_layer
        self.setupUi(self)
        ResponseDesignWindow.instance = self

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
        self.QPBtn_LabelingSetup.setAutoDefault(False)
        self.QPBtn_unlabelSampleButton.setAutoDefault(False)

        # go to sample ID action
        self.GoTo_ID_Button.clicked.connect(self.go_to_sample_id)
        self.GoTo_ID.returnPressed.connect(self.go_to_sample_id)
        self.GoTo_ID.textChanged.connect(lambda: self.GoTo_ID.setStyleSheet(""))

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
        self.radiusFitToSample.setDecimals(
            4 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                     QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.radiusFitToSample.setSingleStep(
            0.0001 if layer_dist_unit in [QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles,
                                          QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceDegrees] else 1)
        self.radiusFitToSample.setValue(self.response_design.fit_to_sample)

        # set total samples
        self.QPBar_SamplesNavigation.setMaximum(len(self.response_design.points))

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
        self.sample_unit = None
        self.SampleUnit_PixelBuffer.setCurrentIndex(self.response_design.sample_unit_pixel_buffer)
        self.set_current_sample()
        self.change_sample_unit_color(color=self.response_design.sample_unit_color)
        self.SampleUnit_Color.clicked.connect(self.change_sample_unit_color)
        self.SampleUnit_PixelBuffer.currentIndexChanged.connect(self.show_the_sample_unit)
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
                                view_config["render_file_path"]), level=Qgis.Warning, duration=-1)
                    else:
                        self.MsgBar.pushMessage(
                            "Could not to load the layer '{}' in the view {} (for network layers use save/load a Qgis project)".format(
                                layer_name,
                                "'{}'".format(view_config["view_name"]) if view_config["view_name"] else view_widget.id + 1),
                            level=Qgis.Warning, duration=-1)
                    # TODO: restore size by view widget
                    # view_widget.resize(*view_config["view_size"])
                    view_widget.QLabel_ViewName.setText(view_config["view_name"])
                    view_widget.scaleFactor.setValue(view_config["scale_factor"])
                    # active render layer in canvas
                    view_widget.set_render_layer(view_widget.QCBox_RenderFile.currentLayer())

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        ResponseDesignWindow.is_opened = True
        # adjust some objects in the dockwidget while response design window is opened
        AcATaMa.dockwidget.QGBox_SamplingFile.setDisabled(True)
        AcATaMa.dockwidget.QGBox_GridSettings.setDisabled(True)
        AcATaMa.dockwidget.QGBox_LabelingStatus.setDisabled(True)
        AcATaMa.dockwidget.QGBox_saveSamplingLabeled.setDisabled(True)
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

    @pyqtSlot()
    @error_handler
    def open_current_point_in_google_engine(self):
        # create temp file
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        kml_file = tempfile.mktemp(
            prefix="point_id_{}_{}_".format(self.current_sample.sample_id, self.sampling_layer.name()),
            suffix=".kml", dir=AcATaMa.dockwidget.tmp_dir)
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
        outfile = open(kml_file, "w")
        outfile.writelines(kml_raw)
        outfile.close()

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
        thematic_pixel = self.current_sample.get_thematic_pixel()
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
    def change_sample_unit_color(self, color=None):
        if not color:
            color = QColorDialog.getColor(self.response_design.sample_unit_color, self)
        if color.isValid():
            self.response_design.sample_unit_color = color
            self.SampleUnit_Color.setStyleSheet("QToolButton{{background-color:{};}}".format(color.name()))
            self.show_the_sample_unit()

    @pyqtSlot()
    def show_the_sample_unit(self):
        if self.sample_unit:
            self.sample_unit.hide()
        pixel_buffer = int(self.SampleUnit_PixelBuffer.currentText())
        self.response_design.sample_unit_pixel_buffer = pixel_buffer
        if pixel_buffer > 0:
            sample_unit = self.current_sample.get_thematic_pixel(with_buffer=pixel_buffer)
            if sample_unit:
                self.sample_unit = Tile(*sample_unit, self.response_design.sample_unit_color)
                self.sample_unit.show()

    @pyqtSlot()
    def show_the_current_pixel(self):
        # show the edges of the thematic pixel of the current sample
        if self.pixel_tile:
            self.pixel_tile.hide()
        thematic_pixel = self.current_sample.get_thematic_pixel()
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
        self.show_the_sample_unit()

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

    @pyqtSlot()
    def open_labeling_setup_dialog(self):
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
        # clear layout
        for i in reversed(range(self.Grid_LabelingButtons.count())):
            if self.Grid_LabelingButtons.itemAt(i).widget():
                self.Grid_LabelingButtons.itemAt(i).widget().setParent(None)
            else:
                self.Grid_LabelingButtons.removeItem(self.Grid_LabelingButtons.itemAt(i))

        buttons = {}

        def create_button(item_num, item_name, item_color, item_thematic_class):
            # save button config
            buttons[int(item_num)] = {"name": item_name, "color": item_color,
                                      "thematic_class": item_thematic_class}
            # create button
            QPButton = QPushButton(item_name)
            QPButton.setStyleSheet('QPushButton {color: ' + item_color + '}')
            QPButton.clicked.connect(lambda state, label_id=item_num: self.label_sample(label_id))
            QPButton.setAutoDefault(False)
            QPButton.setCheckable(True)
            self.Grid_LabelingButtons.addWidget(QPButton, len(buttons) - 1, 0)

        # from tableBtnsConfig
        if tableBtnsConfig:
            for row in range(self.labeling_btns_config.tableBtnsConfig.rowCount()):
                item_name = self.labeling_btns_config.tableBtnsConfig.item(row, 0).text()
                item_color = self.labeling_btns_config.tableBtnsConfig.item(row, 1).background().color().name()
                item_thematic_class = self.labeling_btns_config.tableBtnsConfig.item(row, 2).text()
                item_thematic_class = None if item_thematic_class == "none" else item_thematic_class
                if item_name != "":
                    create_button(row + 1, item_name, item_color, item_thematic_class)
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
                              buttons_config[row]["thematic_class"])
                # define if this labeling was made with thematic classes
                if buttons_config[row]["thematic_class"] is not None and buttons_config[row]["thematic_class"] != "":
                    self.response_design.with_thematic_classes = True

        # reload sampling file status in analysis tab
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.set_sampling_file_in_analysis()
        # reload the current sample status
        self.update_sample_status()

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

        ResponseDesignWindow.is_opened = False
        # restore the states for some objects in the dockwidget
        AcATaMa.dockwidget.QGBox_SamplingFile.setEnabled(True)
        AcATaMa.dockwidget.QGBox_GridSettings.setEnabled(True)
        AcATaMa.dockwidget.QGBox_LabelingStatus.setEnabled(True)
        AcATaMa.dockwidget.QGBox_saveSamplingLabeled.setEnabled(True)
        AcATaMa.dockwidget.QPBtn_OpenResponseDesignWindow.setText("Open response design window")
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
        self.table_buttons = dict(zip(range(1, 61), [""] * 60))
        self.create_table()
        #
        self.tableBtnsConfig.itemClicked.connect(self.table_item_clicked)
        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.check_before_accept)
        self.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

    @error_handler
    def create_table(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        header = ["Label Name", "Color", "Thematic Class", ""]
        # clear table
        self.tableBtnsConfig.clear()
        # init table
        self.tableBtnsConfig.setRowCount(len(self.table_buttons))
        self.tableBtnsConfig.setColumnCount(4)
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
        # clean the current row clicked in the trash icon
        if tableItem.column() == 3:
            self.tableBtnsConfig.item(tableItem.row(), 0).setText("")
            self.tableBtnsConfig.item(tableItem.row(), 1).setBackground(QColor(255, 255, 255, 0))
            if not self.tableBtnsConfig.item(tableItem.row(), 2).text() == "none":
                self.tableBtnsConfig.item(tableItem.row(), 2).setText("")

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
        # pass all checks
        self.accept()


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
            nodata=int(AcATaMa.dockwidget.nodata_ThematicMap.value()))}

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
        [rubber_band.reset() for rubber_band in self.rbs_in_response_design_window]