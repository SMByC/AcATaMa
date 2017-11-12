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

from AcATaMa.core.dockwidget import get_file_path_of_layer


def get_html(accu_asse):
    html = '''
        <head>
        <style type="text/css">
        table {
          table-layout: fixed;
          white-space: normal!important;
          background: #ffffff;
        }
        th {
          word-wrap: break-word;
          padding: 2px;
          background: #efefef;
          valign: middle;
        }
        td {
          word-wrap: break-word;
          padding: 2px;
          background: #efefef;
        }
        .field-values {
          background: #dddddd;
        }
        .th-rows {
          max-width: 120px;
        }
        .empty {
          background: #f9f9f9;
        }
        </style>
        </head>
        <body>
        '''
    html += "<h2>Classification accuracy assessment results</h2>"
    html += "<p><strong>Thematic raster:</strong> {}</p>".format(os.path.basename(accu_asse.ThematicR.file_path))
    html += "<p><strong>Sampling file:</strong> {}</p>".format(os.path.basename(get_file_path_of_layer(accu_asse.classification.sampling_layer)))
    total_classified = sum(sample.is_classified for sample in accu_asse.classification.points)
    html += "<p><strong>Classification status:</strong> {}/{} samples classified</p>".format(total_classified, len(accu_asse.classification.points))

    ###########################################################################
    html += "<h3>1) Error matrix (confusion matrix):</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values (User)</th>
            <td class="empty"></td>
            <td class="empty"></td>
            <td class="empty"></td>
            <td class="empty"></td>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    print accu_asse.labels
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        <th>Total</th>
        <th>U. Accuracy</th>
        <th>Total class area (ha)</th>
        <th>Wi</th>
        </tr>
        '''
    for idx_table, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_table == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=t) for t in accu_asse.error_matrix[idx_table]])
        html += '''
            <td>{total_row}</td>
            <td>{u_accuracy}</td>
            <td>{total_class_area}</td>
            <td>{wi}</td>
            </tr>
            '''.format(total_row=sum(accu_asse.error_matrix[idx_table]),
                       u_accuracy=round(accu_asse.error_matrix[idx_table][idx_table]/float(sum(accu_asse.error_matrix[idx_table])), 4)
                           if sum(accu_asse.error_matrix[idx_table]) > 0 else "nan",
                       total_class_area=accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_ha,
                       wi=round(accu_asse.thematic_pixels_count[value] /
                           float(sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])), 4))
    html += '''    
        <tr>
        <td class="empty"></td>
          <th>total</th>
        '''
    html += "".join(['''
                <td>{total_col}</td>
                '''.format(total_col=sum(t)) for t in zip(*accu_asse.error_matrix)])
    html += '''
        <td>{total_total}</td>
        '''.format(total_total=sum([sum(r) for r in accu_asse.error_matrix]))
    html += '''
        <td></td>
        '''
    html += '''
        <td>{total_classes_area}</td>
        '''.format(total_classes_area=sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_ha)
    html += '''
        <td></td>
        </tr>
        <tr>
        <td class="empty"></td>
          <th>P. Accuracy</th>
        '''
    for idx_col, col in enumerate(zip(*accu_asse.error_matrix)):
        html += '''
            <td>{p_accuracy}</td>
            '''.format(p_accuracy=round(col[idx_col] / float(sum(col)), 4) if sum(col) > 0 else "nan")
    html += '''
        <td></td>
        <td>{u_p_accuracy}</td>
        '''.format(u_p_accuracy=round(sum([col[idx_col] for idx_col, col in enumerate(zip(*accu_asse.error_matrix))]) /
                                      float(sum([sum(r) for r in accu_asse.error_matrix])), 4))
    html += '''
        <td></td>
        <td></td>
        </tr>
        </tbody>
        </table>
        </body>
        '''

    return html