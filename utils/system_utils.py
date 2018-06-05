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
import traceback
import os, sys, subprocess

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar
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
                iface.messageBar().pushMessage("AcATaMa", msg_error,
                                                level=QgsMessageBar.CRITICAL, duration=10)
                # message in log
                msg_error = "\n################## ERROR IN ACATAMA PLUGIN:\n"
                msg_error += traceback.format_exc()
                msg_error += "\nPlease report the error in:\n" \
                             "\thttps://bitbucket.org/smbyc/qgisplugin-acatama/issues"
                msg_error += "\n################## END REPORT"
                QgsMessageLog.logMessage(msg_error)
        return applicator
    return decorate


def wait_process(disable_button=None):
    def decorate(f):
        def applicator(*args, **kwargs):
            # disable button during process
            if disable_button:
                if "." in disable_button:
                    getattr(getattr(args[0], disable_button.split(".")[0]),
                            disable_button.split(".")[1]).setEnabled(False)
                else:
                    getattr(args[0], disable_button).setEnabled(False)
            # mouse wait
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # do
            obj_returned = f(*args, **kwargs)
            # restore mouse
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            # restore button
            if disable_button:
                if "." in disable_button:
                    getattr(getattr(args[0], disable_button.split(".")[0]),
                            disable_button.split(".")[1]).setEnabled(True)
                else:
                    getattr(args[0], disable_button).setEnabled(True)
            # finally return the object by f
            return obj_returned
        return applicator
    return decorate


def open_file(filename):
    """Open a file with the standard application"""
    filename = os.path.abspath(filename)

    if sys.platform == "linux" or sys.platform == "linux2":
        # Linux
        subprocess.call(["xdg-open", filename])
    elif sys.platform == "darwin":
        # OS X
        subprocess.call(["open", filename])
    elif sys.platform == "win32":
        # Windows
        os.startfile(filename)


class block_signals_to(object):
    """Block all signals emits from specific QT object"""
    def __init__(self, object_to_block):
        self.object_to_block = object_to_block

    def __enter__(self):
        # block
        self.object_to_block.blockSignals(True)

    def __exit__(self, type, value, traceback):
        # unblock
        self.object_to_block.blockSignals(False)
