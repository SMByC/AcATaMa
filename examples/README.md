# AcATaMa Examples

This directory provides simple, ready-to-use AcATaMa configurations that demonstrate different sampling approaches, labeling methods, and settings for a 2019-2020 forest change map in Tinigua National Natural Park (Colombia). Each `.yaml` file represents a complete plugin state that can be loaded directly into AcATaMa, allowing you to explore the plugin's features.

## Requirements
- QGIS >= 3.30 with the **AcATaMa** plugin installed
- **Google Earth Engine** plugin (recommended)
- **CCD-Plugin** for QGIS (recommended) to access additional change-detection utilities while exploring the samples

## How to Use the Examples
1. Restore Qgis project **.qml** (optional, for the exercise with the same name)
2. Launch AcATaMa and choose **Restore state**, to load the YAML file

## Available Example Configurations

### Simple exercise - 2019-2020 change - Tinigua.yaml
Demonstrates a basic **simple random sampling** design for accuracy assessment of forest change detection, using equal probability sampling across the entire study area.

### Simple post-stratify exercise - 2019-2020 change - Tinigua.yaml
Showcases **simple random sampling with post-stratification**, where samples are initially drawn randomly, then post-stratified by map classes to improve precision in area and accuracy estimates.

### Stratified exercise - 2019-2020 change - Tinigua.yaml
Illustrates **stratified random sampling**, where samples are allocated proportionally (or optimally) across predefined strata (e.g., forest change vs. no change) to ensure adequate representation of each class.

### Systematic exercise - 2019-2020 change - Tinigua.yaml
Presents a **systematic sampling** design with samples distributed on a regular grid pattern across the study area, providing spatially balanced coverage for change detection assessment.

### Systematic post-stratify exercise - 2019-2020 change - Tinigua.yaml
Combines **systematic sampling with post-stratification**, leveraging the spatial regularity of systematic designs while applying post-stratification adjustments to improve area estimation accuracy for specific strata.

### Tinigua Natural Park exercise 2019-2020 change.yaml
A comprehensive example workflow covering the full AcATaMa pipeline for forest change assessment in Tinigua Natural Park
