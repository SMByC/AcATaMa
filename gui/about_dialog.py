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
"""

import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'about_dialog.ui'))


class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        about_file = os.path.join(plugin_folder, 'gui', 'about.html')
        html_text = open(about_file).read()
        self.about_html.setHtml(html_text)
        self.about_html.setOpenExternalLinks(True)
