# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2021 by Xavier Corredor Llano, SMByC
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
import functools
import traceback
import os, sys, subprocess

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication, QMessageBox, QPushButton
from qgis.PyQt.QtGui import QCursor
from qgis.core import Qgis
from qgis.utils import iface


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            # restore mouse
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()

            # select the message bar
            from AcATaMa.gui.response_design_window import ResponseDesignWindow
            if ResponseDesignWindow.is_opened:
                msg_bar = ResponseDesignWindow.instance.MsgBar
            else:
                msg_bar = iface.messageBar()

            msg_bar.clearWidgets()

            # message in status bar with details
            def details_message_box(error, more_details):
                msgBox = QMessageBox()
                msgBox.setWindowTitle("AcATaMa - Error handler")
                msgBox.setText("<i>{}</i>".format(error))
                msgBox.setInformativeText("If you consider this as an AcATaMa error, report it in "
                                          "<a href='https://github.com/SMByC/AcATaMa/issues'>issue tracker</a>"
                                          " including the traceback below.")
                msgBox.setDetailedText(more_details)
                msgBox.setTextFormat(Qt.RichText)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec()
                del msgBox

            error = str(err)
            widget = msg_bar.createMessage("AcATaMa", error)
            more_details = traceback.format_exc()

            button = QPushButton(widget)
            button.setText("Show details...")
            button.pressed.connect(lambda: details_message_box(error, more_details))
            widget.layout().addWidget(button)

            msg_bar.pushWidget(widget, level=Qgis.Warning, duration=20)

    return wrapper


def wait_process(func):
    @error_handler
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # mouse wait
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        # do
        obj_returned = func(*args, **kwargs)
        # restore mouse
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        # finally return the object by f
        return obj_returned
    return wrapper


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
