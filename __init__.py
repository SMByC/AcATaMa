# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                             -------------------
        copyright            : (C) 2017-2019 by Xavier Corredor Llano, SMByC
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
 This script initializes the plugin, making it known to QGIS.
"""


from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

from AcATaMa.utils.extra_deps import load_install_extra_deps, WaitDialog


def pre_init_plugin(iface):
    app = QCoreApplication.instance()
    parent = iface.mainWindow()
    dialog = None
    log = ''
    try:
        for msg_type, msg_val in load_install_extra_deps():
            app.processEvents()
            if msg_type == 'log':
                log += msg_val
            elif msg_type == 'needs_install':
                dialog = WaitDialog(parent, 'AcATaMa - installing dependencies')
            elif msg_type == 'install_done':
                dialog.accept()
    except Exception as e:
        if dialog:
            dialog.accept()
        QMessageBox.critical(parent, 'AcATaMa - installing dependencies',
                             'An error occurred during the installation of Python packages. ' +
                             'Click on "Stack Trace" in the QGIS message bar for details.')
        raise RuntimeError('\nAcATaMa: Error installing Python packages. Read install instruction: '
                           'https://smbyc.github.io/AcATaMa\nLog:\n' + log) from e


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AcATaMa class from file AcATaMa.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # load/install extra python dependencies
    pre_init_plugin(iface)

    #
    from .acatama import AcATaMa
    return AcATaMa(iface)
