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
import traceback
from subprocess import call

from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtCore import Qt
from qgis.gui import QgsMessageBar
from qgis.core import QgsMessageLog
from qgis.utils import iface


def error_handler():
    def decorate(f):
        def applicator(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception as e:
                # restore mouse
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
                # message in status bar
                msg_error = "An error has occurred in AcATaMa plugin. " \
                            "See more in Qgis log messages panel."
                iface.messageBar().pushMessage("Error", msg_error,
                                                    level=QgsMessageBar.CRITICAL, duration=0)
                # message in log
                msg_error = "\n################## ERROR IN ACATAMA PLUGIN:\n"
                msg_error += traceback.format_exc()
                msg_error += "\nPlease report the error in:\n" \
                             "\thttps://bitbucket.org/SMBYC/qgisplugin-acatama/issues"
                msg_error += "\n################## END REPORT"
                QgsMessageLog.logMessage(msg_error)
        return applicator
    return decorate


def wait_process():
    def decorate(f):
        def applicator(*args, **kwargs):
            # mouse wait
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # do
            f(*args, **kwargs)
            # restore mouse
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
        return applicator
    return decorate


def do_clipping_with_shape(target_file, shape, out_path):
    filename, ext = os.path.splitext(os.path.basename(target_file))
    out_file = os.path.join(out_path, filename + "_clip" + ext)

    return_code = call('gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline "{}" -dstnodata 0 "{}" "{}"'
                       .format(shape, target_file, out_file), shell=True)
    if return_code == 0:  # successfully
        return out_file
    else:
        iface.messageBar().pushMessage("Error", "While clipping the thematic raster.", level=QgsMessageBar.WARNING)


def getLayerByName(layer_name):
    for layer in iface.mapCanvas().layers():
        if layer.name() == layer_name:
            return layer


def get_file_path(combo_box):
    try:
        return unicode(getLayerByName(combo_box.currentText()).dataProvider().dataSourceUri().split('|layerid')[0])
    except:
        iface.messageBar().pushMessage("Error", "Please select a valid file", level=QgsMessageBar.WARNING)
