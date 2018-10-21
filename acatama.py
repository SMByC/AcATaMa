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
import os.path
import shutil

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon

# Import the code for the DockWidget
from AcATaMa.core.accuracy_assessment import AccuracyAssessmentDialog
from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget
from AcATaMa.gui.about_dialog import AboutDialog
from AcATaMa.gui.classification_dialog import ClassificationDialog
from AcATaMa.utils.qgis_utils import unload_layer_in_qgis

# Initialize Qt resources from file resources.py
from . import resources


class AcATaMa(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'AcATaMa_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        print("** INITIALIZING AcATaMa")

        self.menu_name_plugin = self.tr("Accuracy Assessment of Thematic Maps")
        self.pluginIsActive = False
        self.dockwidget = None

        self.about_dialog = AboutDialog()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("AcATaMa", message)

    def initGui(self):
        ### Main dockwidget menu
        # Create action that will start plugin configuration
        icon_path = ':/plugins/AcATaMa/icons/acatama.svg'
        self.dockable_action = QAction(QIcon(icon_path), "AcATaMa", self.iface.mainWindow())
        # connect the action to the run method
        self.dockable_action.triggered.connect(self.run)
        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.dockable_action)
        self.iface.addPluginToMenu(self.menu_name_plugin, self.dockable_action)

        # Plugin info
        # Create action that will start plugin configuration
        icon_path = ':/plugins/AcATaMa/icons/about.svg'
        self.about_action = QAction(QIcon(icon_path), self.tr('About'), self.iface.mainWindow())
        # connect the action to the run method
        self.about_action.triggered.connect(self.about)
        # Add toolbar button and menu item
        self.iface.addPluginToMenu(self.menu_name_plugin, self.about_action)

    def about(self):
        self.about_dialog.show()

    #--------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING AcATaMa"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = AcATaMaDockWidget()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)
            # reload
            self.dockwidget.QPBtn_PluginClearReload.clicked.connect(self.clear_reload_plugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        print("** CLOSING AcATaMa")
        if ClassificationDialog.is_opened:
            self.dockwidget.classification_dialog.closing()
            self.dockwidget.classification_dialog.reject(is_ok_to_close=True)

        if AccuracyAssessmentDialog.is_opened:
            self.dockwidget.accuracy_assessment_dialog.closing()
            self.dockwidget.accuracy_assessment_dialog.reject(is_ok_to_close=True)

        self.removes_temporary_files()

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None
        self.dockwidget.deleteLater()
        self.dockwidget = None

        self.pluginIsActive = False

        from qgis.utils import reloadPlugin
        reloadPlugin("AcATaMa")

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        print("** UNLOAD AcATaMa")
        self.removes_temporary_files()
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(self.menu_name_plugin, self.dockable_action)
        self.iface.removePluginMenu(self.menu_name_plugin, self.about_action)
        self.iface.removeToolBarIcon(self.dockable_action)

        if self.dockwidget:
            self.iface.removeDockWidget(self.dockwidget)

    def clear_reload_plugin(self):
        # first prompt
        quit_msg = "Are you sure you want to: clean tmp files, delete unsaved classification, " \
                   "clean all fields and reload plugin?"
        reply = QMessageBox.question(None, 'Clear all and reload the AcATaMa plugin.',
                                     quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        self.onClosePlugin()
        from qgis.utils import plugins
        plugins["AcATaMa"].run()

    def removes_temporary_files(self):
        if not self.dockwidget:
            return
        # unload all layers instances from Qgis saved in tmp dir
        try:
            d = self.dockwidget.tmp_dir
            files_in_tmp_dir = [os.path.join(d, f) for f in os.listdir(d)
                                if os.path.isfile(os.path.join(d, f))]
        except: files_in_tmp_dir = []

        for file_tmp in files_in_tmp_dir:
            unload_layer_in_qgis(file_tmp)

        # clear self.dockwidget.tmp_dir
        if self.dockwidget.tmp_dir and os.path.isdir(self.dockwidget.tmp_dir):
            shutil.rmtree(self.dockwidget.tmp_dir, ignore_errors=True)
        self.dockwidget.tmp_dir = None

        # clear qgis main canvas
        self.iface.mapCanvas().clearCache()
        self.iface.mapCanvas().refresh()
