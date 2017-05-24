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
from subprocess import call
from qgis.utils import iface


def do_clipping_with_shape(target_file, shape, out_path):
    filename, ext = os.path.splitext(os.path.basename(target_file))
    out_file = os.path.join(out_path, filename + "_clip" + ext)

    return_code = call('gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline ' +
                       shape + ' -dstnodata 0 ' + target_file + ' ' + out_file, shell=True)
    return out_file


def getLayerByName(layer_name):
    for layer in iface.mapCanvas().layers():
        if layer.name() == layer_name:
            return layer


def get_file_path(combo_box):
    return unicode(getLayerByName(combo_box.currentText()).dataProvider().dataSourceUri().split('|layerid')[0])
