<p align="center"><img src="docs/img/acatama.svg"></p>
<h1 align="center">AcATaMa</h1>
<p align="center">
<a href="https://plugins.qgis.org/plugins/AcATaMa/"><img src="https://img.shields.io/badge/QGIS%20Plugin-Available-brightgreen.svg" alt="QGIS Plugin"></a>
<a href="https://github.com/SMByC/AcATaMa/actions"><img src="https://github.com/SMByC/AcATaMa/workflows/Tests/badge.svg" alt="Tests"></a>
<a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License"></a>
<br>
<b>Documentation:</b> <a href="https://smbyc.github.io/AcATaMa">https://smbyc.github.io/AcATaMa</a><br>
<b>Paper:</b> <a href="https://doi.org/10.1016/j.acags.2026.100389">https://doi.org/10.1016/j.acags.2026.100389</a><br>
</p>

Thematic maps are indispensable for environmental monitoring, resource management, and policy-making, yet their value depends critically on rigorous accuracy assessment. **AcATaMa** (Accuracy Assessment of Thematic Maps) is a free, open-source QGIS plugin that delivers an integrated workflow for thematic map accuracy assessment and sample-based area estimation, enabling users to follow international good practice guidelines within a single, accessible environment.

Conducting rigorous accuracy assessments is operationally challenging: practitioners must translate statistical guidance into sampling designs, define response protocols, interpret reference data consistently, calculate design-based accuracy and area estimators, and report uncertainty reproducibly. These steps are frequently spread across separate GIS, spreadsheet, scripting, and visual interpretation tools, increasing the risk of inconsistent assumptions or incomplete reporting. AcATaMa addresses this gap by bringing all three stages together within QGIS, in a **design-based inference framework** — a complete, open-source, and offline-capable workflow.

<div align="center">
<img src="docs/img/overview.webp" width="90%" style="margin: auto;display: block;">
</div>

The plugin integrates three fundamental components: **sampling design** (supporting simple random, stratified random, and systematic sampling), **response design** (providing a multi-window interface for simultaneous review of multiple reference data sources), and **analysis** (generating error matrices, accuracy metrics, and area-adjusted estimates with confidence intervals and uncertainty quantification).

AcATaMa has been adopted worldwide — with over 160,000 downloads and application in 86 peer-reviewed studies at the time of publication — for diverse applications including deforestation monitoring, land-cover classification and change analysis, urban analysis, biodiversity and ecosystem studies, wildfire monitoring, water and watershed analysis, and agricultural research.

<div align="center">
<img src="docs/img/process_overview.webp" height="450px" style="margin: auto;display: block;">
</div>

## Install

AcATaMa is available from the official QGIS Plugin Repository. To install it:

1. Open QGIS and go to `Plugins` → `Manage and Install Plugins…`.
2. In the search bar, type `AcATaMa` and click `Install Plugin`.
3. Once installed, activate the plugin via the `Plugins` menu or `Plugins toolbar`.

> **Note:** AcATaMa is compatible with both QGIS 3 (3.36+) and QGIS 4.

### External Python libraries

The AcATaMa plugin package does not bundle its external Python libraries. When Dask is not already available, AcATaMa downloads `extlibs.zip` from the matching GitHub release and installs it into the QGIS profile plugin directory.

For offline installations, download `extlibs.zip` from the same AcATaMa release as the plugin and extract its contents into the plugin `extlibs` directory, for example `QGIS3/profiles/default/python/plugins/AcATaMa/extlibs`.

## Citation

Please cite it as:

> Llano, X. C., Vergara, L. K., Arias, J. A., & Galindo, G. (2026). AcATaMa: A QGIS plugin for accuracy assessment and area estimation. Applied Computing and Geosciences, 31, Article 100389. https://doi.org/10.1016/j.acags.2026.100389

BibTeX:

```bibtex
@article{LLANO2026100389,
title = {AcATaMa: A QGIS plugin for accuracy assessment and area estimation},
journal = {Applied Computing and Geosciences},
volume = {31},
pages = {100389},
year = {2026},
issn = {2590-1974},
doi = {10.1016/j.acags.2026.100389},
url = {https://www.sciencedirect.com/science/article/pii/S259019742600073X},
author = {X.C. Llano and L.K. Vergara and J.A. Arias and G. Galindo},
}
```

## About Us

AcATaMa was developed by the Forest and Carbon Monitoring System (SMByC) at the Institute of Hydrology, Meteorology and Environmental Studies (IDEAM) in Colombia. SMByC is responsible for measuring and ensuring the accuracy of official national forest figures.

- [Xavier C. Llano](https://github.com/XavierCLL) - Author and lead developer
- [SMByC-PDI team](https://github.com/SMByC) - Development support and testing

This project was fully funded by the SMByC-IDEAM, Colombia.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md)
