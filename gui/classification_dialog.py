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
from PyQt4 import QtGui, uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QTableWidgetItem, QSplitter, QColor, QColorDialog

from AcATaMa.core.classification import Classification
from AcATaMa.core.dockwidget import valid_file_selected_in, get_current_file_path_in, \
    load_and_select_filepath_in
from AcATaMa.core.raster import get_color_table
from AcATaMa.gui.classification_view_widget import ClassificationViewWidget

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_dialog.ui'))


class ClassificationDialog(QtGui.QDialog, FORM_CLASS):
    is_opened = False
    view_widgets = []
    current_sample = None

    def __init__(self, sampling_layer, columns, rows):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        QtGui.QDialog.__init__(self)
        self.iface = AcATaMa.dockwidget.iface
        self.setupUi(self)

        # get classification or init new instance
        if sampling_layer in Classification.instances:
            self.classification = Classification.instances[sampling_layer]
        else:
            self.classification = Classification(sampling_layer)
            self.classification.grid_columns = columns
            self.classification.grid_rows = rows

        #### settings the classification dialog

        # set dialog title
        self.setWindowTitle("Classification of samples for " + sampling_layer.name())
        # resize the classification dialog
        if self.classification.dialog_size:
            self.resize(*self.classification.dialog_size)

        # create dynamic size of the view render widgets windows
        # inside the grid with columns x rows divide by splitters
        h_splitters = []
        view_widgets = []
        for row in range(self.classification.grid_rows):
            splitter = QSplitter(Qt.Horizontal)
            for column in range(self.classification.grid_columns):
                new_view_widget = ClassificationViewWidget()
                splitter.addWidget(new_view_widget)
                h_splitters.append(splitter)
                view_widgets.append(new_view_widget)
        v_splitter = QSplitter(Qt.Vertical)
        for splitter in h_splitters:
            v_splitter.addWidget(splitter)
        # add to classification dialog
        self.widget_view_windows.layout().addWidget(v_splitter)
        # save instances
        ClassificationDialog.view_widgets = view_widgets
        # setup view widget
        [view_widget.setup_view_widget(sampling_layer) for view_widget in ClassificationDialog.view_widgets]
        for idx, view_widget in enumerate(ClassificationDialog.view_widgets): view_widget.id = idx
        # set the label names for each view
        for num_view, view_widget in enumerate(ClassificationDialog.view_widgets):
            view_widget.QLabel_ViewID.setText("View {}:".format(num_view+1))
        # restore view widgets status
        for config_id, view_config in self.classification.view_widgets_config.items():
            for view_widget in ClassificationDialog.view_widgets:
                if config_id == view_widget.id:
                    view_widget = ClassificationDialog.view_widgets[config_id]
                    # load file for this view widget if exists
                    file_name = os.path.splitext(os.path.basename(view_config["render_file"]))[0]
                    file_index = view_widget.QCBox_RenderFile.findText(file_name, Qt.MatchFixedString)
                    if file_index != -1:
                        # select layer if exists in Qgis
                        view_widget.QCBox_RenderFile.setCurrentIndex(file_index)
                    elif os.path.isfile(view_config["render_file"]):
                        # load file and select in view if this exists and not load in Qgis
                        load_and_select_filepath_in(view_widget.QCBox_RenderFile, view_config["render_file"],
                                                    "any", ignore_layers=[view_widget.sampling_layer])
                    # restore others config in view widget
                    view_widget.OnOff_RenderView.setChecked(view_config["render_activated"])
                    # TODO: restore size by view widget
                    #view_widget.resize(*view_config["view_size"])
                    view_widget.QLabel_ViewName.setText(view_config["name"])
                    view_widget.scaleFactor.setValue(view_config["scale_factor"])

        # set classification buttons
        self.classification_btns_config = ClassificationButtonsConfig(self.classification.buttons_config)
        self.create_classification_buttons(buttons_config=self.classification.buttons_config)
        self.QPBtn_SetClassification.clicked.connect(self.open_set_classification_dialog)
        # disable enter action
        self.QPBtn_SetClassification.setAutoDefault(False)

        # go to sample ID action
        self.GoTo_ID_Button.clicked.connect(self.go_to_sample_id)
        self.GoTo_ID.returnPressed.connect(self.go_to_sample_id)
        self.GoTo_ID.textChanged.connect(lambda: self.GoTo_ID.setStyleSheet(""))

        # set radius fit to sample
        self.radiusFitToSample.setValue(self.classification.fit_to_sample)

        # set total samples
        self.QPBar_SamplesNavigation.setMaximum(len(self.classification.points))

        # actions for fit and go to current sample
        self.radiusFitToSample.valueChanged.connect(lambda: self.show_and_go_to_current_sample(highlight=False))
        self.currentSample.clicked.connect(lambda: self.show_and_go_to_current_sample(highlight=True))

        # move through samples
        self.nextSample.clicked.connect(self.next_sample)
        self.nextSampleNotClassified.clicked.connect(self.next_sample_not_classified)
        self.previousSample.clicked.connect(self.previous_sample)
        self.previousSampleNotClassified.clicked.connect(self.previous_sample_not_classified)

        # dialog buttons box
        self.closeButton.rejected.connect(self.closing)
        # disable enter action
        self.closeButton.button(QtGui.QDialogButtonBox.Close).setAutoDefault(False)

        # init current point
        self.current_sample_idx = self.classification.current_sample_idx
        self.current_sample = None
        self.set_current_sample()

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        ClassificationDialog.is_opened = True
        # adjust some objects in the dockwidget while is classifying
        AcATaMa.dockwidget.QGBox_SamplingFile.setDisabled(True)
        AcATaMa.dockwidget.QGBox_GridSettings.setDisabled(True)
        AcATaMa.dockwidget.QGBox_ClassificationStatus.setDisabled(True)
        AcATaMa.dockwidget.QGBox_saveSamplingClassified.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_OpenClassificationDialog.setText(u"Classification in progress, click to show")

        super(ClassificationDialog, self).show()

    def set_current_sample(self):
        """Set the current sample"""
        self.current_sample = self.classification.points[self.current_sample_idx]
        ClassificationDialog.current_sample = self.current_sample
        self.classification.current_sample_idx = self.current_sample_idx
        # update progress bar
        self.QPBar_SamplesNavigation.setValue(self.current_sample_idx + 1)
        # show the sample ID
        self.Sample_ID.setText(str(self.current_sample.shape_id))
        # show the class assigned
        self.display_sample_status()
        # show and go to marker
        self.show_and_go_to_current_sample()

    def go_to_sample_id(self):
        try:
            shape_id = int(self.GoTo_ID.text())
            # find the sample point with ID
            sample_point = next((x for x in self.classification.points if x.shape_id == shape_id), None)
            # go to sample
            self.current_sample_idx = self.classification.points.index(sample_point)
            self.set_current_sample()
        except:
            self.GoTo_ID.setStyleSheet("color: red")

    def classify_sample(self, classif_id):
        if classif_id:
            self.current_sample.classif_id = int(classif_id)
            self.current_sample.is_classified = True
            self.display_sample_status()
            if self.autoNextSample.isChecked():
                # automatically follows the next sample
                self.next_sample()

    def display_sample_status(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        if self.current_sample.is_classified:
            class_name = self.classification.buttons_config[self.current_sample.classif_id]["name"]
            self.statusCurrentSample.setText(class_name)
            self.statusCurrentSample.setStyleSheet(
                'QLabel {color: ' + self.classification.buttons_config[self.current_sample.classif_id]["color"] + ';}')
        else:
            self.statusCurrentSample.setText("not classified")
            self.statusCurrentSample.setStyleSheet('QLabel {color: gray;}')
        # update the total classified and not classified samples labels
        total_classified = sum(sample.is_classified for sample in self.classification.points)
        total_not_classified = sum(not sample.is_classified for sample in self.classification.points)
        self.totalClassified.setText(str(total_classified))
        self.totalNotClassified.setText(str(total_not_classified))
        # update in dockwidget status
        AcATaMa.dockwidget.QPBar_ClassificationStatus.setValue(total_classified)
        # check is the classification is completed and update in dockwidget status
        if total_not_classified == 0:
            self.classification.is_completed = True
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: green;}')
        else:
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification not completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: orange;}')
        # updated state of sampling file selected for accuracy assessment tab
        AcATaMa.dockwidget.set_sampling_file_accuracy_assessment()

    def show_and_go_to_current_sample(self, highlight=True):
        for view_widget in ClassificationDialog.view_widgets:
            if view_widget.is_active:
                # fit to current point
                self.current_sample.fit_to(view_widget, self.radiusFitToSample.value())
                # create the marker
                view_widget.render_widget.marker.show(self.current_sample)
                if highlight and view_widget.render_widget.canvas.renderFlag():
                    # highlight to marker
                    view_widget.render_widget.marker.highlight()

    def next_sample(self):
        if self.current_sample_idx >= len(self.classification.points)-1:
            return
        self.current_sample_idx += 1
        self.set_current_sample()

    def next_sample_not_classified(self):
        tmp_sample_idx = self.current_sample_idx + 1
        while tmp_sample_idx < len(self.classification.points) and \
                self.classification.points[tmp_sample_idx].is_classified:
            tmp_sample_idx += 1
        if tmp_sample_idx < len(self.classification.points) and \
                not self.classification.points[tmp_sample_idx].is_classified:
            self.current_sample_idx = tmp_sample_idx
            self.set_current_sample()

    def previous_sample(self):
        if self.current_sample_idx < 1:
            return
        self.current_sample_idx -= 1
        self.set_current_sample()

    def previous_sample_not_classified(self):
        tmp_sample_idx = self.current_sample_idx - 1
        while self.classification.points[tmp_sample_idx].is_classified \
              and tmp_sample_idx >= 0:
            tmp_sample_idx -= 1
        if not self.classification.points[tmp_sample_idx].is_classified and tmp_sample_idx >= 0:
            self.current_sample_idx = tmp_sample_idx
            self.set_current_sample()

    def open_set_classification_dialog(self):
        if self.classification_btns_config.exec_():
            self.create_classification_buttons(tableBtnsConfig=self.classification_btns_config.tableBtnsConfig)

    def create_classification_buttons(self, tableBtnsConfig=None, buttons_config=None):
            if not tableBtnsConfig and not buttons_config:
                return
            # clear layout
            for i in range(self.gridButtonsClassification.count()):
                self.gridButtonsClassification.itemAt(i).widget().close()

            buttons = {}

            def create_button(item_num, item_name, item_color, item_thematic_class):
                # save button config
                buttons[int(item_num)] = {"name": item_name, "color": item_color,
                                          "thematic_class": item_thematic_class}
                # create button
                QPButton = QtGui.QPushButton(item_name)
                QPButton.setStyleSheet('QPushButton {color: '+item_color+'}')
                QPButton.clicked.connect(lambda state, classif_id=item_num: self.classify_sample(classif_id))
                QPButton.setAutoDefault(False)
                self.gridButtonsClassification.addWidget(QPButton, len(buttons)-1, 0)

            # from tableBtnsConfig
            if tableBtnsConfig:
                for row in range(self.classification_btns_config.tableBtnsConfig.rowCount()):
                    item_num = self.classification_btns_config.tableBtnsConfig.item(row, 0).text()
                    item_name = self.classification_btns_config.tableBtnsConfig.item(row, 1).text()
                    item_color = self.classification_btns_config.tableBtnsConfig.item(row, 2).backgroundColor().name()
                    item_thematic_class = self.classification_btns_config.tableBtnsConfig.item(row, 3).text()
                    item_thematic_class = None if item_thematic_class == "No thematic raster" else item_thematic_class
                    if item_name != "":
                        create_button(item_num, item_name, item_color, item_thematic_class)
                # save btns config
                self.classification.buttons_config = buttons
            # from buttons_config
            if buttons_config:
                for row in sorted(buttons_config.keys()):
                    create_button(row, buttons_config[row]["name"], buttons_config[row]["color"],
                                  buttons_config[row]["thematic_class"])

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the classification dialog
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # save some config of classification dialog for this sampling file
        self.classification.fit_to_sample = self.radiusFitToSample.value()
        # save view widgets status
        view_widgets_config = {}
        for view_widget in ClassificationDialog.view_widgets:
            if view_widget.is_active:
                # {N: {"name", "render_file", "render_activated", "scale_factor"}, ...}
                view_widgets_config[view_widget.id] = \
                    {"name": view_widget.QLabel_ViewName.text(),
                     "render_file":  get_current_file_path_in(view_widget.QCBox_RenderFile),
                     "render_activated": view_widget.OnOff_RenderView.isChecked(),
                     #"view_size": (view_widget.size().width(), view_widget.size().height()),
                     "scale_factor": view_widget.current_scale_factor}

        self.classification.view_widgets_config = view_widgets_config
        self.classification.dialog_size = (self.size().width(), self.size().height())

        ClassificationDialog.is_opened = False
        # restore the states for some objects in the dockwidget
        AcATaMa.dockwidget.QGBox_SamplingFile.setEnabled(True)
        AcATaMa.dockwidget.QGBox_GridSettings.setEnabled(True)
        AcATaMa.dockwidget.QGBox_ClassificationStatus.setEnabled(True)
        AcATaMa.dockwidget.QGBox_saveSamplingClassified.setEnabled(True)
        AcATaMa.dockwidget.QPBtn_OpenClassificationDialog.setText(u"Open the classification dialog")
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(ClassificationDialog, self).reject()


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_buttons_config.ui'))


class ClassificationButtonsConfig(QtGui.QDialog, FORM_CLASS):
    def __init__(self, buttons_config):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.buttons_config = buttons_config if buttons_config is not None else {}
        # init with empty table
        self.table_buttons = dict(zip(range(1,31), [""]*30))
        self.create_table()

    def create_table(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        header = ["No.", "Classification Name", "Color", "Thematic raster class"]
        # init table
        self.tableBtnsConfig.setRowCount(len(self.table_buttons))
        self.tableBtnsConfig.setColumnCount(4)
        # hidden row labels
        self.tableBtnsConfig.verticalHeader().setVisible(False)
        # add Header
        self.tableBtnsConfig.setHorizontalHeaderLabels(header)
        # insert items
        for n, h in enumerate(header):
            if h == "No.":
                for m, item in enumerate(self.table_buttons.keys()):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Classification Name":
                for m, item in enumerate(self.table_buttons.values()):
                    if m+1 in self.buttons_config:
                        item_table = QTableWidgetItem(self.buttons_config[m + 1]["name"])
                    else:
                        item_table = QTableWidgetItem(str(item))
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Color":
                for m, item in enumerate(self.table_buttons.values()):
                    item_table = QTableWidgetItem()
                    if m+1 in self.buttons_config:
                        item_table.setBackground(QColor(self.buttons_config[m + 1]["color"]))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Thematic raster class":
                for m, item in enumerate(self.table_buttons.values()):
                    if valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicRaster):
                        if m+1 in self.buttons_config and self.buttons_config[m+1]["thematic_class"] is not None:
                            item_table = QTableWidgetItem(self.buttons_config[m + 1]["thematic_class"])
                        else:
                            item_table = QTableWidgetItem(str(item))
                    else:
                        item_table = QTableWidgetItem("No thematic raster")
                        item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        item_table.setForeground(QColor("lightGrey"))
                        item_h = QTableWidgetItem(h)
                        item_h.setForeground(QColor("lightGrey"))
                        self.tableBtnsConfig.setHorizontalHeaderItem(3, item_h)

                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)

        # adjust size of Table
        self.tableBtnsConfig.resizeColumnsToContents()
        self.tableBtnsConfig.resizeRowsToContents()
        # adjust the dialog based on table content
        dialog_width = self.tableBtnsConfig.horizontalHeader().length() + 50
        self.resize(dialog_width, self.height())

        self.tableBtnsConfig.itemClicked.connect(self.table_item_clicked)

    def table_item_clicked(self, tableItem):
        if tableItem.text() == "No thematic raster":
            return
        # set color
        if tableItem.column() == 2:
            remember_color = tableItem.backgroundColor()
            remember_color = QColor("white") if remember_color.name() == QColor("black").name() else remember_color
            color = QColorDialog.getColor(remember_color, self)
            if color.isValid():
                tableItem.setBackground(color)
                self.tableBtnsConfig.clearSelection()
        # set the thematic raster class
        if tableItem.column() == 3:
            thematic_raster_class = ThematicRasterClasses()
            if thematic_raster_class.exec_():
                tableItem.setText(thematic_raster_class.pix_value)
                self.tableBtnsConfig.item(tableItem.row(), 2).setBackground(thematic_raster_class.color)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_thematic_raster_classes.ui'))


class ThematicRasterClasses(QtGui.QDialog, FORM_CLASS):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        # init with empty table
        self.create_table()

    def create_table(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        header = ["Pix Val", "Color", "Select"]
        # get color table from raster
        nodata = int(AcATaMa.dockwidget.nodata_ThematicRaster.value())
        thematic_table = {"color_table": get_color_table(
            get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicRaster), band_number=1, nodata=nodata)}

        if not thematic_table["color_table"]:
            # clear table
            self.tableOfClasses.setRowCount(0)
            self.tableOfClasses.setColumnCount(0)
            return
        thematic_table["row_count"] = len(thematic_table["color_table"].values()[0])
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
                for m, item in enumerate(thematic_table["color_table"]["Pixel Value"]):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Color":
                for m in range(thematic_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setBackground(QColor(thematic_table["color_table"]["Red"][m],
                                                    thematic_table["color_table"]["Green"][m],
                                                    thematic_table["color_table"]["Blue"][m],
                                                    thematic_table["color_table"]["Alpha"][m]))
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Select":
                for m in range(thematic_table["row_count"]):
                    item_table = QtGui.QPushButton("Select this")
                    item_table.clicked.connect(self.select_clicked)
                    self.tableOfClasses.setCellWidget(m, n, item_table)

        # adjust size of Table
        self.tableOfClasses.resizeColumnsToContents()
        self.tableOfClasses.resizeRowsToContents()
        # adjust the dialog based on table content
        dialog_width = self.tableOfClasses.horizontalHeader().length() + 50
        self.resize(dialog_width, self.height())

    def select_clicked(self):
        button = self.sender()
        row = self.tableOfClasses.indexAt(button.pos()).row()

        self.pix_value = self.tableOfClasses.item(row, 0).text()
        self.color = self.tableOfClasses.item(row, 1).backgroundColor()

        self.accept()
