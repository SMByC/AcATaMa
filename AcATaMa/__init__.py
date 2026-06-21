"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                             -------------------
        copyright            : (C) 2017-2026 by Xavier C. Llano, SMByC
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

from .utils import extlibs


def pre_init_plugin():
    try:
        extlibs.ensure_extlibs()
    except extlibs.ExtlibsError as error:
        extlibs.show_install_error(error)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AcATaMa class from file AcATaMa.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # load extra python dependencies
    pre_init_plugin()

    #
    from . import resources_rc  # noqa: F401
    from .acatama import AcATaMa

    return AcATaMa(iface)
