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
from __future__ import division

import csv
import os
import copy

from qgis.core import QGis

from AcATaMa.utils.qgis_utils import get_file_path_of_layer


def rf(fv, r=5):
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
    html += "<p><strong>Thematic raster:</strong> {}</p>".format(os.path.basename((accu_asse.ThematicR.file_path).encode('utf-8')))
    html += "<p><strong>Sampling file:</strong> {}</p>".format(
        os.path.basename((get_file_path_of_layer(accu_asse.classification.sampling_layer)).encode('utf-8')))
    html += "<p><strong>Classification status:</strong> {}/{} samples classified</p>".format(
        accu_asse.classification.total_classified, accu_asse.classification.num_points)

    # warning block if the thematic has a geographic units
    if accu_asse.base_area_unit == QGis.Degrees:
        html += "<p style='color:black;background-color:#ffc53a;white-space:pre;padding:4px'><strong>Warning!</strong><br/>" \
                "The thematic raster has a geographic coordinate system, therefore all area values are not accurate.<br/>" \
                "For fix that use the UTM coordinate system.</p>"

    # warning block for samples outside the thematic raster area or inside the no data values
    if accu_asse.samples_outside_the_thematic:
        html += "<p style='color:black;background-color:#ffc53a;white-space:pre;padding:4px'><strong>Warning!</strong><br/>" \
                "There are {} samples classified that are outside the thematic raster area or inside the no data values:<br/>".format(
            len(accu_asse.samples_outside_the_thematic))
        for idx, sample in enumerate(accu_asse.samples_outside_the_thematic):
            html += "    {}) Sample ID: {}, Coordinate: {},{}<br/>".format(idx+1, sample.shape_id, int(sample.QgsPnt.x()), int(sample.QgsPnt.y()))
        html += "These samples will be ignored for accuracy assessment results.</p>"

    ###########################################################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>1) Error matrix (confusion matrix):</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values</th>
            <td class="empty"></td>
            <td class="empty"></td>
            <td class="empty"></td>
            <td class="empty"></td>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += '''
        <th>Total</th>
        <th>User accuracy</th>
        <th>Total class area ({area_unit})</th>
        <th>Wi</th>
        </tr>
        '''.format(area_unit=accu_asse.pixel_area_unit)
    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes</th>
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
                       total_class_area=rf(accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_value),
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
        '''.format(total_classes_area=rf(sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) *
                                         accu_asse.pixel_area_value))
    html += '''
        <td></td>
        </tr>
        <tr>
        <td class="empty"></td>
          <th>Producer accuracy</th>
        '''
    for idx_col, col in enumerate(zip(*accu_asse.error_matrix)):
        html += '''
            <td>{p_accuracy}</td>
            '''.format(p_accuracy=rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-")
    html += '''
        <td></td>
        <td>{u_p_accuracy}</td>
        '''.format(u_p_accuracy=rf(sum([col[idx_col] for idx_col, col in enumerate(zip(*accu_asse.error_matrix))]) /
                                      sum([sum(r) for r in accu_asse.error_matrix])) if sum([sum(r) for r in accu_asse.error_matrix]) != 0 else "-")
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
         <th colspan="{table_size}">Classified values</th>
            <td class="empty"></td>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
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
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t)) if t > 0 else "-") for t in error_matrix_area_prop[idx_row]])
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
                '''.format(total_col=rf(sum(t))) for t in zip(*error_matrix_area_prop)])
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
         <th colspan="{table_size}">Classified values</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += "</tr>"
    
    quadratic_error_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
             sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
        for idx_col, value in enumerate(row):
            quadratic_error_matrix[idx_row][idx_col] = \
                (wi**2*((value/sum(row))*(1-(value/sum(row)))/(sum(row)-1))) if sum(row) > 1 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t)) if t > 0 else "-") for t in quadratic_error_matrix[idx_row]])
        html += "</tr>"
    html += '''    
        <tr>
        <td class="empty"></td>
          <th>total</th>
        '''
    html += "".join(['''
                    <td>{total_col}</td>
                    '''.format(total_col=rf(sum(t)**0.5)) for t in zip(*quadratic_error_matrix)])
    html += '''
        </tr>
        </tbody>
        </table>
        '''

    ###########################################################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>4) Accuracy matrices:</h3>"
    ###################################
    html += "<h4>User's accuracy matrix of estimated area proportion:</h4>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += "</tr>"
    
    user_accuracy_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        for idx_col, value in enumerate(row):
            user_accuracy_matrix[idx_row][idx_col] = \
                value/sum(row) if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t)) if t > 0 else "-") for t in user_accuracy_matrix[idx_row]])
        html += "</tr>"
    html += '''
        </tbody>
        </table>
        '''
    ###################################
    html += "<h4>Producer's accuracy matrix of estimated area proportion:</h4>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Classified values</th>
        </tr>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    html += "".join([
        "<th >"+str(i)+"</th>" for i in labels])
    html += "</tr>"
    
    producer_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
    for idx_col, col in enumerate(zip(*error_matrix_area_prop)):
        for idx_row, value in enumerate(col):
            producer_accuracy_matrix[idx_row][idx_col] = value/sum(col) if sum(col) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        if idx_row == 0:
            html += '''
                <th  class="th-rows" rowspan="{table_size}">Thematic raster<br />classes</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="field-values">{table_field}</td>
            '''.format(table_field=(rf(t)) if t > 0 else "-") for t in producer_accuracy_matrix[idx_row]])
        html += "</tr>"
        
    html += '''
        </tbody>
        </table>
        '''
    ###################################
    html += "<h4>Overall Accuracy: </h4>"
    overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(error_matrix_area_prop)])
    html += '''
            <table>
            <tbody>
            <tr>
            <td>{}</td>
            </tr>'''.format(rf(overall_accuracy))
    html += '''
            </tbody>
            </table>
            '''

    ###################################
    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>5) Class area adjusted table:</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    headers = ["Area ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Error", "Lower limit", "Upper limit"]
    html += "".join([
        "<th >" + str(h) + "</th>" for h in headers])
    html += "</tr>"

    total_area = 0

    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"

        html += "<th >{} ({})</th>".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-")
        # area
        area = sum(zip(*error_matrix_area_prop)[idx_row]) * \
               sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_value
        html += '''<td>{area}</th>'''.format(area=rf(area))
        total_area += area
        # error
        error = (sum(zip(*quadratic_error_matrix)[idx_row])**0.5) * \
                sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_value
        html += '''<td>{error}</th>'''.format(error=rf(error))
        # lower limit
        html += '''<td>{lower_limit}</th>'''.format(lower_limit=rf(area - accu_asse.z_score * error))
        # upper limit
        html += '''<td>{upper_limit}</th>'''.format(upper_limit=rf(area + accu_asse.z_score * error))
        html += "</tr>"

    html += '''    
        <tr>
          <th>total</th>
        '''
    html += '''<td>{total_area}</th>'''.format(total_area=rf(total_area))
    html += '''
        <td class="empty"></td>
        <td class="empty"></td>
        <td class="empty"></td>
        </tr>'''

    html += '''
        </tbody>
        </table>
        '''

    html += '''
        </body>
        '''

    return html


def export_to_csv(accu_asse, file_out, csv_separator, csv_decimal_separator):
    csv_rows = []
    csv_rows.append(["Classification accuracy assessment results"])
    csv_rows.append([])
    csv_rows.append(["Thematic raster:"])
    csv_rows.append([os.path.basename((accu_asse.ThematicR.file_path).encode('utf-8'))])
    csv_rows.append([])
    csv_rows.append(["Sampling file:"])
    csv_rows.append([os.path.basename((get_file_path_of_layer(accu_asse.classification.sampling_layer)).encode('utf-8'))])
    csv_rows.append([])
    csv_rows.append(["Classification status:"])
    csv_rows.append(["{}/{} samples classified".format(accu_asse.classification.total_classified,
                                                       accu_asse.classification.num_points)])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["1) Error matrix (confusion matrix):"])
    csv_rows.append(["", "", "Classified values"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels + ["Total", "User accuracy",
                                         "Total class area ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Wi"])

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes")
        else:
            r.append("")
        r.append(value)
        r += accu_asse.error_matrix[idx_row]
        r.append(sum(accu_asse.error_matrix[idx_row]))
        r.append(rf(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))
                 if sum(accu_asse.error_matrix[idx_row]) > 0 else "-")
        r.append(rf(accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_value))
        r.append(rf(accu_asse.thematic_pixels_count[value] /
                 sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])))
        csv_rows.append(r)

    csv_rows.append(["", "total"] + [sum(t) for t in zip(*accu_asse.error_matrix)] + [sum([sum(r) for r in accu_asse.error_matrix])] +
                    [""] + [sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_value])
    csv_rows.append(["", "Producer accuracy"] +
                    [rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-" for idx_col, col in enumerate(zip(*accu_asse.error_matrix))] +
                    [""] + [rf(sum([col[idx_col] for idx_col, col in enumerate(zip(*accu_asse.error_matrix))]) /
                            sum([sum(r) for r in accu_asse.error_matrix])) if sum([sum(r) for r in accu_asse.error_matrix]) != 0 else "-"])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["2) Error matrix of estimated area proportion:"])
    csv_rows.append(["", "", "Classified values"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels + ["Wi"])

    error_matrix_area_prop = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
             sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
        for idx_col, value in enumerate(row):
            error_matrix_area_prop[idx_row][idx_col] = (value / sum(row)) * wi if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes")
        else:
            r.append("")
        r.append(value)
        r += [rf(t) if t > 0 else "-" for t in error_matrix_area_prop[idx_row]]
        r.append(rf(sum(error_matrix_area_prop[idx_row])) if sum(error_matrix_area_prop[idx_row]) > 0 else "-")
        csv_rows.append(r)

    csv_rows.append(["", "total"] + [rf(sum(t)) for t in zip(*error_matrix_area_prop)])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["3) Quadratic error matrix of estimated area proportion:"])
    csv_rows.append(["", "", "Classified values"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels)

    quadratic_error_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
             sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
        for idx_col, value in enumerate(row):
            quadratic_error_matrix[idx_row][idx_col] = \
                (wi ** 2 * ((value / sum(row)) * (1 - (value / sum(row))) / (sum(row) - 1))) if sum(row) > 1 else 0

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes")
        else:
            r.append("")
        r.append(value)
        r += [rf(t) if t > 0 else "-" for t in quadratic_error_matrix[idx_row]]
        csv_rows.append(r)

    csv_rows.append(["", "total"] + [rf(sum(t)**0.5) for t in zip(*quadratic_error_matrix)])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["4) Accuracy matrices:"])
    csv_rows.append([])
    csv_rows.append(["User's accuracy matrix of estimated area proportion:"])
    csv_rows.append(["", "", "Classified values"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels)

    user_accuracy_matrix = copy.deepcopy(accu_asse.error_matrix)
    for idx_row, row in enumerate(accu_asse.error_matrix):
        for idx_col, value in enumerate(row):
            user_accuracy_matrix[idx_row][idx_col] = \
                value / sum(row) if sum(row) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes")
        else:
            r.append("")
        r.append(value)
        r += [rf(t) if t > 0 else "-" for t in user_accuracy_matrix[idx_row]]
        csv_rows.append(r)

    csv_rows.append([])
    csv_rows.append(["Producer's accuracy matrix of estimated area proportion:"])
    csv_rows.append(["", "", "Classified values"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels)

    producer_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
    for idx_col, col in enumerate(zip(*error_matrix_area_prop)):
        for idx_row, value in enumerate(col):
            producer_accuracy_matrix[idx_row][idx_col] = value / sum(col) if sum(col) > 0 else 0

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic raster classes")
        else:
            r.append("")
        r.append(value)
        r += [rf(t) if t > 0 else "-" for t in producer_accuracy_matrix[idx_row]]
        csv_rows.append(r)

    csv_rows.append([])
    csv_rows.append(["Overall Accuracy:"])
    overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(error_matrix_area_prop)])
    csv_rows.append([rf(overall_accuracy)])

    ###########################################################################
    csv_rows.append([])
    csv_rows.append(["5) Class area adjusted table:"])
    csv_rows.append(["", "Area ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Error", "Lower limit", "Upper limit"])

    total_area = 0

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        r.append("{} ({})".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-"))

        # area
        area = sum(zip(*error_matrix_area_prop)[idx_row]) * \
               sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_value
        r.append(rf(area))
        total_area += area
        # error
        error = (sum(zip(*quadratic_error_matrix)[idx_row]) ** 0.5) * \
                sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values]) * accu_asse.pixel_area_value
        r.append(rf(error))
        # lower limit
        r.append(rf(area - accu_asse.z_score * error))
        # upper limit
        r.append(rf(area + accu_asse.z_score * error))
        csv_rows.append(r)

    csv_rows.append(["total"] + [rf(total_area)])

    # write CSV file
    with open(file_out, 'wb') as csvfile:
        csv_w = csv.writer(csvfile, delimiter=str(csv_separator))
        # replace with the user define decimal separator
        if csv_decimal_separator != ".":
            for idx, row in enumerate(csv_rows):
                csv_rows[idx] = [str(item).replace('.', csv_decimal_separator) if isinstance(item, float) else item for item in row]

        csv_w.writerows(csv_rows)

