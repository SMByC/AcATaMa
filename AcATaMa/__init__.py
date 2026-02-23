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
 This script initializes the plugin, making it known to QGIS.
"""
import os
import site


def pre_init_plugin():
    extra_libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "extlibs"))
    if os.path.isdir(extra_libs_path):
        # add to python path
        site.addsitedir(extra_libs_path)
        # register with pkg_resources if available (not bundled in Python 3.12+)
        try:
            import pkg_resources
            pkg_resources.working_set.add_entry(extra_libs_path)
        except ImportError:
            pass


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AcATaMa class from file AcATaMa.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # load extra python dependencies
    pre_init_plugin()

    #
    from .acatama import AcATaMa
    return AcATaMa(iface)
