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

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_dialog.ui'))


class ClassificationDialog(QtGui.QDialog, FORM_CLASS):
    view_widgets = []

    def __init__(self, sampling_layer):
        QtGui.QDialog.__init__(self)

        self.setupUi(self)

        # save the six view render widgets
        ClassificationDialog.view_widgets = \
            [self.render_window_1, self.render_window_2, self.render_window_3,
             self.render_window_4, self.render_window_5, self.render_window_6]

        # setup view widget
        [view_widget.setup_view_widget(sampling_layer) for view_widget in ClassificationDialog.view_widgets]

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
        self.class_buttons_config = ClassificationButtonsConfig()
        self.SetClassification.clicked.connect(self.set_buttons_classification)

    def set_buttons_classification(self):
        if self.class_buttons_config.exec_():
            print self.class_buttons_config.table.rowCount()

            buttons = {}
            for i in range(5):
                # keep a reference to the buttons
                buttons[i] = QtGui.QPushButton('row %d, col %d' % (i, 0))
                # add to the layout
                self.gridButtonsClassification.addWidget(buttons[i], i, 0)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_buttons_config.ui'))


class ClassificationButtonsConfig(QtGui.QDialog, FORM_CLASS):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
