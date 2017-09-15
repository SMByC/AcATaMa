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
from PyQt4.QtGui import QTableWidgetItem

from AcATaMa.core.classification import Classification

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_dialog.ui'))


class ClassificationDialog(QtGui.QDialog, FORM_CLASS):
    view_widgets = []

    def __init__(self, sampling_layer):
        QtGui.QDialog.__init__(self)
        self.classification = Classification(sampling_layer)

        self.setupUi(self)

        # save the six view render widgets
        ClassificationDialog.view_widgets = \
            [self.render_window_1, self.render_window_2, self.render_window_3,
             self.render_window_4, self.render_window_5, self.render_window_6]

        # setup view widget
        [view_widget.setup_view_widget(sampling_layer) for view_widget in ClassificationDialog.view_widgets]
        for idx, view_widget in enumerate(ClassificationDialog.view_widgets): view_widget.id = idx

        # set the master view and label names for each view
        for num_view, view_widget in zip(range(1, 7), ClassificationDialog.view_widgets):
            view_widget.master_view = ClassificationDialog.view_widgets[0]
            view_widget.view_label_name.setText("View {}:".format(num_view))

        # set some config for master view
        ClassificationDialog.view_widgets[0].view_label_name.setText("Master:")
        ClassificationDialog.view_widgets[0].scaleFactor.setReadOnly(True)
        ClassificationDialog.view_widgets[0].scaleFactor.setEnabled(False)
        ClassificationDialog.view_widgets[0].scaleFactor.setToolTip("Always 1 for the master view")

        # set classification buttons
        self.classification_btns_config = ClassificationButtonsConfig()
        self.SetClassification.clicked.connect(self.set_buttons_classification)

        # set dialog title
        self.setWindowTitle("Classification of samples for " + sampling_layer.name())

        # move through samples
        self.previousSampleButton.clicked.connect(self.previous_sample)
        self.nextSampleButton.clicked.connect(self.next_sample)

        # set total samples
        self.progressClassification.setMaximum(len(self.classification.points))

        # actions for fit and go to current sample
        self.radiusFitToSample.valueChanged.connect(lambda: self.show_and_go_to_current_sample(highlight=False))
        self.gotoCurrentSample.clicked.connect(lambda: self.show_and_go_to_current_sample(highlight=True))

        # init current point
        self.current_sample_idx = 0
        self.current_sample = None
        self.set_current_sample()

    def set_current_sample(self):
        """Set the current sample"""
        # clean the old mark first
        if self.current_sample:
            for idx, view_widget in enumerate(ClassificationDialog.view_widgets):
                if view_widget.is_active:
                    self.current_sample.remove_marker(view_widget)
        self.current_sample = self.classification.points[self.current_sample_idx]
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
        self.totalClassified.setText(str(sum(sample.is_classified for sample in self.classification.points)))
        self.totalNotClassified.setText(str(sum(not sample.is_classified for sample in self.classification.points)))

    def show_and_go_to_current_sample(self, highlight=True):
        for idx, view_widget in enumerate(ClassificationDialog.view_widgets):
            if view_widget.is_active:
                # create the marker
                self.current_sample.show_marker(view_widget)
                # fit to current point/marker
                self.current_sample.fit_to(view_widget, self.radiusFitToSample.value())
                if highlight:
                    # highlight to marker
                    self.current_sample.highlight(view_widget)

    def previous_sample(self):
        if self.current_sample_idx < 1:
            return
        self.current_sample_idx -= 1
        self.set_current_sample()

    def next_sample(self):
        if self.current_sample_idx >= len(self.classification.points):
            return
        self.current_sample_idx += 1
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

    def closeEvent(self, e):
        """Called when the dialog is being closed"""
        pass


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
        header = ["No.", "Classification Name"]
        # init table
        self.tableBtnsConfig.setRowCount(len(self.table_buttons))
        self.tableBtnsConfig.setColumnCount(2)
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
        # hidden row labels
        self.tableBtnsConfig.verticalHeader().setVisible(False)
        # add Header
        self.tableBtnsConfig.setHorizontalHeaderLabels(header)
        # adjust size of Table
        self.tableBtnsConfig.resizeColumnsToContents()
        self.tableBtnsConfig.resizeRowsToContents()
