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
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QPushButton
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtGui import QColor

from AcATaMa.core.map import get_values_and_colors_table
from AcATaMa.utils.system_utils import error_handler

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'post_stratification_classes_dialog.ui'))


class PostStratificationClassesDialog(QDialog, FORM_CLASS):
    instances = {}

    def __init__(self, post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata, set_classes_selected=None):
        QDialog.__init__(self)
        self.setupUi(self)
        self.post_stratification_map_layer = post_stratification_map_layer
        self.post_stratification_map_band = post_stratification_map_band
        self.post_stratification_map_nodata = post_stratification_map_nodata
        self.classes_selected = \
            [i.strip() for i in (set_classes_selected.split(',') if set_classes_selected and
                                                                    set_classes_selected != "click to select" else [])]
        if self.create_table():
            # save instance
            PostStratificationClassesDialog.instances[
                (post_stratification_map_layer, post_stratification_map_band, post_stratification_map_nodata)] = self

    @error_handler
    def create_table(self):
        header = ["Pix Val", "Color", "Select"]
        # get color table from raster
        classes_table = {"values_and_colors_table": get_values_and_colors_table(
            self.post_stratification_map_layer,
            band=self.post_stratification_map_band,
            nodata=self.post_stratification_map_nodata)}

        if not classes_table["values_and_colors_table"]:
            # clear table
            self.tableOfClasses.setRowCount(0)
            self.tableOfClasses.setColumnCount(0)
            return False

        classes_table["row_count"] = len(list(classes_table["values_and_colors_table"].values())[0])
        # init table
        self.tableOfClasses.setRowCount(classes_table["row_count"])
        self.tableOfClasses.setColumnCount(3)
        # hidden row labels
        self.tableOfClasses.verticalHeader().setVisible(False)
        # add Header
        self.tableOfClasses.setHorizontalHeaderLabels(header)

        # insert items
        for n, h in enumerate(header):
            if h == "Pix Val":
                for m, item in enumerate(classes_table["values_and_colors_table"]["Pixel Value"]):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Color":
                for m in range(classes_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setBackground(QColor(classes_table["values_and_colors_table"]["Red"][m],
                                                    classes_table["values_and_colors_table"]["Green"][m],
                                                    classes_table["values_and_colors_table"]["Blue"][m],
                                                    classes_table["values_and_colors_table"]["Alpha"][m]))
                    self.tableOfClasses.setItem(m, n, item_table)
            if h == "Select":
                for m, item in enumerate(classes_table["values_and_colors_table"]["Pixel Value"]):
                    item_table = QPushButton("  Select  ")
                    item_table.setCheckable(True)
                    if str(item) in self.classes_selected:
                        item_table.setChecked(True)
                        item_table.setText("Selected")
                    item_table.clicked.connect(self.select_clicked)
                    self.tableOfClasses.setCellWidget(m, n, item_table)

        # adjust size of Table
        self.tableOfClasses.resizeColumnsToContents()
        self.tableOfClasses.resizeRowsToContents()
        # adjust the dialog based on table content
        dialog_width = self.tableOfClasses.horizontalHeader().length() + 80
        self.resize(dialog_width, self.height())
        return True

    @pyqtSlot()
    def select_clicked(self):
        button = self.sender()
        row = self.tableOfClasses.indexAt(button.pos()).row()
        class_selected = self.tableOfClasses.item(row, 0).text()
        if button.isChecked():
            self.classes_selected.append(class_selected)
            self.classes_selected = sorted(self.classes_selected)
            button.setText("Selected")
            button.setDown(True)
        else:
            self.classes_selected.remove(class_selected)
            button.setText("  Select  ")
            button.setDown(False)
