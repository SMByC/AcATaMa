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
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.PyQt.QtGui import QColor

from AcATaMa.utils.system_utils import wait_process, block_signals_to
from AcATaMa.utils.others_utils import mask, get_pixel_count_by_pixel_values, get_nodata_format


def check_min_distance(point, index, distance, points):
    """Check if distance from given point to all other points is greater
    than given value.
    """
    if distance == 0:
        return True

    neighbors = index.nearestNeighbor(point)
    if len(neighbors) == 0:
        return True

    if neighbors[0] in points:
        np = points[neighbors[0]]
        if np.distance(point) < distance:
            return False

    return True


def get_num_samples_by_area_based_proportion(srs_table, total_std_error):
    total_pixel_count = float(sum(mask(srs_table["pixel_count"], srs_table["On"])))
    ratio_pixel_count = [p_c / total_pixel_count for p_c in mask(srs_table["pixel_count"], srs_table["On"])]
    Si = [(float(ui)*(1-float(ui))) ** 0.5 for ui in mask(srs_table["ui"], srs_table["On"])]
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
    the total of samples, this occurs when a num sample item is changed
    """
    for idx, (old_ns, new_ns) in enumerate(zip(srs_table["num_samples"], new_num_samples)):
        if old_ns != new_ns:
            sample_idx = idx
            sample_diff = int(old_ns) - int(new_ns)
            break
    distribute_on = list(srs_table["On"])
    distribute_on[sample_idx] = False

    total_pixel_count = float(sum(mask(srs_table["pixel_count"], distribute_on)))
    ratio_pixel_count = [p_c / total_pixel_count for p_c in mask(srs_table["pixel_count"], distribute_on)]

    while True:
        num_samples = []
        idx = 0
        for global_idx, item_enable in enumerate(distribute_on):
            if item_enable:
                num_samples.append(str(int(round(int(new_num_samples[global_idx]) + ratio_pixel_count[idx] * sample_diff))))
                idx += 1
            else:
                num_samples.append(str(new_num_samples[global_idx]))
        # check if one of the new num samples is negative
        if any([int(ns) < 0 for ns in num_samples]):
            sample_diff += 1
        else:
            break

    # update the sample_idx (editing) with the (new) sample_diff
    num_samples[sample_idx] = str(int(srs_table["num_samples"][sample_idx]) - sample_diff)

    return num_samples


@wait_process
def update_srs_table_content(srs_table):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    with block_signals_to(sampling_design.QTableW_StraRS):
        # init table
        sampling_design.QTableW_StraRS.setRowCount(srs_table["row_count"])
        sampling_design.QTableW_StraRS.setColumnCount(srs_table["column_count"])

        # first check and disable the classes with zero pixels on the map
        for n, key in enumerate(srs_table["header"]):
            if key == "On":
                for m in range(srs_table["row_count"]):
                    if srs_table["pixel_count"][m] == 0:
                        srs_table["On"][m] = False
                        item_table = QTableWidgetItem()
                        item_table.setFlags(item_table.flags() & ~Qt.ItemIsEnabled)
                        item_table.setCheckState(Qt.Unchecked)
                        item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                        item_table.setToolTip("DISABLED: This class has 0 pixels on the map")
                        sampling_design.QTableW_StraRS.setItem(m, n, item_table)

        # enter data onto Table
        for n, key in enumerate(srs_table["header"]):
            if key == "Pix Val":
                for m, item in enumerate(srs_table["values_and_colors_table"]["Pixel Value"]):
                    item_table = QTableWidgetItem(str(item))
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    sampling_design.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Color":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem()
                    item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item_table.setBackground(QColor(srs_table["values_and_colors_table"]["Red"][m],
                                                    srs_table["values_and_colors_table"]["Green"][m],
                                                    srs_table["values_and_colors_table"]["Blue"][m],
                                                    srs_table["values_and_colors_table"]["Alpha"][m]))
                    sampling_design.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Num Samples":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem(srs_table["num_samples"][m])
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
                        item_table.setToolTip("Total number of samples for this class, this is generated\n"
                                              "automatically based on the area proportion by the activated\n"
                                              "classes, overall expected standard error and its user\n"
                                              "accuracy expected value.")
                    if not srs_table["On"][m]:
                        item_table.setForeground(QColor("lightGrey"))
                        item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    sampling_design.QTableW_StraRS.setItem(m, n, item_table)
            if key == "Ui":
                for m in range(srs_table["row_count"]):
                    item_table = QTableWidgetItem(srs_table["ui"][m])
                    item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    item_table.setToolTip("User's accuracy confidence for this map class. This is the\n"
                                          "probability that a pixel classified as class i is actually class i.\n\n"
                                          "Between 0.6 - 0.8 for unstable classes\n"
                                          "Between 0.8 - 0.95 for stable classes")
                    if not srs_table["On"][m]:
                        item_table.setForeground(QColor("lightGrey"))
                        item_table.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    sampling_design.QTableW_StraRS.setItem(m, n, item_table)
            if key == "On":
                for m in range(srs_table["row_count"]):
                    if srs_table["pixel_count"][m] > 0:
                        item_table = QTableWidgetItem()
                        item_table.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        item_table.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                        item_table.setToolTip("Enable/disable this class")
                        if srs_table["On"][m]:
                            item_table.setCheckState(Qt.Checked)
                        else:
                            item_table.setCheckState(Qt.Unchecked)
                        sampling_design.QTableW_StraRS.setItem(m, n, item_table)

        # hidden row labels
        sampling_design.QTableW_StraRS.verticalHeader().setVisible(False)
        # add Header
        sampling_design.QTableW_StraRS.setHorizontalHeaderLabels(srs_table["header"])
        # adjust size of Table
        sampling_design.QTableW_StraRS.resizeColumnsToContents()
        sampling_design.QTableW_StraRS.resizeRowsToContents()
        # set label total samples
        total_num_samples = sum([int(x) for x in mask(srs_table["num_samples"], srs_table["On"])])
        sampling_design.TotalNumSamples.setText(str(total_num_samples))
        # set maximum and reset the value in progress bar status
        sampling_design.QPBar_GenerateSamples_StraRS.setValue(0)
        sampling_design.QPBar_GenerateSamples_StraRS.setMaximum(total_num_samples)


@wait_process
def reload_StraRS_table():
    """Reset the table, reloading the layer style, pixel count and restoring default values"""
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window
    # clear table
    sampling_design.QTableW_StraRS.setRowCount(0)
    sampling_design.QTableW_StraRS.setColumnCount(0)

    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        srs_method = "fixed values"
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        srs_method = "area based proportion"

    # delete style
    if sampling_design.QCBox_SamplingMap_StraRS.currentText() in sampling_design.srs_tables.keys() and \
        srs_method in sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()].keys():
        del sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()][srs_method]
    # delete pixel count
    if srs_method == "area based proportion":
        from AcATaMa.utils.others_utils import storage_pixel_count_by_pixel_values
        global storage_pixel_count_by_pixel_values
        layer = sampling_design.QCBox_SamplingMap_StraRS.currentLayer()
        band = int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText())
        nodata = get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text())
        if (layer, band, nodata) in storage_pixel_count_by_pixel_values:
            del storage_pixel_count_by_pixel_values[(layer, band, nodata)]

    fill_stratified_sampling_table()


def fill_stratified_sampling_table():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window
    try:
        # check the current selected file
        sampling_design.QCBox_SamplingMap_StraRS.currentLayer().dataProvider()
        # check sampling method selected
        if not sampling_design.QCBox_StraRS_Method.currentText():
            raise Exception
    except:
        # clear table
        sampling_design.QTableW_StraRS.setRowCount(0)
        sampling_design.QTableW_StraRS.setColumnCount(0)
        return

    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        srs_method = "fixed values"
        sampling_design.widget_TotalExpectedSE.setHidden(True)
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        srs_method = "area based proportion"
        sampling_design.widget_TotalExpectedSE.setVisible(True)

    srs_table = None
    if sampling_design.QCBox_SamplingMap_StraRS.currentText() in sampling_design.srs_tables.keys() and \
        srs_method in sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()].keys():
        # restore values saved for number of samples configured for selected post-stratification file
        srs_table = sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()][srs_method]

    if srs_table is None:
        from AcATaMa.core.map import get_values_and_colors_table
        # init a new stratified random sampling table
        srs_table = {"values_and_colors_table": get_values_and_colors_table(
            layer=sampling_design.QCBox_SamplingMap_StraRS.currentLayer(),
            band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
            nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()))}

        if not srs_table["values_and_colors_table"]:
            # clear table
            sampling_design.QTableW_StraRS.setRowCount(0)
            sampling_design.QTableW_StraRS.setColumnCount(0)
            # deselect
            sampling_design.QCBox_StraRS_Method.setCurrentIndex(-1)
            return
        srs_table["row_count"] = len(list(srs_table["values_and_colors_table"].values())[0])

        srs_table["pixel_count"] = list(
            get_pixel_count_by_pixel_values(sampling_design.QCBox_SamplingMap_StraRS.currentLayer(),
                                            int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
                                            srs_table["values_and_colors_table"]["Pixel Value"],
                                            get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text())).values())

        if srs_method == "fixed values":
            srs_table["header"] = ["Pix Val", "Color", "Num Samples", "On"]
            srs_table["column_count"] = len(srs_table["header"])
            srs_table["num_samples"] = [str(0)]*srs_table["row_count"]
            srs_table["On"] = [True] * srs_table["row_count"]

        if srs_method == "area based proportion":
            srs_table["header"] = ["Pix Val", "Color", "Num Samples", "Ui", "On"]
            srs_table["column_count"] = len(srs_table["header"])
            srs_table["ui"] = [str(0.8)]*srs_table["row_count"]
            total_std_error = sampling_design.TotalExpectedSE.value()
            srs_table["On"] = [True] * srs_table["row_count"]
            srs_table["num_samples"] = get_num_samples_by_area_based_proportion(srs_table, total_std_error)
            # adjust the number of samples based on minimum samples per stratum
            minimum_samples_per_stratum = sampling_design.MinimumSamplesPerStratum.value()
            for idx, ns in enumerate(srs_table["num_samples"]):
                if 0 < int(ns) < minimum_samples_per_stratum:
                    srs_table["num_samples"][idx] = str(minimum_samples_per_stratum)

        # save srs table
        if sampling_design.QCBox_SamplingMap_StraRS.currentText() not in sampling_design.srs_tables.keys():
            sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()] = {}
        sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()][srs_method] = srs_table

    # update content
    update_srs_table_content(srs_table)


def update_stratified_sampling_table(changes_from):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        srs_method = "fixed values"
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        srs_method = "area based proportion"
    srs_table = sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()][srs_method]

    if changes_from in ["TotalExpectedSE", "MinimumSamplesPerStratum"]:
        srs_table["num_samples"] = \
            get_num_samples_by_area_based_proportion(srs_table, sampling_design.TotalExpectedSE.value())

    if changes_from == "TableContent":
        num_samples = []
        ui = []
        on = []

        for row in range(sampling_design.QTableW_StraRS.rowCount()):
            num_samples_in_row = sampling_design.QTableW_StraRS.item(row, 2).text()
            if not num_samples_in_row.isdigit() or int(num_samples_in_row) < 0:
                num_samples_in_row = srs_table["num_samples"][row]
            num_samples.append(num_samples_in_row)
            if srs_method == "fixed values":
                if sampling_design.QTableW_StraRS.item(row, 3).checkState() == 2:
                    on.append(True)
                if sampling_design.QTableW_StraRS.item(row, 3).checkState() == 0:
                    on.append(False)
            if srs_method == "area based proportion":
                ui.append(sampling_design.QTableW_StraRS.item(row, 3).text())
                if sampling_design.QTableW_StraRS.item(row, 4).checkState() == 2:
                    on.append(True)
                if sampling_design.QTableW_StraRS.item(row, 4).checkState() == 0:
                    on.append(False)

        if srs_method == "fixed values":
            srs_table["num_samples"] = num_samples
            srs_table["On"] = on
        if srs_method == "area based proportion":
            srs_table["ui"] = ui
            srs_table["On"] = on
            if srs_table["num_samples"] != num_samples:
                # only change the number of samples keeping the total samples
                srs_table["num_samples"] = get_num_samples_by_keeping_total_samples(srs_table, num_samples)
            else:
                srs_table["num_samples"] = \
                    get_num_samples_by_area_based_proportion(srs_table, sampling_design.TotalExpectedSE.value())

    # adjusts the number of samples based on minimum samples per stratum
    minimum_samples_per_stratum = sampling_design.MinimumSamplesPerStratum.value()
    if srs_method == "area based proportion":
        for idx, ns in enumerate(srs_table["num_samples"]):
            if srs_table["On"][idx] and int(ns) < minimum_samples_per_stratum:
                srs_table["num_samples"][idx] = str(minimum_samples_per_stratum)

    # update content
    update_srs_table_content(srs_table)
    # save srs table
    sampling_design.srs_tables[sampling_design.QCBox_SamplingMap_StraRS.currentText()][srs_method] = srs_table

