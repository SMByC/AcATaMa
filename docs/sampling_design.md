# Sampling Design

Assessing the accuracy of thematic maps requires sampling, as verifying every location on the ground is neither practical nor cost-effective. An effective sampling design depends on characterizing the distribution of map classes, determining the appropriate sample size and allocation, and selecting a suitable sampling scheme.

Since sampling design directly affects both cost and statistical reliability, it is one of the most critical components of thematic map accuracy assessment, ensuring that reference data are selected using statistically valid and representative procedures {cite}`Stehman1998`. A well-structured sampling design is essential for producing unbiased accuracy estimates and reliable area estimates.

According to {cite:t}`Olofsson2014`, **probability sampling is recommended** because every unit in the population has a known, non-zero chance of selection, thereby allowing for design-based, statistically rigorous inferences.

```{image} img/sampling_design.webp
:width: 85%
:align: center
```
<p align="center"><em>Sampling design interface in AcATaMa. The window enables users to select sampling
designs (simple random, stratified random, or systematic), define post-stratification strategies,
set minimum distance constraints, configure neighbor aggregation parameters, and establish
random seed values for reproducibility.</em></p>

## Sampling Designs

AcATaMa allows users to select from a variety of sampling designs to meet specific needs and to
ensure that the sample is representative of the population being studied.

The sampling units generated in AcATaMa are **points**: each pair of X and Y coordinates is
selected randomly (SRS and STR) or placed at a fixed interval with a random offset (SYS).

```{seealso}
The estimators applied for each design — and the sample-size formulas — are documented in
[Equations, Measures and Estimators](introduction.md#equations-measures-and-estimators).
```

### Simple Random Sampling (SRS)

```{image} img/simple_sampling.svg
:width: 25%
:align: center
```

Simple random sampling provides **equal probability to all units**. It is appropriate if the sample size is large enough to ensure that all classes are adequately represented and could be useful to serve the needs of a wide group of users.

**Advantages:**
- Extremely simple to use
- Adapts to the need to increase or decrease the sampling units
- Less complex statistical estimators compared to other sampling designs

**Disadvantages:**
- Underestimates the less representative classes
- Not well distributed spatially

### Stratified Random Sampling (STR)

```{image} img/stratified_sampling.svg
:width: 25%
:align: center
```

Stratified random sampling **increases precision via allocation across different map classes or strata**. It is useful for reporting results when strata are of interest and the precision of accuracy and area estimates need to be improved. As a result, it is one of the most commonly used designs.

This design is recommended by {cite:t}`Olofsson2014` as a good practice option for ensuring that rare classes are well represented.

For STR, the sample size for each stratum is calculated based on:
1. Class area proportions
2. A target standard error for overall accuracy
3. Anticipated user's accuracies by stratum

If necessary, the user can manually adjust the number of samples for one or more classes, e.g., to implement the allocation proposed by {cite:t}`Olofsson2014` or other allocation strategies.

**Advantages:**
- Allows to increase the sample size of the less common classes
- Lowers the standard errors of the accuracy estimates for rare classes
- Geographic stratification could be used to ensure a good spatial distribution
- Allows the option of using different sampling designs in different strata

**Disadvantages:**
- Stratification by geographic region does not result in a gain in precision
- Only the evaluation of the accuracy of the map that gives rise to the strata is allowed
- Sampling with an optimal allocation leads to different probabilities of inclusion, making estimator calculation more difficult

### Systematic Sampling (SYS)

```{image} img/systematic_sampling_info.svg
:width: 25%
:align: center
```

Systematic sampling **promotes even spatial distribution** by selecting samples at regular intervals across a grid, either by distance or pixel units. Sampling begins from a fixed or random point, starting in the top-left corner, and applies a random offset to the initial grid position.

We implemented two systematic sampling methodologies: one based on **physical distances** and the other on **pixel units**, both based on the thematic map.

```{image} img/systematic_sampling_by_distance.svg
:width: 35%
:align: center
```
<p align="center"><em>Systematic sampling by distance</em></p>

```{image} img/systematic_sampling_by_pixel.svg
:width: 35%
:align: center
```
<p align="center"><em>Systematic sampling by pixel</em></p>

**Parameters:**

- **Point spacing**: The spacing between points in the systematic grid (in distance units or pixels)
- **Initial inset**: The distance from the top-left corner of the study area to the first point unit. In
  *Random* mode it is drawn independently for the X and Y axes, between 0 and the point spacing, which
  gives every location of the map the same probability of being selected (random start). With a single
  draw per offset area the grid is extended beyond the map edges, so the initial inset only sets the
  position of the grid
- **Max offset**: Maximum distance along the X and Y axes from the point of the aligned systematic grid
- **Random offset area**: The area surrounding each point where a random offset is applied
- **Draws per offset area**: How the random location is drawn inside each offset area (see
  [Draws per Offset Area](#draws-per-offset-area) below)

```{tip}
Set the maximum offset value to half of the point spacing so the offset areas tile the whole thematic
map without overlapping; with a single draw per offset area every location then has the same probability
of being selected.
```

```{warning}
A *Fixed* initial inset with no random offset places the grid deterministically, so the sample is not a
probability sample and design-based inference does not strictly apply {cite}`Stehman2019`. Use a
*Random* initial inset (or a random offset) to obtain a probability sample. With a *Fixed* initial inset
and a random offset, the offset areas must tile the map (max offset of half the point spacing): a smaller
max offset leaves gaps whose locations can never be selected, and a larger one overlaps the offset areas,
so the inclusion probabilities are not equal in general. The sampling report warns about both cases.
```

The expected sample size of a systematic grid with a random start is the sampled area divided by the
square of the point spacing, whatever the shape of the area, because the grid has one point (or one offset
area with a single draw) at a random position per cell of the grid, so the expected number of points in any
area is its size divided by the square of the spacing. The point spacing proposed by the sample size
calculator is therefore {math}`d = \sqrt{A/n}`, where {math}`A` is the area with valid data of the thematic
map; the actual number of samples varies around {math}`n`. In the systematic sampling by pixels a pixel is
sampled only once, so overlapping offset areas (max offset larger than half the point spacing) give fewer
samples than {math}`A/d^2`; the expected number of samples shown in the sampling design window accounts
for it.

#### Aligned Systematic Sampling

```{image} img/aligned_systematic_sampling.webp
:width: 25%
:align: left
```

*(When the max XY offset value is zero)*

Distributes the sampling units equally for the entire study area. As long as the grid position is randomly selected (random initial inset), systematic sampling is a probability sample.

**Advantages:**
- Distributes sampling units equitably throughout the study area
- Simplicity is highly attractive to end users
- With positively autocorrelated errors it gives more precise estimates (smaller sampling variance) than
  simple random sampling {cite}`Stehman2019`

**Disadvantages:**
- There is no unbiased estimator of its variance; the simple random sampling variance estimators are
  approximations that usually overestimate the variance {cite}`Olofsson2014`
- Not desirable in the presence of periodic patterns aligned with the grid spacing

#### Unaligned Systematic Sampling

```{image} img/unaligned_systematic_sampling.webp
:width: 25%
:align: left
```

*(When the max XY offset value is NOT zero)*

It is also known as _"Random Sampling Within Blocks"_. The area is divided into smaller, regularly spaced regions, with a randomly chosen sample unit within each region. This minimizes the effects of the periodicity of errors and keeps the sample spatially balanced, as a spatial stratification with one sample unit per spatial stratum {cite}`Stehman2019`.

**Advantages:**
- Less susceptible to periodic patterns aligned with the grid than the aligned grid
- Keeps a good spatial distribution of the sample

**Disadvantages:**
- As for the aligned grid, there is no unbiased estimator of its variance; the simple random sampling
  variance estimators are approximations

#### Draws per Offset Area

When using unaligned systematic sampling (max XY offset > 0), a random location is drawn inside each
offset area. The **draws per offset area** option controls what happens when that location is not valid
(no data, outside the map, a class not selected for the post-stratification, or failing the neighbor
aggregation):

- **1 draw (equal probability, default):** a single random location is drawn in each offset area and it is
  kept only if it is valid, otherwise that offset area has no sample. The grid starts outside the map so the
  offset areas also cover its edges, and with a random initial inset, or with a fixed one and offset areas
  that tile the map (max offset of half the point spacing), every location of the map has the same
  inclusion probability (in the sampling by distance, the same expected number of samples), which is the
  assumption of the simple and post-stratified estimators used for systematic samples. In the sampling by
  distance, two samples of neighbor offset areas can (rarely) fall in the same pixel, as in simple random
  sampling, because discarding one of them would make the pixels cut by the borders of the offset areas
  less likely to be sampled.
- **Up to X% coverage:** the draw is repeated until a valid pixel is found, up to {math}`K` draws, the
  number of draws that would test a pixel of the offset area at least once with probability {math}`CL` if
  all of them were made:

```{math}
1 - \left(1-\frac{1}{N}\right)^K \ge CL \quad\Rightarrow\quad K = \left\lceil \frac{\ln(1-CL)}{\ln\left(1-\frac{1}{N}\right)} \right\rceil
```

The coverage {math}`CL` is nominal: it assumes that each draw selects any of the {math}`N` pixels of the
offset area with probability {math}`1/N`, which only holds approximately in the sampling by distance (a
pixel cut by the border of the offset area is drawn with the probability of its part inside it), while in
the sampling by pixels the repeated draws are made among the pixels with data. Besides, the draws stop at
the first valid pixel, which can reduce the probability that the other pixels are tested compared to
making all the {math}`K` draws.

```{warning}
Repeating the draw generates more samples but changes the inclusion probabilities. In an offset area with
only {math}`m` valid pixels, each of them is selected with probability
{math}`\left[1-\left(1-m/N\right)^K\right]/m`, which is larger than {math}`1/N` whenever {math}`m < N`.
For example, with {math}`N=16` and {math}`CL=0.95` ({math}`K=47`), an isolated valid pixel is selected with
probability 0.95 instead of 0.0625, so the valid pixels of partially valid offset areas (near no data, the
map edges or the classes not selected) are over-represented by up to {math}`N` times. In the systematic
sampling by pixels the repeated draws are made only among the pixels with data, so a pixel isolated by no
data is always selected. The simple and
post-stratified estimators do not account for these unequal inclusion probabilities {cite}`Stehman2019`,
so use the single draw unless the estimates are weighted accordingly. Configurations saved before this
option was saved are restored with "Up to 95% coverage", the default since version 26.1 (the coverage
selected was not saved). With a fixed initial inset and the same seed, this reproduces exactly the samples
generated with that default, but not the ones generated with another coverage or with the versions before
26.1, which repeated the draw without limit, nor the samples with a random initial inset, which is now
drawn independently for the X and Y axes.
```

## Additional Features

### Reproducibility

The plugin ensures randomness by automatically generating a random seed for all sampling methods; the
automatic seed is reported in the sampling report, so any sample can be reproduced later by setting it as
the seed by user. If users require reproducible sampling results from the start, they can set a
**fixed seed**. Setting a known seed value ensures replicability given identical inputs and configurations.

```{important}
Setting a known seed ensures that the assessment can be reproduced and validated by other parties, which is critical for scientific studies and decision-making, and it also supports the **IPCC principle of transparency** for national reports.
```

### Minimum Distance Constraint

A minimum distance constraint between sampling units prevents spatial clustering and gives a more evenly
distributed sample. However, it is not needed to legitimize design-based inference, whose estimators and
variance estimators remain unbiased regardless of spatial correlation {cite}`Stehman2019`. Discarding the
candidate samples within the minimum distance of a previous sample makes the inclusion probabilities very
complicated, and unless they are derived the design does not satisfy the criteria of a probability sample
{cite}`Stehman2019`; AcATaMa does not derive them, and its estimators assume the inclusion probabilities of
simple (or stratified) random sampling. The smaller the minimum distance compared to the mean distance
between samples, the fewer candidates are discarded and the closer the design is to random sampling. To
obtain a spatially balanced sample, use systematic sampling, the most familiar spatially balanced
probability design {cite}`Stehman2019`.

### Neighbor Aggregation

Neighbor aggregation calculates, for each candidate sample location, the number of adjacent pixels in a user-defined neighborhood that share the same class, and only accepts the locations with at least the required number.

```{warning}
Neighbor aggregation restricts the population that is sampled to the pixels with a homogeneous
neighborhood, a part of the map whose area is not known. The accuracy estimated from the sample counts
(simple estimator, and the user's accuracies of all the estimators) refers only to that part of the map and
must be reported as such, while the area estimates and the accuracy estimates weighted with the mapped area
of the classes in the whole map (overall and producer's accuracy of the stratified and post-stratified
estimators) are not valid, neither for the whole map nor for that part. Accuracy is generally higher there
than for the whole map, because edge and heterogeneous pixels, which are more difficult to classify
correctly and more affected by geolocation errors, are excluded {cite}`Stehman2019`. To assess the impact
of locational error, prefer reporting the accuracy of the homogeneous subset of a sample of the whole map
alongside the full results {cite}`Stehman2019`.
```

### Post-Stratification

AcATaMa supports post-stratification for simple random sampling (SRS) and systematic sampling (SYS), enabling users to adjust estimation weights after sampling to correct class imbalances, ultimately improving the reliability of accuracy estimates {cite}`McRoberts2012`.

#### What post-stratification means

Post-stratification groups the already selected SRS/SYS reference sample into "post-strata" (e.g., map classes) and then adjusts the estimation weights using known totals for those map classes. In AcATaMa's analysis, based on the confusion-matrix sample counts it creates the estimated area proportions using the post-stratified estimator of {cite:t}`Stehman2013` (Eq. 48); see [Equations, Measures and Estimators](introduction.md#equations-measures-and-estimators).

#### When to use it

Post-stratification is useful when SRS/SYS produces an imbalanced realized sample (for example, rare classes end up with too few points), because post-stratification can reweight the sample using known class totals to produce more defensible accuracy/area estimates. However, post-stratification reweights estimates after sampling ("sample first, classify later"), so the number of samples in each post-stratum is determined by how the initial sample falls across classes; as a result, it is not possible to control (or guarantee) the per-class sample size the way stratified sampling does.

For simple random and systematic samples, {cite:t}`Olofsson2014` recommend the stratified (here,
post-stratified) estimators of accuracy and area with the map classes as strata, which are generally more
precise than the simple estimators; nearly the same precision as a proportionally allocated stratified
sample is achieved this way {cite}`Stehman2019`.

## Sample Size

### Sample Size for Stratified Sampling

#### Overall Expected Standard Error - S(Ô)

```{image} img/overall_std_error.webp
:width: 35%
:align: center
```

The standard error of the estimated overall accuracy that you would like to achieve. For stratified sampling, {cite:t}`Cochran1977` provides the sample size formula:

```{image} img/ecuation_sample_size.webp
:width: 70%
:align: center
```

Where:
- N = number of units in the study region
- S(Ô) = standard error of the expected global accuracy
- Wi = mapped proportion of the area of class i
- Si = standard deviation of stratum i
- Ui = accuracy expected by class i

Since N is usually very large, the second term in the denominator can be discarded.

#### User's Accuracy Confidence

```{image} img/user_accuracy.webp
:width: 35%
:align: center
```

The user's accuracy (Ui) is the probability that a pixel classified as class i is actually class i. In general:

- **0.6 - 0.8**: for unstable classes
- **0.8 - 0.95**: for stable classes

Example values based on {cite:t}`Olofsson2014` for forest change assessment:

- 0.6 - 0.7: forest gain (very unstable class)
- 0.7 - 0.8: deforestation (unstable class)
- 0.8 - 0.9: stable forest (stable class)
- 0.95: stable non-forest (very stable class)

### Minimum Sample Size per Stratum

```{image} img/minimum_sampling_per_stratum.webp
:width: 35%
:align: center
```

Using stratified or post-stratified sampling, a minimum sample size of **30** {cite}`VanGenderen1978` or **50** {cite}`Stehman2019,Hay1979` per evaluated stratum is generally recommended to ensure statistical significance.
