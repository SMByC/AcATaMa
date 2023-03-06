# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2023 by Xavier C. Llano, SMByC
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
"""
import csv
import os
import copy
import numpy as np

from qgis.core import QgsUnitTypes

from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import error_handler


def rf(fv, r=5):
    if np.isnan(fv):
        return "-"
    return round(fv, r)


@error_handler
def get_html(accu_asse):
    ###########################################################################
    # #### preprocess common variables

    total_samples = sum([sum(r) for r in accu_asse.error_matrix])
    total_pixels_classes = sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
    sum_total_class_area = total_pixels_classes * accu_asse.pixel_area_value

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:

        error_matrix_area_prop = copy.deepcopy(accu_asse.error_matrix)
        for idx_row, row in enumerate(accu_asse.error_matrix):
            wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
                 total_pixels_classes
            for idx_col, value in enumerate(row):
                error_matrix_area_prop[idx_row][idx_col] = (value / sum(row)) * wi if sum(row) > 0 else 0

        quadratic_error_matrix = copy.deepcopy(accu_asse.error_matrix)
        for idx_row, row in enumerate(accu_asse.error_matrix):
            wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
                 total_pixels_classes
            for idx_col, value in enumerate(row):
                quadratic_error_matrix[idx_row][idx_col] = \
                    (wi ** 2 * ((value / sum(row)) * (1 - (value / sum(row))) / (sum(row) - 1))) if sum(row) > 1 else 0

    accuracy_table = error_matrix_area_prop if accu_asse.estimator == 'Stratified estimator' else accu_asse.error_matrix

    ###########################################################################
    # #### html init
    html = '''
        <head>
        
        <style type="text/css">
        table {
          table-layout: fixed;
          white-space: normal!important;
          background: #ffffff;
          margin: 4px;
        }
        th {
          word-wrap: break-word;
          padding: 4px 6px;
          background: #efefef;
          valign: middle;
        }
        td {
          word-wrap: break-word;
          padding: 4px 6px;
          background: #efefef;
        }
        .highlight {
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
    html += "<h2>Analysis - Accuracy assessment results</h2>"
    html += "<p><strong>Thematic map:</strong> {}</p>".format(os.path.basename(accu_asse.thematic_map.file_path))
    html += "<p><strong>Sampling file:</strong> {}</p>".format(
        os.path.basename(get_file_path_of_layer(accu_asse.response_design.sampling_layer)))
    html += "<p><strong>Estimator:</strong> {}</p>".format(accu_asse.estimator)
    html += "<p><strong>Response design state:</strong> {}/{} samples labeled</p>".format(
        accu_asse.response_design.total_labeled, accu_asse.response_design.num_points)

    # warning block if the thematic has a geographic units
    if accu_asse.base_area_unit == QgsUnitTypes.AreaSquareDegrees:
        html += "<p style='color:black;background-color:#ffc53a;white-space:pre;padding:4px'><strong>Warning!</strong><br/>" \
                "The thematic map has a geographic coordinate system, therefore all area values are not accurate.<br/>" \
                "For fix that use the UTM coordinate system.</p>"

    # warning block for samples outside the thematic map area or inside the no data values
    if accu_asse.samples_outside_the_thematic:
        html += "<p style='color:black;background-color:#ffc53a;white-space:pre;padding:4px'><strong>Warning!</strong><br/>" \
                "There are {} samples labeled that are outside the thematic map area or inside the no data values:<br/>".format(
            len(accu_asse.samples_outside_the_thematic))
        for idx, sample in enumerate(accu_asse.samples_outside_the_thematic):
            html += "    {}) Sample ID: {}, Coordinate: {},{}<br/>".format(idx+1, sample.sample_id, int(sample.QgsPnt.x()), int(sample.QgsPnt.y()))
        html += "These samples will be ignored for accuracy assessment results.</p>"

    ###########################################################################
    # #### 1) Error matrix

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>1) Error matrix:</h3>"
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        <td class="empty"></td>
         <th colspan="{table_size}">Validation</th>
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
                <th  class="th-rows" rowspan="{table_size}">Thematic map<br />classes</th>
                '''.format(table_size=len(accu_asse.values))

        html += "<th>{value}</th>".format(value=value)
        html += "".join(['''
            <td class="highlight">{table_field}</td>
            '''.format(table_field=t) for t in accu_asse.error_matrix[idx_row]])
        html += '''
            <td>{total_row}</td>
            <td>{u_accuracy}</td>
            <td>{total_class_area}</td>
            <td>{wi}</td>
            </tr>
            '''.format(total_row=sum(accu_asse.error_matrix[idx_row]),
                       u_accuracy=rf(accuracy_table[idx_row][idx_row]/sum(accuracy_table[idx_row]))
                       if sum(accuracy_table[idx_row]) > 0 else "-",
                       total_class_area=rf(accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_value),
                       wi=rf(accu_asse.thematic_pixels_count[value] / total_pixels_classes))
    html += '''    
        <tr>
        <td class="empty"></td>
          <th>Total</th>
        '''
    html += "".join(['''
                <td>{total_col}</td>
                '''.format(total_col=sum(t)) for t in zip(*accu_asse.error_matrix)])
    html += '''
        <td>{total_total}</td>
        '''.format(total_total=total_samples)
    html += '''
        <td class="empty"></td>
        '''
    html += '''
        <td>{total_classes_area}</td>
        '''.format(total_classes_area=rf(sum_total_class_area))
    html += '''
        <td class="empty"></td>
        </tr>
        <tr>
        <td class="empty"></td>
          <th>Producer accuracy</th>
        '''
    for idx_col, col in enumerate(zip(*accuracy_table)):
        html += '''
            <td>{p_accuracy}</td>
            '''.format(p_accuracy=rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-")
    html += '''
        <td class="empty"></td>
        <td class="empty"></td>
        '''
    html += '''
        <td class="empty"></td>
        <td class="empty"></td>
        </tr>
        </tbody>
        </table>
        '''

    ###########################################################################
    # #### 2) Accuracy

    if accu_asse.estimator in ['Simple/systematic estimator']:
        # overall
        overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(accu_asse.error_matrix)]) / total_samples
        standard_deviation = (overall_accuracy*(1-overall_accuracy)/(total_samples-1))**0.5
    if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
        # overall
        overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(error_matrix_area_prop)])
        try:
            overall_variance = sum([((accu_asse.thematic_pixels_count[value]/total_pixels_classes)**2) *
                                    (accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row])) *
                                    (1-(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))) /
                                    (sum(accu_asse.error_matrix[idx_row])-1) for idx_row, value in enumerate(accu_asse.values)])
        except ZeroDivisionError:
            overall_variance = np.NaN
        standard_deviation = overall_variance ** 0.5

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>2) Accuracy:</h3>"

    html += "<h4>Overall:</h4>"
    # Overall Accuracy
    html += '''
            <table>
            <tbody>
            <tr>
            <td><strong>Overall Accuracy</strong></td>
            <td><strong>Standard deviation</strong></td>
            </tr>
            <tr>
            <td class="highlight">{overall_accuracy}</td>
            <td>{standard_deviation}</td>
            </tr>'''.format(overall_accuracy=rf(overall_accuracy), standard_deviation=rf(standard_deviation))
    html += '''
            </tbody>
            </table>
            '''
    # user's accuracy
    html += "<h4>User:</h4>"
    html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            '''.format(table_size=len(accu_asse.values))
    headers = ["User's accuracy", "Standard deviation"]
    html += "".join([
        "<th>" + str(h) + "</th>" for h in headers])
    html += "</tr>"
    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        html += "<th >{} ({})</th>".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-")
        # accuracy
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                accuracy = accuracy_table[idx_row][idx_row] / sum(accuracy_table[idx_row])
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                accuracy = error_matrix_area_prop[idx_row][idx_row] / sum(error_matrix_area_prop[idx_row])
        except ZeroDivisionError:
            accuracy = np.NaN
        html += '''<td class="highlight">{}</th>'''.format(rf(accuracy))
        # standard error
        try:
            html += '''<td>{}</th>'''.format(rf((accuracy*(1-accuracy)/(sum(accu_asse.error_matrix[idx_row])-1))**0.5))
        except ZeroDivisionError:
            html += '''<td>{}</th>'''.format("-")
        html += "</tr>"
    html += '''
            </tbody>
            </table>
            '''
    # producer's accuracy
    html += "<h4>Producer:</h4>"
    html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            '''.format(table_size=len(accu_asse.values))
    headers = ["Producer's accuracy", "Standard deviation"]
    html += "".join([
        "<th>" + str(h) + "</th>" for h in headers])
    html += "</tr>"
    for idx_row, value in enumerate(accu_asse.values):
        html += "<tr>"
        html += "<th >{} ({})</th>".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-")
        # accuracy
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                accuracy = accuracy_table[idx_row][idx_row] / sum(list(zip(*accuracy_table))[idx_row])
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                accuracy = error_matrix_area_prop[idx_row][idx_row] / sum(list(zip(*error_matrix_area_prop))[idx_row])
        except ZeroDivisionError:
            accuracy = np.NaN
        html += '''<td class="highlight">{}</th>'''.format(rf(accuracy))
        # standard error
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                producer_standard_error = (accuracy*(1-accuracy)/(sum(list(zip(*accu_asse.error_matrix))[idx_row])-1))**0.5
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                u_accuracy = accuracy_table[idx_row][idx_row] / sum(accuracy_table[idx_row])
                producer_standard_error = \
                    (1/(sum([n*row[idx_row]/total_row for total_row, row, n in
                             zip([sum(r) for r in accu_asse.error_matrix], accu_asse.error_matrix,
                                 [accu_asse.thematic_pixels_count[v] for v in accu_asse.values])])**2) *
                     sum([n**2*(1-accuracy)**2*u_accuracy*(1-u_accuracy)/(total_row-1) if idx == idx_row else
                          accuracy**2*n**2*row[idx_row]/total_row*(1-row[idx_row]/sum(list(zip(*accu_asse.error_matrix))[idx_row]))/(total_row-1)
                          for idx, total_row, row, n in zip(range(len(accu_asse.error_matrix)),
                                                            [sum(r) for r in accu_asse.error_matrix], accu_asse.error_matrix,
                                                            [accu_asse.thematic_pixels_count[v] for v in accu_asse.values])]))**0.5
        except ZeroDivisionError:
            producer_standard_error = np.NaN
        html += '''<td>{}</th>'''.format(rf(producer_standard_error))
        html += "</tr>"
    html += '''
            </tbody>
            </table>
            '''

    # #### 2b) Accuracy matrix of estimated area proportion

    if accu_asse.estimator == 'Stratified estimator':
        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>2b) Accuracy matrix of estimated area proportion:</h3>"
        ###################################
        html += "<h4>User:</h4>"
        html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            <td class="empty"></td>
             <th colspan="{table_size}">Validation</th>
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

        user_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
        for idx_row, row in enumerate(error_matrix_area_prop):
            for idx_col, value in enumerate(row):
                user_accuracy_matrix[idx_row][idx_col] = value/sum(row) if sum(row) > 0 else 0

        for idx_row, value in enumerate(accu_asse.values):
            html += "<tr>"
            if idx_row == 0:
                html += '''
                    <th  class="th-rows" rowspan="{table_size}">Thematic map<br />classes</th>
                    '''.format(table_size=len(accu_asse.values))

            html += "<th>{value}</th>".format(value=value)
            html += "".join(['''
                <td class="highlight">{table_field}</td>
                '''.format(table_field=(rf(t)) if t > 0 else "-") for t in user_accuracy_matrix[idx_row]])
            html += "</tr>"
        html += '''
            </tbody>
            </table>
            '''
        ###################################
        html += "<h4>Producer:</h4>"
        html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            <td class="empty"></td>
             <th colspan="{table_size}">Validation</th>
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
                    <th  class="th-rows" rowspan="{table_size}">Thematic map<br />classes</th>
                    '''.format(table_size=len(accu_asse.values))

            html += "<th>{value}</th>".format(value=value)
            html += "".join(['''
                <td class="highlight">{table_field}</td>
                '''.format(table_field=(rf(t)) if t > 0 else "-") for t in producer_accuracy_matrix[idx_row]])
            html += "</tr>"

        html += '''
            </tbody>
            </table>
            '''

    ###########################################################################
    # #### 3) Error matrix of estimated area proportion

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:
        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>3) Error matrix of estimated area proportion:</h3>"
        html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            <td class="empty"></td>
             <th colspan="{table_size}">Validation</th>
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
        for idx_row, value in enumerate(accu_asse.values):
            html += "<tr>"
            if idx_row == 0:
                html += '''
                    <th  class="th-rows" rowspan="{table_size}">Thematic map<br />classes</th>
                    '''.format(table_size=len(accu_asse.values))

            html += "<th>{value}</th>".format(value=value)
            html += "".join(['''
                <td class="highlight">{table_field}</td>
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
    # #### 4) Quadratic error matrix of estimated area proportion

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:
        html += "<p style='font-size:2px'><br/></p>"
        html += "<h3>4) Quadratic error matrix of estimated area proportion:</h3>"
        html += '''
            <table>
            <tbody>
            <tr>
            <td class="empty"></td>
            <td class="empty"></td>
             <th colspan="{table_size}">Validation</th>
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

        for idx_row, value in enumerate(accu_asse.values):
            html += "<tr>"
            if idx_row == 0:
                html += '''
                    <th  class="th-rows" rowspan="{table_size}">Thematic map<br />classes</th>
                    '''.format(table_size=len(accu_asse.values))

            html += "<th>{value}</th>".format(value=value)
            html += "".join(['''
                <td class="highlight">{table_field}</td>
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
    # #### 3/5) Class area adjusted

    html += "<p style='font-size:2px'><br/></p>"
    html += "<h3>{}) Class area adjusted:</h3>".format("3" if accu_asse.estimator == 'Simple/systematic estimator' else "5")
    html += '''
        <table>
        <tbody>
        <tr>
        <td class="empty"></td>
        '''.format(table_size=len(accu_asse.values))
    headers = ["Area adjusted ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Error", "Lower limit", "Upper limit"]
    html += "".join([
        "<th >" + str(h) + "</th>" for h in headers])
    html += "</tr>"

    total_area = 0

    # the error for post-stratified
    if accu_asse.estimator == 'Simple/systematic post-stratified estimator':
        std_dev_table = [[(1-i/total_row)**2*i/(total_row-1) if total_row not in [0, 1] else np.NaN
                          for i in row] for total_row, row in
                         zip([sum(r) for r in accu_asse.error_matrix], accu_asse.error_matrix)]
        wi = [accu_asse.thematic_pixels_count[value]/total_pixels_classes
              for value in accu_asse.values]
        variance = [((1-total_samples/total_pixels_classes)/total_samples)*sum([w*s for w,s in zip(wi, std_dev_col)]) +
                    (1/(total_samples**2))*sum([(1-w)*s for w,s in zip(wi, std_dev_col)])
                    for std_dev_col in zip(*std_dev_table)]
        _error = [sum_total_class_area*v**0.5 for v in variance]

    for idx_row, value in enumerate(accu_asse.values):
        if accu_asse.estimator == 'Simple/systematic estimator':
            p_k = sum(list(zip(*accu_asse.error_matrix))[idx_row])/total_samples
            area = p_k * sum_total_class_area
            v_p_k = ((p_k)*(1-p_k)/total_samples)*(total_pixels_classes-total_samples)/(total_pixels_classes-1)
            error = (v_p_k**0.5) * sum_total_class_area
        if accu_asse.estimator == 'Simple/systematic post-stratified estimator':
            area = sum(list(zip(*error_matrix_area_prop))[idx_row]) * sum_total_class_area
            error = _error[idx_row]
        if accu_asse.estimator == 'Stratified estimator':
            area = sum(list(zip(*error_matrix_area_prop))[idx_row]) * sum_total_class_area
            error = (sum(list(zip(*quadratic_error_matrix))[idx_row])**0.5) * sum_total_class_area

        html += "<tr>"
        html += "<th >{} ({})</th>".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-")
        # area
        html += '''<td>{area}</th>'''.format(area=rf(area))
        total_area += area
        # error
        html += '''<td>{error}</th>'''.format(error=rf(error))
        # lower limit
        lower_limit = area - accu_asse.z_score * error
        lower_limit = 0 if lower_limit < 0 else lower_limit
        html += '''<td>{lower_limit}</th>'''.format(lower_limit=rf(lower_limit))
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


@error_handler
def export_to_csv(accu_asse, file_out, csv_separator, csv_decimal_separator):
    csv_rows = []
    csv_rows.append(["Analysis - Accuracy assessment results"])
    csv_rows.append([])
    csv_rows.append(["Thematic map:"])
    csv_rows.append([os.path.basename(accu_asse.thematic_map.file_path)])
    csv_rows.append([])
    csv_rows.append(["Sampling file:"])
    csv_rows.append([os.path.basename(get_file_path_of_layer(accu_asse.response_design.sampling_layer))])
    csv_rows.append([])
    csv_rows.append(["Estimator:"])
    csv_rows.append([accu_asse.estimator])
    csv_rows.append([])
    csv_rows.append(["Response design state:"])
    csv_rows.append(["{}/{} samples labeled".format(accu_asse.response_design.total_labeled,
                                                    accu_asse.response_design.num_points)])

    ###########################################################################
    # #### preprocess common variables

    total_samples = sum([sum(r) for r in accu_asse.error_matrix])
    total_pixels_classes = sum([accu_asse.thematic_pixels_count[v] for v in accu_asse.values])
    sum_total_class_area = total_pixels_classes * accu_asse.pixel_area_value

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:

        error_matrix_area_prop = copy.deepcopy(accu_asse.error_matrix)
        for idx_row, row in enumerate(accu_asse.error_matrix):
            wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
                 total_pixels_classes
            for idx_col, value in enumerate(row):
                error_matrix_area_prop[idx_row][idx_col] = (value / sum(row)) * wi if sum(row) > 0 else 0

        quadratic_error_matrix = copy.deepcopy(accu_asse.error_matrix)
        for idx_row, row in enumerate(accu_asse.error_matrix):
            wi = accu_asse.thematic_pixels_count[accu_asse.values[idx_row]] / \
                 total_pixels_classes
            for idx_col, value in enumerate(row):
                quadratic_error_matrix[idx_row][idx_col] = \
                    (wi ** 2 * ((value / sum(row)) * (1 - (value / sum(row))) / (sum(row) - 1))) if sum(row) > 1 else 0

    accuracy_table = error_matrix_area_prop if accu_asse.estimator == 'Stratified estimator' else accu_asse.error_matrix

    ###########################################################################
    # #### 1) Error matrix

    csv_rows.append([])
    csv_rows.append(["1) Error matrix:"])
    csv_rows.append(["", "", "Validation"])
    labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
              for i in accu_asse.values]
    csv_rows.append(["", ""] + labels + ["Total", "User accuracy",
                                         "Total class area ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Wi"])

    for idx_row, value in enumerate(accu_asse.values):
        r = []
        if idx_row == 0:
            r.append("Thematic map classes")
        else:
            r.append("")
        r.append(value)
        r += accu_asse.error_matrix[idx_row]
        r.append(sum(accu_asse.error_matrix[idx_row]))
        r.append(rf(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))
                 if sum(accu_asse.error_matrix[idx_row]) > 0 else "-")
        r.append(rf(accu_asse.thematic_pixels_count[value] * accu_asse.pixel_area_value))
        r.append(rf(accu_asse.thematic_pixels_count[value] / total_pixels_classes))
        csv_rows.append(r)

    csv_rows.append(["", "total"] + [sum(t) for t in zip(*accu_asse.error_matrix)] + [total_samples] +
                    [""] + [sum_total_class_area])
    csv_rows.append(["", "Producer accuracy"] +
                    [rf(col[idx_col] / sum(col)) if sum(col) > 0 else "-" for idx_col, col in enumerate(zip(*accuracy_table))])

    ###########################################################################
    # #### 2) Accuracy

    csv_rows.append([])
    csv_rows.append(["2) Accuracy:"])

    if accu_asse.estimator in ['Simple/systematic estimator']:
        # overall
        overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(accu_asse.error_matrix)]) / total_samples
        standard_deviation = (overall_accuracy*(1-overall_accuracy)/(total_samples-1))**0.5
    if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
        # overall
        overall_accuracy = sum([row[idx_row] for idx_row, row in enumerate(error_matrix_area_prop)])
        try:
            overall_variance = sum([((accu_asse.thematic_pixels_count[value]/total_pixels_classes)**2) *
                                    (accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row])) *
                                    (1-(accu_asse.error_matrix[idx_row][idx_row]/sum(accu_asse.error_matrix[idx_row]))) /
                                    (sum(accu_asse.error_matrix[idx_row])-1) for idx_row, value in enumerate(accu_asse.values)])
        except ZeroDivisionError:
            overall_variance = np.NaN
        standard_deviation = overall_variance ** 0.5

    csv_rows.append([])
    csv_rows.append(["Overall:"])
    csv_rows.append(["", "Overall Accuracy", "Standard deviation"])
    csv_rows.append(["", rf(overall_accuracy), rf(standard_deviation)])

    csv_rows.append([])
    csv_rows.append(["User:"])
    csv_rows.append(["", "User's Accuracy", "Standard deviation"])
    for idx_row, value in enumerate(accu_asse.values):
        r = []
        r.append("{} ({})".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-"))
        # accuracy
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                accuracy = accuracy_table[idx_row][idx_row] / sum(accuracy_table[idx_row])
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                accuracy = error_matrix_area_prop[idx_row][idx_row] / sum(error_matrix_area_prop[idx_row])
        except ZeroDivisionError:
            accuracy = np.NaN
        r.append(rf(accuracy))
        # standard error
        try:
            r.append(rf((accuracy * (1 - accuracy) / (sum(accu_asse.error_matrix[idx_row]) - 1)) ** 0.5))
        except ZeroDivisionError:
            r.append("-")
        csv_rows.append(r)

    csv_rows.append([])
    csv_rows.append(["Producer:"])
    csv_rows.append(["", "Producer's Accuracy", "Standard deviation"])
    for idx_row, value in enumerate(accu_asse.values):
        r = []
        r.append("{} ({})".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-"))
        # accuracy
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                accuracy = accuracy_table[idx_row][idx_row] / sum(list(zip(*accuracy_table))[idx_row])
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                accuracy = error_matrix_area_prop[idx_row][idx_row] / sum(list(zip(*error_matrix_area_prop))[idx_row])
        except ZeroDivisionError:
            accuracy = np.NaN
        r.append(rf(accuracy))
        # standard error
        try:
            if accu_asse.estimator in ['Simple/systematic estimator']:
                producer_standard_error = (accuracy * (1 - accuracy) / (
                            sum(list(zip(*accu_asse.error_matrix))[idx_row]) - 1)) ** 0.5
            if accu_asse.estimator in ['Stratified estimator', 'Simple/systematic post-stratified estimator']:
                u_accuracy = accuracy_table[idx_row][idx_row] / sum(accuracy_table[idx_row])
                producer_standard_error = \
                    (1 / (sum([n * row[idx_row] / total_row for total_row, row, n in
                               zip([sum(r) for r in accu_asse.error_matrix], accu_asse.error_matrix,
                                   [accu_asse.thematic_pixels_count[v] for v in accu_asse.values])]) ** 2) *
                     sum([n ** 2 * (1 - accuracy) ** 2 * u_accuracy * (1 - u_accuracy) / (
                                 total_row - 1) if idx == idx_row else
                          accuracy ** 2 * n ** 2 * row[idx_row] / total_row * (
                                      1 - row[idx_row] / sum(list(zip(*accu_asse.error_matrix))[idx_row])) / (
                                      total_row - 1)
                          for idx, total_row, row, n in zip(range(len(accu_asse.error_matrix)),
                                                            [sum(r) for r in accu_asse.error_matrix],
                                                            accu_asse.error_matrix,
                                                            [accu_asse.thematic_pixels_count[v] for v in
                                                             accu_asse.values])])) ** 0.5
        except ZeroDivisionError:
            producer_standard_error = np.NaN
        r.append(rf(producer_standard_error))
        csv_rows.append(r)

    # #### 2b) Accuracy matrix of estimated area proportion

    if accu_asse.estimator == 'Stratified estimator':
        csv_rows.append([])
        csv_rows.append(["2b) Accuracy matrix of estimated area proportion:"])
        ###################################
        csv_rows.append([])
        csv_rows.append(["User:"])
        csv_rows.append(["", "", "Validation"])
        labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
                  for i in accu_asse.values]
        csv_rows.append(["", ""] + labels)

        user_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
        for idx_row, row in enumerate(error_matrix_area_prop):
            for idx_col, value in enumerate(row):
                user_accuracy_matrix[idx_row][idx_col] = value / sum(row) if sum(row) > 0 else 0

        for idx_row, value in enumerate(accu_asse.values):
            r = []
            if idx_row == 0:
                r.append("Thematic map classes")
            else:
                r.append("")
            r.append(value)
            r += [rf(t) if t > 0 else "-" for t in user_accuracy_matrix[idx_row]]
            csv_rows.append(r)

        ###################################
        csv_rows.append([])
        csv_rows.append(["Producer:"])
        csv_rows.append(["", "", "Validation"])
        labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
                  for i in accu_asse.values]
        csv_rows.append(["", ""] + labels)

        producer_accuracy_matrix = copy.deepcopy(error_matrix_area_prop)
        for idx_col, col in enumerate(zip(*error_matrix_area_prop)):
            for idx_row, value in enumerate(col):
                producer_accuracy_matrix[idx_row][idx_col] = value/sum(col) if sum(col) > 0 else 0

        for idx_row, value in enumerate(accu_asse.values):
            r = []
            if idx_row == 0:
                r.append("Thematic map classes")
            else:
                r.append("")
            r.append(value)
            r += [rf(t) if t > 0 else "-" for t in producer_accuracy_matrix[idx_row]]
            csv_rows.append(r)

    ###########################################################################
    # #### 3) Error matrix of estimated area proportion

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:
        csv_rows.append([])
        csv_rows.append(["3) Error matrix of estimated area proportion:"])
        csv_rows.append(["", "", "Validation"])
        labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
                  for i in accu_asse.values]
        csv_rows.append(["", ""] + labels + ["Wi"])

        for idx_row, value in enumerate(accu_asse.values):
            r = []
            if idx_row == 0:
                r.append("Thematic map classes")
            else:
                r.append("")
            r.append(value)
            r += [rf(t) if t > 0 else "-" for t in error_matrix_area_prop[idx_row]]
            r.append(rf(sum(error_matrix_area_prop[idx_row])) if sum(error_matrix_area_prop[idx_row]) > 0 else "-")
            csv_rows.append(r)

        csv_rows.append(["", "total"] + [rf(sum(t)) for t in zip(*error_matrix_area_prop)])

    ###########################################################################
    # #### 4) Quadratic error matrix of estimated area proportion

    if accu_asse.estimator in ['Simple/systematic post-stratified estimator', 'Stratified estimator']:
        csv_rows.append([])
        csv_rows.append(["4) Quadratic error matrix of estimated area proportion:"])
        csv_rows.append(["", "", "Validation"])
        labels = ["{} ({})".format(i, accu_asse.labels[str(i)] if str(i) in accu_asse.labels else "-")
                  for i in accu_asse.values]
        csv_rows.append(["", ""] + labels)

        for idx_row, value in enumerate(accu_asse.values):
            r = []
            if idx_row == 0:
                r.append("Thematic map classes")
            else:
                r.append("")
            r.append(value)
            r += [rf(t) if t > 0 else "-" for t in quadratic_error_matrix[idx_row]]
            csv_rows.append(r)

        csv_rows.append(["", "total"] + [rf(sum(t)**0.5) for t in zip(*quadratic_error_matrix)])

    ###########################################################################
    # #### 3/5) Class area adjusted

    csv_rows.append([])
    csv_rows.append(["{}) Class area adjusted:".format("3" if accu_asse.estimator == 'Simple/systematic estimator' else "5")])
    csv_rows.append(["", "Area adjusted ({area_unit})".format(area_unit=accu_asse.pixel_area_unit), "Error", "Lower limit", "Upper limit"])

    total_area = 0

    # the error for post-stratified
    if accu_asse.estimator == 'Simple/systematic post-stratified estimator':
        std_dev_table = [[(1-i/total_row)**2*i/(total_row-1) if total_row not in [0, 1] else np.NaN
                          for i in row] for total_row, row in
                         zip([sum(r) for r in accu_asse.error_matrix], accu_asse.error_matrix)]
        wi = [accu_asse.thematic_pixels_count[value]/total_pixels_classes
              for value in accu_asse.values]
        variance = [((1-total_samples/total_pixels_classes)/total_samples)*sum([w*s for w,s in zip(wi, std_dev_col)]) +
                    (1/(total_samples**2))*sum([(1-w)*s for w,s in zip(wi, std_dev_col)])
                    for std_dev_col in zip(*std_dev_table)]
        _error = [sum_total_class_area*v**0.5 for v in variance]

    for idx_row, value in enumerate(accu_asse.values):
        if accu_asse.estimator == 'Simple/systematic estimator':
            p_k = sum(list(zip(*accu_asse.error_matrix))[idx_row])/total_samples
            area = p_k * sum_total_class_area
            v_p_k = ((p_k)*(1-p_k)/total_samples)*(total_pixels_classes-total_samples)/(total_pixels_classes-1)
            error = (v_p_k**0.5) * sum_total_class_area
        if accu_asse.estimator == 'Simple/systematic post-stratified estimator':
            area = sum(list(zip(*error_matrix_area_prop))[idx_row]) * sum_total_class_area
            error = _error[idx_row]
        if accu_asse.estimator == 'Stratified estimator':
            area = sum(list(zip(*error_matrix_area_prop))[idx_row]) * sum_total_class_area
            error = (sum(list(zip(*quadratic_error_matrix))[idx_row])**0.5) * sum_total_class_area

        r = []
        r.append("{} ({})".format(value, accu_asse.labels[str(value)] if str(value) in accu_asse.labels else "-"))

        # area
        r.append(rf(area))
        total_area += area
        # error
        r.append(rf(error))
        # lower limit
        lower_limit = area - accu_asse.z_score * error
        lower_limit = 0 if lower_limit < 0 else lower_limit
        r.append(rf(lower_limit))
        # upper limit
        r.append(rf(area + accu_asse.z_score * error))
        csv_rows.append(r)

    csv_rows.append(["total"] + [rf(total_area)])

    # write CSV file
    with open(file_out, 'w') as csvfile:
        csv_w = csv.writer(csvfile, delimiter=str(csv_separator))
        # replace with the user define decimal separator
        if csv_decimal_separator != ".":
            for idx, row in enumerate(csv_rows):
                csv_rows[idx] = [str(item).replace('.', csv_decimal_separator) if isinstance(item, float) else item for item in row]

        csv_w.writerows(csv_rows)

