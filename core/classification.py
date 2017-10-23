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
from collections import OrderedDict
from random import shuffle

from AcATaMa.core.dockwidget import get_current_file_path_in, get_file_path_of_layer
from AcATaMa.core.point import ClassificationPoint


class Classification:
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the classification buttons properties
        # {btn_id: {"name", "color", "thematic_class"}}
        self.btns_config = None
        # get all points from the layer
        # [ClassificationPoint, ClassificationPoint, ...]
        self.points = self.getPoints()
        # save and init the current sample index
        self.current_sample_idx = 0
        # grid config
        self.grid_columns = 3
        self.grid_rows = 2
        # radius to sample
        self.fit_to_sample = 120
        # save views widget config
        # {N: {"name", "render_file", "scale_factor"}, ...}
        self.view_widgets_config = {}
        # when all points are classified
        self.is_completed = False

        # shuffle the list items
        shuffle(self.points)
        # save instance
        Classification.instances[sampling_layer] = self

    def getPoints(self):
        points = []
        for qgs_feature in self.sampling_layer.getFeatures():
            geom = qgs_feature.geometry()
            x, y = geom.asPoint()
            points.append(ClassificationPoint(x, y))
        return points

    def save_config(self, file_out):
        import yaml
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        def setup_yaml():
            """
            Keep dump ordered with orderedDict
            """
            represent_dict_order = lambda self, data: self.represent_mapping('tag:yaml.org,2002:map', data.items())
            yaml.add_representer(OrderedDict, represent_dict_order)
        setup_yaml()

        data = OrderedDict({
            "thematic_raster": {"path": get_current_file_path_in(AcATaMa.dockwidget.selectThematicRaster, show_message=False),
                                "nodata": AcATaMa.dockwidget.nodata_ThematicRaster.value()},
            "sampling_layer": get_file_path_of_layer(self.sampling_layer),
            "fit_to_sample": self.fit_to_sample,
            "current_sample_idx": self.current_sample_idx,
            "grid_view_widgets": {"columns": self.grid_columns, "rows": self.grid_rows},
            "view_widgets_config": self.view_widgets_config,
            "classification_buttons": self.btns_config,
        })
        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(self.points):
            if point.is_classified:
                points_config[pnt_idx] = {"btn_id": point.btn_id,}
        data["points"] = points_config

        with open(file_out, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)


