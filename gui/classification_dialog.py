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
from PyQt4.QtGui import QTableWidgetItem, QMessageBox, QDialogButtonBox, QSplitter, QColor, QColorDialog
from AcATaMa.core.classification import Classification
from AcATaMa.gui.classification_view_widget import ClassificationViewWidget

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_dialog.ui'))


class ClassificationDialog(QtGui.QDialog, FORM_CLASS):
    is_opened = False
    view_widgets = []
    current_sample = None

    def __init__(self, acatama_dockwidget, sampling_layer, columns, rows):
        QtGui.QDialog.__init__(self)
        self.acatama_dockwidget = acatama_dockwidget
        self.iface = acatama_dockwidget.iface
        ClassificationDialog.is_opened = True
        self.setupUi(self)

        # create dynamic size of the view render widgets windows
        # inside the grid with columns x rows divide by splitters
        h_splitters = []
        view_widgets = []
        for row in range(rows):
            splitter = QSplitter(Qt.Horizontal)
            for column in range(columns):
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

        # init classification
        self.classification = Classification(sampling_layer)

        # setup view widget
        [view_widget.setup_view_widget(sampling_layer) for view_widget in ClassificationDialog.view_widgets]
        for idx, view_widget in enumerate(ClassificationDialog.view_widgets): view_widget.id = idx

        # set the label names for each view
        for num_view, view_widget in enumerate(ClassificationDialog.view_widgets):
            view_widget.view_label_name.setText("View {}:".format(num_view+1))

        # set classification buttons
        self.classification_btns_config = ClassificationButtonsConfig()
        self.SetClassification.clicked.connect(self.set_buttons_classification)

        # set dialog title
        self.setWindowTitle("Classification of samples for " + sampling_layer.name())

        # dialog buttons box
        self.OkCancelButtons.button(QDialogButtonBox.Ok).setDisabled(True)
        self.OkCancelButtons.button(QDialogButtonBox.Ok).setToolTip("Only enabled when all samples are classified")
        self.OkCancelButtons.accepted.connect(self.accept_dialog)
        self.OkCancelButtons.rejected.connect(self.close_dialog)

        # move through samples
        self.nextSample.clicked.connect(self.next_sample)
        self.nextSampleNotClassified.clicked.connect(self.next_sample_not_classified)
        self.previousSample.clicked.connect(self.previous_sample)
        self.previousSampleNotClassified.clicked.connect(self.previous_sample_not_classified)

        # set total samples
        self.progressClassification.setMaximum(len(self.classification.points))

        # actions for fit and go to current sample
        self.radiusFitToSample.valueChanged.connect(lambda: self.show_and_go_to_current_sample(highlight=False))
        self.currentSample.clicked.connect(lambda: self.show_and_go_to_current_sample(highlight=True))

        # init current point
        self.current_sample_idx = 0
        self.current_sample = None
        self.set_current_sample()

    def set_current_sample(self):
        """Set the current sample"""
        self.current_sample = self.classification.points[self.current_sample_idx]
        ClassificationDialog.current_sample = self.current_sample
        # update progress bar
        self.progressClassification.setValue(self.current_sample_idx + 1)
        # show the class assigned
        self.display_sample_status()
        # show and go to marker
        self.show_and_go_to_current_sample()

    def classify_sample(self, class_id):
        if class_id:
            self.current_sample.class_id = class_id
            self.current_sample.is_classified = True
            self.display_sample_status()
            if self.autoNextSample.isChecked():
                # automatically follows the next sample
                self.next_sample()

    def display_sample_status(self):
        if self.current_sample.is_classified:
            class_name = self.classification.btns_config[self.current_sample.class_id]
            self.statusCurrentSample.setText(class_name)
            self.statusCurrentSample.setStyleSheet('QLabel {color: green;}')
        else:
            self.statusCurrentSample.setText("not classified")
            self.statusCurrentSample.setStyleSheet('QLabel {color: red;}')
        # update the total classified and not classified samples labels
        total_classified = sum(sample.is_classified for sample in self.classification.points)
        total_not_classified = sum(not sample.is_classified for sample in self.classification.points)
        self.totalClassified.setText(str(total_classified))
        self.totalNotClassified.setText(str(total_not_classified))
        # check is the classification is completed
        if total_not_classified == 0:
            self.OkCancelButtons.button(QDialogButtonBox.Ok).setEnabled(True)

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

    def set_buttons_classification(self):
        if self.classification_btns_config.exec_():
            # clear layout
            for i in range(self.gridButtonsClassification.count()):
                self.gridButtonsClassification.itemAt(i).widget().close()

            buttons = {}
            for row in range(self.classification_btns_config.tableBtnsConfig.rowCount()):
                classification_num = self.classification_btns_config.tableBtnsConfig.item(row, 0).text()
                classification_name = self.classification_btns_config.tableBtnsConfig.item(row, 1).text()
                if classification_name != "":
                    # save button config
                    buttons[int(classification_num)] = classification_name
                    # create button
                    QPButton = QtGui.QPushButton(classification_name)
                    QPButton.clicked.connect(lambda state, x=int(classification_num): self.classify_sample(x))
                    self.gridButtonsClassification.addWidget(QPButton, len(buttons)-1, 0)

            # save btns config
            self.classification.btns_config = buttons

    def closeEvent(self, event):
        self.close_dialog()
        event.ignore()

    def accept_dialog(self):
        self.closing()
        super(ClassificationDialog, self).accept()

    def close_dialog(self):
        quit_msg = "Are you sure you want to close the classification? " \
                   "all settings will be lost in the classification window"
        reply = QMessageBox.question(self, 'Close classification window',
                                     quit_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.closing()
            self.reject(is_ok_to_close=True)

    def closing(self):
        """Do this before close the classification dialog"""
        ClassificationDialog.is_opened = False
        # restore the states for some objects in the dockwidget
        self.acatama_dockwidget.selectSamplingFile.setEnabled(True)
        self.acatama_dockwidget.browseSamplingFile.setEnabled(True)
        self.acatama_dockwidget.buttonOpenClassificationDialog.setText(u"Classify the sampling file")

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(ClassificationDialog, self).reject()


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_buttons_config.ui'))


class ClassificationButtonsConfig(QtGui.QDialog, FORM_CLASS):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        # init with empty table
        self.table_buttons = dict(zip(range(1,31), [""]*30))
        self.create_table()

    def create_table(self):
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
                    item_table = QTableWidgetItem(str(item))
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Color":
                for m, item in enumerate(self.table_buttons.values()):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableBtnsConfig.setItem(m, n, item_table)
            if h == "Thematic raster class":
                for m, item in enumerate(self.table_buttons.values()):
                    if False:
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

        self.tableBtnsConfig.itemClicked.connect(self.table_item_clicked)

    def table_item_clicked(self, tableItem):
        if tableItem.text() == "No thematic raster":
            return
        if tableItem.column() == 2:
            color = QColorDialog.getColor()
            if color.isValid():
                tableItem.setBackground(color)
                self.tableBtnsConfig.clearSelection()


