# Introduction

Maps are essential tools for environmental monitoring, resource management, and sustainable
development planning. As global resources become increasingly scarce due to population growth
and environmental pressures, their role has widened further, into urban planning, emergency
response, and habitat conservation. They serve as critical instruments for communication,
navigation, and decision support, providing a symbolic representation of reality
{cite}`Awange2013`. By supplying precise and timely spatial information, maps enable us to
measure, analyze, and understand the extent and distribution of resources, empowering
decision-makers to take informed actions {cite}`Congalton2019`.

Since maps are models or generalizations of reality, they inherently contain errors due to
factors such as map projections, construction techniques, and data symbolization
{cite}`Lightfoot1987,Maling2013`. That single fact has **two distinct consequences** for anyone
who uses a thematic map:

1. You do not know **how good the map is** — which classes are reliable and which are not.
2. You do not know **how much area each class really covers** — because the mapped extent of a
   class is not the same as its true extent.

AcATaMa answers both questions from the same set of labeled sample points. The two sections below
explain why each matters; the rest of the documentation describes how the plugin delivers them.

## Assessing Map Quality

The primary goal of quantitative accuracy assessment is to quantify the error (or correctness) of
mapped labels or attributes by comparing them with true reference data, providing critical
insights into the reliability of classification results {cite}`Congalton2019`. It is, in effect,
the **quality control** step of map production: it establishes whether a map is fit for the use
it is intended to serve, and makes the limits of that fitness explicit.

A rigorous assessment of map accuracy is necessary to either derive scientifically valid data or
ensure the reliability of data for decision-making {cite}`Stehman1998,Strahler2006,Olofsson2014`:

- **For researchers**: the construction of scientific knowledge requires a structured and
  robust analytical framework with appropriate statistical methods to make valid inferences;
  consequently, maps without associated information on the accuracy of the predictions
  essentially remain untested hypotheses {cite}`Strahler2006,McRoberts2011,Mitchell2018`.

- **For policymakers**: errors in geospatial data can lead to flawed conclusions and misguided
  actions with potentially serious consequences; assessing the accuracy of thematic maps is
  essential to incorporate realistic expectations into the planning processes and environmental
  monitoring, supporting informed decision-making and effective resource allocation
  {cite}`Estes1994,McKendry2000,Foody2001,Foody2015`.

Because accuracy is reported per class — not only as a single overall figure — quality control
also tells you *where* a map can be trusted. A map may be highly accurate for a dominant, stable
class and unreliable for the rare change class that a study actually depends on.

## Estimating Area

The accuracy measures alone do not answer the second question. Knowing that a class has 85 %
user's accuracy tells you how often that label is correct, but not how much of the class actually
exists on the ground.

The intuitive answer — count the pixels labeled as a class and multiply by the pixel size — is
biased whenever the map contains classification error, which in practice is always
{cite}`Gallego2004,Olofsson2013,Olofsson2014`. Omission and commission errors do not cancel out,
so the mapped area of a class departs systematically from its true area. {cite:t}`Gallego2004`
characterizes this as a **measurement bias** rather than an estimator bias: the map is a complete
census of the territory, but the instrument doing the counting is imperfect. This is why the
problem cannot be solved by mapping more carefully at the margins or by collecting a larger
sample — the bias is a property of the map itself.

The distortion is most severe for **rare classes**, which are usually the ones that matter most
in change monitoring. A class such as deforestation may occupy a very small fraction of the
territory, so even a low commission rate among the dominant stable classes introduces
false-positive pixels that are large relative to the rare class's true extent
{cite}`Olofsson2014,Olofsson2020,Stehman2024`. Reporting a raw pixel count in that situation can
misstate the very change being monitored.

Good practice is therefore to derive the area from the **reference sample**, using the map only
to define the strata and their weights {cite}`Olofsson2013,Olofsson2014,Stehman2013`. Expressing
the error matrix in terms of area proportions instead of sample counts yields a design-based
estimator of each class's true proportion, and hence its area. Just as importantly, that
estimator carries a **variance** — so the output is not merely a corrected number but a number
with a confidence interval, which a pixel count can never provide.

That property is what makes an area figure reportable. Good-practice guidance for forest
monitoring and greenhouse-gas accounting requires activity data to be accompanied by quantified
uncertainty {cite}`Global2020,FAO2016,Finegold2016`. AcATaMa produces the area-adjusted estimate,
its standard error, the confidence interval, the uncertainty and the coefficient of variation
{cite}`McMurray2017` in the same operation that produces the accuracy metrics.

Two design decisions make the plugin practical for this purpose:

- **The estimator follows the sampling design.** Stratum weights are taken from the thematic map
  under assessment, and the estimator is selected to match the design in use — simple random,
  stratified, systematic, or post-stratified — so the area estimate is always statistically
  consistent with the sample that produced it.
- **The estimate stays tied to the assessment.** The error matrix, the accuracy metrics and the
  area estimates come from one sample, one map and one configuration. This removes the manual
  transfer step between separate accuracy and area tools, which is where inconsistent
  assumptions typically enter.

```{seealso}
A worked application of both outputs is described in
[Real-World Case Study](install_and_example.md#real-world-case-study).
```

## Why a Dedicated Tool

Despite the widespread acceptance of accuracy assessment and the extensive literature on the
topic, conducting rigorous assessments remains **operationally challenging**. Practitioners must
translate statistical guidance into sampling designs, define response protocols, interpret
reference data consistently, calculate design-based accuracy and area estimators, and report
uncertainty in a reproducible way. Each step demands specialized expertise, which can itself pose
a barrier to adoption {cite}`Foody2001`.

These steps are also frequently distributed across separate GIS, spreadsheet, scripting, and
visual interpretation tools, each covering only part of the workflow. Every hand-off between them
is an opportunity for inconsistent assumptions or incomplete reporting. Several existing tools
and platforms support important parts of the workflow — visual reference-data interpretation,
sampling design, or area estimation — but none brings all three stages together in a single,
open-source desktop environment. Some rely on persistent internet connectivity or cloud
platforms, others require programming expertise, and proprietary options impose licensing costs
that limit accessibility.

AcATaMa (Accuracy Assessment of Thematic Maps) was developed to close that gap: a QGIS plugin
providing a **complete, open-source, and offline-capable workflow** that integrates sampling
design, response design, and analysis in a single, user-friendly environment, within a
**design-based inference framework**.

## Theoretical Foundation

AcATaMa is designed and developed based on validated methodologies from foundational research
studies in thematic map accuracy assessment. Its structure and protocols follow the fundamental
principles outlined by {cite:t}`Stehman1998` for the design and analysis of accuracy assessment
for raster thematic maps. The sampling methods, statistical techniques, and estimation
procedures are implemented as specified in the literature for each sampling design by
{cite:t}`Cochran1977` and {cite:t}`Sarndal1992`.

Additionally, AcATaMa incorporates other key recommendations for good practice in accuracy
assessment from {cite:t}`Stehman2009`, {cite:t}`Olofsson2013`, {cite:t}`Olofsson2014`,
{cite:t}`Stehman2014`, {cite:t}`Finegold2016`, {cite:t}`FAO2016`, {cite:t}`Stehman2019`, and
{cite:t}`Global2020`.

These protocols and best practices for accuracy assessment are internationally recognized,
widely accepted, and extensively applied in numerous studies and real-world applications across
various disciplines. Only well-validated and widely trusted methods have been integrated into
AcATaMa to ensure reliable, reproducible, and statistically rigorous accuracy assessments.

### Equations, Measures and Estimators

The following table presents the equations, measures, and estimators incorporated in AcATaMa's
sampling design and analysis protocol, which are used for sampling design, accuracy assessment,
and area estimation. The estimator applied depends on the **sampling design** selected in the
plugin, so make sure the design reported in the analysis window matches the design you intend to
report.

```{list-table}
:header-rows: 1
:widths: 14 18 18 50

* - Sampling design
  - Measures and estimators
  - Reference
  - Key formulas (compact notation)
* - Simple random sampling (SRS)
  - Accuracy (overall, user's, producer's)
  - {cite:t}`Stehman2009`, Table 21.3
  - $$\hat{O} = \frac{\sum_{i=1}^{q} n_{ii}}{n}, \quad \hat{U}_i = \frac{n_{ii}}{n_{i+}}, \quad \hat{P}_j = \frac{n_{jj}}{n_{+j}}$$
* -
  - Area estimation and confidence interval
  - {cite:t}`Stehman2013`, Eqs. 13 and 44
  - $$\hat{p}_{+j} = \frac{n_{+j}}{n}, \quad \hat{A}_j = A_T\, \hat{p}_{+j}$$
    $$\hat{V}\left(\hat{p}_{+j}\right) = \frac{\hat{p}_{+j}\left(1 - \hat{p}_{+j}\right)(N - n)}{n(N - 1)}$$
* - Stratified random sampling (STR)
  - Accuracy (overall, user's, producer's)
  - {cite:t}`Olofsson2013`, Eqs. 1–3
  - $$\hat{q}_{ij} = \frac{n_{ij}}{n_{i+}}, \quad \hat{p}_{ij} = W_i\, \hat{q}_{ij}, \quad \hat{O} = \sum_i \hat{p}_{ii}$$
    $$\hat{U}_i = \frac{\hat{p}_{ii}}{\hat{p}_{i+}}, \quad \hat{P}_j = \frac{\hat{p}_{jj}}{\hat{p}_{+j}}$$
* -
  - Area estimation and confidence interval
  - {cite:t}`Olofsson2013`, Eqs. 10–11
  - $$\hat{p}_{+j} = \sum_i W_i\, \hat{q}_{ij}, \quad \hat{A}_j = A_T\, \hat{p}_{+j}$$
    $$\hat{V}\left(\hat{p}_{+j}\right) = \sum_i \frac{W_i^{2}\, \hat{q}_{ij}\left(1 - \hat{q}_{ij}\right)}{n_{i+} - 1}$$
* -
  - Sample size and allocation
  - {cite:t}`Olofsson2014`, Eq. 13
  - $$n = \frac{\left(\sum_i W_i S_i\right)^{2}}{\left[S\left(\hat{O}\right)\right]^{2} + \frac{1}{N}\sum_i W_i S_i^{2}} \approx \left(\frac{\sum_i W_i S_i}{S\left(\hat{O}\right)}\right)^{2}$$
    $$S_i = \sqrt{U_i\left(1 - U_i\right)}, \quad n_i \approx W_i\, n$$
    with a minimum allocation per stratum
* - Systematic sampling (SYS)
  - Accuracy (overall, user's, producer's)
  - {cite:t}`Stehman2009`, Table 21.3
  - $$\hat{O} = \frac{\sum_{i=1}^{q} n_{ii}}{n}, \quad \hat{U}_i = \frac{n_{ii}}{n_{i+}}, \quad \hat{P}_j = \frac{n_{jj}}{n_{+j}}$$
    SYS uses the simple (SRS) estimators
* -
  - Area estimation and confidence interval
  - {cite:t}`Stehman2012`, Eq. 3, for systematic design context
  - $$\hat{p}_{+j} = \frac{n_{+j}}{n}, \quad \hat{A}_j = A_T\, \hat{p}_{+j}$$
    $$\hat{V}\left(\hat{p}_{+j}\right) = \frac{\hat{p}_{+j}\left(1 - \hat{p}_{+j}\right)(N - n)}{n(N - 1)}$$
    SYS uses the simple (SRS) area estimator
* - Post stratified
  - Area estimation and confidence interval
  - {cite:t}`Stehman2013`, Eq. 48
  - $$\hat{p}_{+j}^{\mathrm{PS}} = \sum_h W_h^{\mathrm{PS}}\left(\frac{n_{hj}}{n_{h+}}\right), \quad \hat{A}_j^{\mathrm{PS}} = A_T\, \hat{p}_{+j}^{\mathrm{PS}}$$
    $$\hat{V}\left(\hat{p}_{+j}^{\mathrm{PS}}\right) = \frac{1}{n}\left(1 - \frac{n}{N}\right)\sum_{h=1}^{H} W_h S_{yh}^{2} + \frac{1}{n^{2}}\sum_{h=1}^{H}\left(1 - W_h\right) S_{yh}^{2}$$
* - SRS and SYS
  - Sample size
  - {cite:t}`Cochran1977`, Eq. 4.2
  - $$n = \frac{Z^{2}\, p\,(1 - p)}{d^{2}}$$
    where $p$ is the anticipated overall accuracy, $d$ the desired half-width of the confidence
    interval and $Z$ the standard normal quantile
* - All designs
  - Uncertainty and coefficient of variation
  - {cite:t}`McMurray2017`, p. 17
  - $$U(\%) = \frac{100\, z\, \mathrm{SE}\left(\hat{A}_j\right)}{\hat{A}_j}, \quad \mathrm{CV}(\%) = \frac{100\, \mathrm{SE}\left(\hat{A}_j\right)}{\hat{A}_j}$$
```

**Notation:** $n$ = total sample size; $N$ = total number of map units/pixels in the analysis
area; $n_{ij}$ = sample count in map/stratum row $i$ and reference-class column $j$; $n_{i+}$ and
$n_{+j}$ = row and column totals; $W_i = A_i/A_T$; $A_T$ = total map area; $\hat{q}_{ij}$ =
within-stratum sample proportion; $\hat{p}_{ij}$ = area-adjusted proportion; $U_i$ = conjectured
user's accuracy for stratum $i$; $S(\hat{O})$ = target standard error of overall accuracy;
$z$ = normal critical value for the selected confidence level.

```{tip}
The minimum-per-stratum allocation prevents rare but policy-relevant classes (for example
deforestation) from receiving too few samples to yield comparably precise estimates. See
[Sampling Design](sampling_design.md) for how to set this in the plugin.
```

```{important}
AcATaMa has been rigorously tested using multiple real-world examples across various use cases
to ensure the reliability of its results. This involved manually calculating several test cases
from scratch and systematically comparing them with AcATaMa's outputs to validate its
computational accuracy.
```
