<p align="center"><img src="docs/img/acatama.svg"></p>
<h1 align="center">AcATaMa</h1>
<p align="center">
<a href="https://plugins.qgis.org/plugins/AcATaMa/"><img src="https://img.shields.io/badge/QGIS%20Plugin-Available-brightgreen.svg" alt="QGIS Plugin"></a>
<a href="https://github.com/SMByC/AcATaMa/actions"><img src="https://github.com/SMByC/AcATaMa/workflows/Tests/badge.svg" alt="Tests"></a>
<a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License"></a>
<br>
<b>Documentation:</b> <a href="https://smbyc.github.io/AcATaMa">https://smbyc.github.io/AcATaMa</a><br>
<!--<b>Paper:</b> <a href="">soon</a>-->
</p>

AcATaMa (Accuracy Assessment of Thematic Maps) is an open-source QGIS plugin designed to provide comprehensive support for accuracy assessment and sample-based area estimation of raster thematic maps. The primary goal of AcATaMa is to equip users with the necessary tools to comply with international guidance and best practices for sampling design, estimation of land category areas and changes, and map accuracy assessment.

AcATaMa has been adopted worldwide for diverse applications including deforestation monitoring, land-cover classification and change analysis, environmental and ecological studies, wildfire monitoring, water and watershed analysis, and agricultural research.

<div align="center">
<img src="docs/img/overview.webp" width="90%" style="margin: auto;display: block;">
</div>

The plugin integrates three fundamental components: **sampling design** (supporting simple random, stratified random, and systematic sampling), **response design** (providing a multi-window interface for reference data interpretation), and **analysis** (generating error matrices, accuracy metrics, and area-adjusted estimates with uncertainty quantification).

<div align="center">
<img src="docs/img/process_overview.webp" height="450px" style="margin: auto;display: block;">
</div>

## Install

AcATaMa is available from the official QGIS Plugin Repository. To install it:

1. Open QGIS and go to `Plugins` → `Manage and Install Plugins…`.
2. In the search bar, type `AcATaMa` and click `Install Plugin`.
3. Once installed, activate the plugin via the `Plugins` menu or `Plugins toolbar`.

> **Warning:** The latest versions of AcATaMa (>=24.10) are not compatible with QGIS 3.28 or older versions due to changes in a QGIS function introduced in QGIS 3.30 (see issue #22). Please update QGIS to at least the LTR version (recommended) or the latest version.

## About Us

AcATaMa was developed by the Forest and Carbon Monitoring System (SMByC) at the Institute of Hydrology, Meteorology and Environmental Studies (IDEAM) in Colombia. SMByC is responsible for measuring and ensuring the accuracy of official national forest figures.

- [Xavier C. Llano](https://github.com/XavierCLL) - Author and lead developer
- [SMByC-PDI team](https://github.com/SMByC) - Development support and testing

This project was fully funded by the SMByC-IDEAM, Colombia.

## How to Cite

Llano, X. (version_year), SMByC-IDEAM. AcATaMa - QGIS plugin for Accuracy Assessment of Thematic Maps, version XX.XX. Available in https://github.com/SMByC/AcATaMa

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md)
