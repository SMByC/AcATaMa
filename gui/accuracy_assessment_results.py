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
from __future__ import division

import csv
import os
import copy

from AcATaMa.core.dockwidget import get_file_path_of_layer


def rf(fv, r=4):
    """
    Round float
    """
    return round(fv, r)


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
    html += "<p style='font-size:2px'><br/></p>"
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
    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=t) for t in accu_asse.error_matrix[idx_row]])
        html += '''
            <td>{total_row}</td>
            <td>{u_accuracy}</td>
            <td>{total_class_area}</td>
            <td>{wi}</td>
            </tr>
            '''.format(total_row=sum(accu_asse.error_matrix[idx_row]),
                       u_accuracy=rf(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))
                           if sum(accu_asse.error_matrix[idx_row]) > 0 else "-",
                       total_class_area=accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_ha,
                       wi=rf(accu_asse.thematic_pixels_count[value] /
                           sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])))
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
            '''.format(p_accuracy=rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-")
    html += '''
        <td></td>
        <td>{u_p_accuracy}</td>
        '''.format(u_p_accuracy=rf(sum([col[idx_col] for idx_col, col in enumerate(zip(*accu_asse.error_matrix))]) /
                                      sum([sum(r) for r in accu_asse.error_matrix])))
    html += '''
        <td></td>
        <td></td>
        </tr>
        </tbody>
        </table>
        '''

    ###########################################################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>2) Error matrix of estimated area proportion:</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values (User)</th>
            <td class="empty"></td>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        <th>Wi</th>
        </tr>
        '''
    error_matrix_area_prop = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
             sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
        for idx_col, value in enumerate(row):
            error_matrix_area_prop[idx_row][idx_col] = (value / sum(row)) * wi if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t, 5)) if t > 0 else "-") for t in error_matrix_area_prop[idx_row]])
        html += '''
            <td>{wi}</td>
            </tr>
            '''.format(wi=rf(sum(error_matrix_area_prop[idx_row])) if sum(error_matrix_area_prop[idx_row]) > 0 else "-")
    html += '''    
        <tr>
        <td class="empty"></td>
          <th>total</th>
        '''
    html += "".join(['''
                <td>{total_col}</td>
                '''.format(total_col=rf(sum(t), 5)) for t in zip(*error_matrix_area_prop)])
    html += '''
        <td></td>
        </tr>
        </tbody>
        </table>
        '''

    ###########################################################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>3) Quadratic error matrix of estimated area proportion:</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values (User)</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        </tr>
        '''
    quadratic_error_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
             sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
        for idx_col, value in enumerate(row):
            quadratic_error_matrix[idx_row][idx_col] = \
                (wi**2*((value/sum(row))*(1-(value/sum(row)))/(sum(row)-1))) if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t, 5)) if t > 0 else "-") for t in quadratic_error_matrix[idx_row]])
    html += '''
        </tbody>
        </table>
        '''

    ###########################################################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>4) Overall matrix accuracy:</h3>"
    ###################################
    html += "<h4>User's accuracy matrix:</h4>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values (User)</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        </tr>
        '''
    user_accuracy_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        for idx_col, value in enumerate(row):
            user_accuracy_matrix[idx_row][idx_col] = \
                value/sum(row) if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t, 5)) if t > 0 else "-") for t in user_accuracy_matrix[idx_row]])
    html += '''
        </tbody>
        </table>
        '''
    ###################################
    html += "<h4>Producer's accuracy matrix:</h4>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values (User)</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        </tr>
        '''
    producer_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
    for idx_col, col in enumerate(zip(*error_matrix_area_prop)):
        for idx_row, value in enumerate(col):
            producer_accuracy_matrix[idx_row][idx_col] = value/sum(col) if sum(col) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes (Producer)</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t, 5)) if t > 0 else "-") for t in producer_accuracy_matrix[idx_row]])
    html += '''
        </tbody>
        </table>
        '''


    html += '''
        </body>
        '''

    return html


def export_to_csv(accu_asse, file_out):
    csv_rows = []
    csv_rows.append(["Classification accuracy assessment results"])
    # csv_rows.append([])
    # csv_rows.append(["Thematic raster:", os.path.basename(accu_asse.ThematicR.file_path)])
    # csv_rows.append(["Sampling file:", os.path.basename(get_file_path_of_layer(accu_asse.classification.sampling_layer))])
    # total_classified = sum(sample.is_classified for sample in accu_asse.classification.points)
    # csv_rows.append(["Classification status:", "{}/{} samples classified".format(total_classified, len(accu_asse.classification.points))])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["1) Error matrix (confusion matrix):"])
    csv_rows.append(["", "", "Classified values (User)"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)]) if str(i) in accu_asse.labels else i
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels + ["Total", "U. Accuracy", "Total class area (ha)", "Wi"])

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes (Producer)")
        else:
            r.append("")
        r.append(value)
        r += accu_asse.error_matrix[idx_row]
        r.append(sum(accu_asse.error_matrix[idx_row]))
        r.append(rf(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))
                 if sum(accu_asse.error_matrix[idx_row]) > 0 else "-")
        r.append(accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_ha)
        r.append(rf(accu_asse.thematic_pixels_count[value] /
                 sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])))
        csv_rows.append(r)

    csv_rows.append(["", "total"] + [sum(t) for t in zip(*accu_asse.error_matrix)] + [sum([sum(r) for r in accu_asse.error_matrix])] +
                    [""] + [sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_ha])
    csv_rows.append(["", "P. Accuracy"] +
                    [rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-" for idx_col, col in enumerate(zip(*accu_asse.error_matrix))] +
                    [""] + [rf(sum([col[idx_col] for idx_col, col in enumerate(zip(*accu_asse.error_matrix))]) /
                            sum([sum(r) for r in accu_asse.error_matrix]))])


    with open(file_out, 'wb') as csvfile:
        csv_w = csv.writer(csvfile)
        csv_w.writerows(csv_rows)

