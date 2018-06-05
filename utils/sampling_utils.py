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
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.PyQt.QtGui import QColor

from AcATaMa.utils.qgis_utils import get_layer_by_name, get_current_layer_in, get_current_file_path_in
from AcATaMa.utils.system_utils import wait_process, block_signals_to
from AcATaMa.utils.others_utils import mask


@wait_process()
def get_pixel_count_by_category(srs_table, categorical_raster):
    """Get the total pixel count for all pixel values"""
    from osgeo import gdalnumeric
    cateR_numpy = gdalnumeric.LoadFile(categorical_raster)
    pixel_count = []
    for pixel_value in srs_table["color_table"]["Pixel Value"]:
        pixel_count.append((cateR_numpy == int(pixel_value)).sum())
    return pixel_count


def get_num_samples_by_area_based_proportion(srs_table, total_std_error):
    total_pixel_count = float(sum(mask(srs_table["pixel_count"], srs_table["On"])))
    ratio_pixel_count = [p_c / total_pixel_count for p_c in mask(srs_table["pixel_count"], srs_table["On"])]
    Si = [(float(std_error)*(1-float(std_error))) ** 0.5 for std_error in mask(srs_table["std_error"], srs_table["On"])]
    total_num_samples = (sum([rpc*si for rpc, si in zip(ratio_pixel_count, Si)])/total_std_error)**2

    num_samples = []
    idx = 0
    for item_enable in srs_table["On"]:
        if item_enable:
            num_samples.append(str(int(round(ratio_pixel_count[idx] * total_num_samples))))
            idx += 1
        else:
            num_samples.append(str("0"))
    return num_samples


def get_num_samples_by_keeping_total_samples(srs_table, new_num_samples):
    """Redistribute the samples number by area based proportion keeping
    the total of samples, this occur when one num sample is changed
    """
    for idx, (old_ns, new_ns) in enumerate(zip(srs_table["num_samples"], new_num_samples)):
        if old_ns != new_ns:
            sample_idx = idx
            sample_diff = float(old_ns) - float(new_ns)
            break
    distribute_on = list(srs_table["On"])
    distribute_on[sample_idx] = False

    total_pixel_count = float(sum(mask(srs_table["pixel_count"], distribute_on)))
    ratio_pixel_count = [p_c / total_pixel_count for p_c in mask(srs_table["pixel_count"], distribute_on)]

    num_samples = []
    idx = 0
    for global_idx, item_enable in enumerate(distribute_on):
        if item_enable:
            num_samples.append(str(int(round(int(new_num_samples[global_idx]) + ratio_pixel_count[idx] * sample_diff))))
            idx += 1
        else:
            num_samples.append(str(new_num_samples[global_idx]))

    return num_samples


@wait_process()
def update_srs_table_content(dockwidget, srs_table):
    with block_signals_to(dockwidget.QTableW_StraRS):
        # init table
        dockwidget.QTableW_StraRS.setRowCount(srs_table["row_count"])
        dockwidget.QTableW_StraRS.setColumnCount(srs_table["column_count"])

        # enter data onto Table
        for n, key in enumerate(srs_table["header"]):
            if key == "Pix Val":
                for m, item in enumerate(srs_table["color_table"]["Pixel Value"]):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    dockwidget.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Color":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setBackground(QColor(srs_table["color_table"]["Red"][m],
                                                    srs_table["color_table"]["Green"][m],
                                                    srs_table["color_table"]["Blue"][m],
                                                    srs_table["color_table"]["Alpha"][m]))
                    dockwidget.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Num Samples":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem(srs_table["num_samples"][m])
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if not srs_table["On"][m]:
                        item_table.setForeground(QColor("lightGrey"))
                        item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    dockwidget.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Std Error":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem(srs_table["std_error"][m])
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if not srs_table["On"][m]:
                        item_table.setForeground(QColor("lightGrey"))
                        item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    dockwidget.QTableW_StraRS.setItem(m, n, item_table)
            if key == "On":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if srs_table["On"][m]:
                        item_table.setCheckState(Qt.Checked)
                    else:
                        item_table.setCheckState(Qt.Unchecked)
                    dockwidget.QTableW_StraRS.setItem(m, n, item_table)

        # hidden row labels
        dockwidget.QTableW_StraRS.verticalHeader().setVisible(False)
        # add Header
        dockwidget.QTableW_StraRS.setHorizontalHeaderLabels(srs_table["header"])
        # adjust size of Table
        dockwidget.QTableW_StraRS.resizeColumnsToContents()
        dockwidget.QTableW_StraRS.resizeRowsToContents()
        # set label total samples
        total_num_samples = sum([int(x) for x in mask(srs_table["num_samples"], srs_table["On"])])
        dockwidget.TotalNumSamples.setText(str(total_num_samples))
        # set maximum and reset the value in progress bar status
        dockwidget.widget_generate_StraRS.QPBar_GenerateSampling.setValue(0)
        dockwidget.widget_generate_StraRS.QPBar_GenerateSampling.setMaximum(total_num_samples)


def fill_stratified_sampling_table(dockwidget):
    try:
        # check the current selected file
        get_layer_by_name(dockwidget.QCBox_CategRaster_StraRS.currentText()).dataProvider()
        # check sampling method selected
        if not dockwidget.QCBox_StraRS_Method.currentText():
            raise Exception
    except:
        # clear table
        dockwidget.QTableW_StraRS.setRowCount(0)
        dockwidget.QTableW_StraRS.setColumnCount(0)
        return

    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        srs_method = "fixed values"
        dockwidget.widget_TotalExpectedSE.setHidden(True)
    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        srs_method = "area based proportion"
        dockwidget.widget_TotalExpectedSE.setVisible(True)

    if dockwidget.QCBox_CategRaster_StraRS.currentText() in dockwidget.srs_tables.keys() and \
        srs_method in dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()].keys():
        # restore values saved for number of samples configured for selected categorical file
        srs_table = dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()][srs_method]
    else:
        from AcATaMa.core.raster import get_current_colors_style
        # init a new stratified random sampling table
        srs_table = {"color_table": get_current_colors_style(
            get_current_layer_in(dockwidget.QCBox_CategRaster_StraRS),
            band_number=int(dockwidget.QCBox_band_CategRaster_StraRS.currentText()),
            nodata=int(dockwidget.nodata_CategRaster_StraRS.value()))}

        if not srs_table["color_table"]:
            # clear table
            dockwidget.QTableW_StraRS.setRowCount(0)
            dockwidget.QTableW_StraRS.setColumnCount(0)
            # unselect
            dockwidget.QCBox_StraRS_Method.setCurrentIndex(-1)
            return
        srs_table["row_count"] = len(srs_table["color_table"].values()[0])

        if srs_method == "fixed values":
            srs_table["header"] = ["Pix Val", "Color", "Num Samples"]
            srs_table["column_count"] = len(srs_table["header"])
            srs_table["num_samples"] = [str(0)]*srs_table["row_count"]
            srs_table["On"] = [True] * srs_table["row_count"]

        if srs_method == "area based proportion":
            srs_table["header"] = ["Pix Val", "Color", "Num Samples", "Std Error", "On"]
            srs_table["column_count"] = len(srs_table["header"])
            srs_table["std_error"] = [str(0.01)]*srs_table["row_count"]
            srs_table["pixel_count"] = \
                get_pixel_count_by_category(srs_table, get_current_file_path_in(dockwidget.QCBox_CategRaster_StraRS))
            total_std_error = dockwidget.TotalExpectedSE.value()
            srs_table["On"] = [True] * srs_table["row_count"]
            srs_table["num_samples"] = get_num_samples_by_area_based_proportion(srs_table, total_std_error)

        # save srs table
        if dockwidget.QCBox_CategRaster_StraRS.currentText() not in dockwidget.srs_tables.keys():
            dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()] = {}
        dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()][srs_method] = srs_table

    # update content
    update_srs_table_content(dockwidget, srs_table)


def update_stratified_sampling_table(dockwidget, changes_from):
    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        srs_method = "fixed values"
    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        srs_method = "area based proportion"
    srs_table = dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()][srs_method]

    if changes_from == "TotalExpectedSE":
        srs_table["num_samples"] = \
            get_num_samples_by_area_based_proportion(srs_table, dockwidget.TotalExpectedSE.value())

    if changes_from == "TableContent":
        num_samples = []
        std_error = []
        on = []
        try:
            for row in range(dockwidget.QTableW_StraRS.rowCount()):
                num_samples.append(dockwidget.QTableW_StraRS.item(row, 2).text())
                if srs_method == "area based proportion":
                    std_error.append(dockwidget.QTableW_StraRS.item(row, 3).text())
                    if dockwidget.QTableW_StraRS.item(row, 4).checkState() == 2:
                        on.append(True)
                    if dockwidget.QTableW_StraRS.item(row, 4).checkState() == 0:
                        on.append(False)
        except:
            return
        if srs_method == "fixed values":
            srs_table["num_samples"] = num_samples
        if srs_method == "area based proportion":
            srs_table["std_error"] = std_error
            srs_table["On"] = on
            if srs_table["num_samples"] != num_samples:
                # only change the number of samples keeping the total samples
                srs_table["num_samples"] = get_num_samples_by_keeping_total_samples(srs_table, num_samples)
            else:
                srs_table["num_samples"] = \
                    get_num_samples_by_area_based_proportion(srs_table, dockwidget.TotalExpectedSE.value())

    # update content
    update_srs_table_content(dockwidget, srs_table)
    # save srs table
    dockwidget.srs_tables[dockwidget.QCBox_CategRaster_StraRS.currentText()][srs_method] = srs_table

