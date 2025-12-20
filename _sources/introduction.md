# Introduction

Since maps are models or generalizations of reality, they inherently contain errors due to factors such as map projections, construction techniques, and data symbolization. The primary goal of quantitative accuracy assessment is to quantify the error (or correctness) of mapped labels or attributes by comparing them with true reference data, providing critical insights into the reliability of classification results. In addition, accuracy assessment supports the estimation of area-adjusted class proportions and their confidence intervals as measures of uncertainty. These statistically adjusted estimates are often more accurate than areas derived directly from the map {cite}`Olofsson2013,Olofsson2014,FAO2016,Foody2015,Global2020`.

A rigorous assessment of map accuracy is necessary to either derive scientifically valid data or ensure the reliability of data for decision-making {cite}`Stehman1998,Strahler2006,Olofsson2014`:

- **For researchers**: The construction of scientific knowledge requires a structured and robust analytical framework with appropriate statistical methods to make valid inferences; consequently, maps without associated information on the accuracy of the predictions essentially remain untested hypotheses.

- **For policymakers**: Errors in geospatial data can lead to flawed conclusions and misguided actions with potentially serious consequences; assessing the accuracy of thematic maps is essential to incorporate realistic expectations into the planning processes and environmental monitoring, supporting informed decision-making and effective resource allocation.

### Why AcATaMa?

The development of AcATaMa was motivated by the need for a standardized, user-friendly tool to support rigorous thematic map accuracy assessment and to produce adjusted, sample-based area estimates. Traditional accuracy assessment methods often require multiple software tools and workflows and involve complex statistical procedures that demand specialized expertise and can pose a barrier to adoption.

AcATaMa addresses these challenges by offering an integrated and intuitive suite of tools that simplify the processes of sampling design, response design, and analysis, while ensuring statistical rigor and reproducibility. AcATaMa was developed as an open-source QGIS plugin specifically designed for the accuracy assessment of thematic raster maps in alignment with international guidance and good practice, including the Intergovernmental Panel on Climate Change (IPCC) principles of transparency, completeness, consistency, comparability, and accuracy.

The versatility of AcATaMa allows for a wide range of applications, it has been used and cited in numerous studies across various fields, including:

- Deforestation monitoring
- Land-cover classification and change analysis
- Environmental and ecological studies
- Wildfire monitoring
- Water and watershed analysis
- Agricultural research

## Theoretical Foundation

AcATaMa is designed and developed based on validated methodologies from foundational research studies in thematic map accuracy assessment. Its structure and protocols follow the fundamental principles outlined by {cite:t}`Stehman1998` for the design and analysis of accuracy assessment for raster thematic maps. The plugin implements sampling methods, statistical techniques, and estimation procedures as specified in the literature for each sampling design.

AcATaMa incorporates key recommendations for good practice in accuracy assessment from {cite:t}`Stehman2009`, {cite:t}`Olofsson2013`, {cite:t}`Olofsson2014`, {cite:t}`Stehman2014`, {cite:t}`Finegold2016`, {cite:t}`Stehman2019`, and {cite:t}`Global2020`.

These protocols and best practices for accuracy assessment are internationally recognized, widely accepted, and extensively applied in numerous studies and real-world applications across various disciplines. Only well-validated and widely trusted methods have been integrated into AcATaMa to ensure reliable, reproducible, and statistically rigorous accuracy assessments.
