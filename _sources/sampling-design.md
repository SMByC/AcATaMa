# Sampling Design

Assessing the accuracy of thematic maps requires sampling, as verifying every location on the ground is neither practical nor cost-effective. An effective sampling design depends on characterizing the distribution of map classes, determining the appropriate sample size and allocation, and selecting a suitable sampling scheme.

Since sampling design directly affects both cost and statistical reliability, it is one of the most critical components of thematic map accuracy assessment, ensuring that reference data are selected using statistically valid and representative procedures {cite}`Stehman1998`. A well-structured sampling design is essential for producing unbiased accuracy estimates and reliable area estimates.

According to {cite:t}`Olofsson2014`, **probability sampling is recommended** because every unit in the population has a known, non-zero chance of selection, thereby allowing for design-based, statistically rigorous inferences.

```{image} img/sampling_design.webp
:width: 85%
:align: center
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
- **Initial inset**: The distance from the top-left corner of the study area to the first point unit
- **Max offset**: Maximum distance along the X and Y axes from the point of the aligned systematic grid
- **Random offset area**: The area surrounding each point where a random offset is applied

```{tip}
To ensure the offset area covers the entire thematic map (giving every pixel an equal probability of being selected), set the maximum offset value to half of the point spacing.
```

#### Aligned Systematic Sampling

*(When the max XY offset value is zero)*

Distributes the sampling units equally for the entire study area. As long as the first sampling unit is randomly selected, systematic sampling is considered random.

**Advantages:**
- Distributes sampling units equitably throughout the study area
- Simplicity is highly attractive to end users
- The variance depends on how the error is spatially distributed

**Disadvantages:**
- If errors are located in certain areas, systematic sampling will have a lower variance
- Non-existence of an impartial estimator for calculating the variance
- Not desirable in the presence of uniformly distributed errors

#### Unaligned Systematic Sampling

*(When the max XY offset value is NOT zero)*

The area is divided into smaller, regularly spaced regions, with a randomly chosen sample unit within each region. This minimizes the effects of the periodicity of errors.

**Advantages:**
- Less susceptible to error if linearity of error is present
- The calculation of the variance is acceptable and unbiased

**Disadvantages:**
- Reduces the advantage of spatial distribution of error
- The lack of an unbiased estimator

## Additional Features

### Reproducibility

The plugin ensures randomness by automatically generating a random seed for all sampling methods. However, if users require reproducible sampling results, they can set a **fixed seed**. Setting a known seed value ensures replicability given identical inputs and configurations.

```{important}
Setting a known seed ensures that the assessment can be reproduced and validated by other parties, which is critical for scientific studies and decision-making.
```

### Minimum Distance Constraint

A minimum distance constraint between sampling units helps prevent spatial clustering, reduces spatial autocorrelation effects, and ensures a more evenly distributed sample.

### Neighbor Aggregation

The neighbor-aggregation feature (counting the number of neighbors with the same class) allows users to define sampling based on adjacent pixel values, improving spatial consistency and reducing edge effects.

### Post-Stratification

AcATaMa offers post-stratification for SRS and SYS, enabling users to adjust estimation weights after sampling to correct class imbalances, ultimately improving the reliability of accuracy estimates.

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
