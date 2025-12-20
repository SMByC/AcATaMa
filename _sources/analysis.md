# Analysis

The analysis component of thematic map accuracy assessment focuses on quantifying classification accuracy and estimating mapped class areas while accounting for uncertainty {cite}`Stehman1998`.

```{image} img/accuracy_assessment.webp
:width: 85%
:align: center
```

## Error Matrix

A central element of this process is the **error (confusion) matrix**, which provides a detailed comparison between map classifications and reference data. The matrix enables the calculation of key accuracy metrics:

- **Overall accuracy**
- **User's accuracy** (commission error)
- **Producer's accuracy** (omission error)

The confusion matrix is the most widely used method for assessing accuracy. The matrix should remain a cornerstone of the analysis protocol due to its ease of interpretation and valuable descriptive information.

Typically, the map data is arranged in **rows** and the reference data is arranged in **columns** in the matrix. The values arranged on the diagonal indicate the degree of agreement between the two data sets.

This matrix is essential for the analysis of the area and variance estimators. The row and column totals of the population error matrix are important because they quantify the distribution, by area, of different land cover classes:
- **Row totals**: Proportion of area of each class according to the map classification
- **Column totals**: Proportion of area according to the reference classification

## Accuracy Measures

### Overall Accuracy

The global accuracy has a direct interpretation in terms of area, since it represents the proportion of area correctly classified.

```{note}
Overall accuracy hides important information specific to each class. The limitation to overall accuracy is not how it weights or represents class-specific information, but rather that it does not provide class-specific information.
```

### User's Accuracy

The number of correctly classified sampling units (nii) in a class divided by the total number of sampling units of that same class in the map (nk+).

User's accuracy is associated with the measurement of **commission errors**, which are defined as the inclusion of a map area in a land cover class in which that area should not be included.

### Producer's Accuracy

The number of correctly classified sampling units (njj) in a class divided by the total number of sampling units in the reference data n+j for that class.

Producer's accuracy is associated with **omission errors**, which occur when an area is excluded on the map from the land cover class to which it should belong.

```{tip}
Errors of omission and errors of commission can be problematic to different degrees depending on the goals of a given application. Therefore, it is advisable to have separate estimates of user and producer accuracies. If general measures are reported, they must be accompanied by specific measures of each class.
```

### About Kappa

```{warning}
AcATaMa does not include the Kappa coefficient in the results, because in general we don't recommend using it. The kappa coefficient is widely used as a measure of thematic accuracy in remote sensing. However, {cite:t}`Foody2020` and {cite:t}`Pontius2011` have shown that the Kappa coefficient is not a good measure of accuracy. {cite:t}`Pontius2011` argued that Kappa indices are redundant, useless, and/or flawed and should be abandoned because they do not provide any information helping in the purpose of accuracy assessment and map comparison. {cite:t}`Foody2020` said that while Kappa is a useful measure of agreement, it is not a good measure of accuracy.
```

## Area Estimation

The area estimation component of accuracy assessment adjusts the mapped class areas based on accuracy assessment results, ensuring **unbiased and statistically more precise estimates**.

According to {cite:t}`Olofsson2014`, relying solely on sample counts can introduce significant bias, particularly in land change analyses where errors in classification disproportionately affect small or rare classes. By incorporating adjustments using strata areas in the estimations derived from the error matrix, area estimates are corrected to better reflect true land cover proportions.

### Class Area Adjusted

The accuracy assessment serves to derive the uncertainty of the map area estimates. Whereas the map provides a single area estimate for each class without confidence interval, the accuracy estimates:
- Adjust this estimate
- Provide confidence intervals as estimates of uncertainty

The adjusted area estimates can be considerably higher or lower than the map estimates {cite}`FAO2016`.

### Confidence Intervals

The estimated area for each class or stratum and the standard error of the estimated area allow obtaining the confidence interval with the percent defined by the z-score value.

It is typically represented by confidence intervals, which indicate the range within which the true area proportions are expected to lie with a specified level of confidence, such as **95% (Z=1.96)**.

### Coefficient of Variation and Uncertainty

The coefficient of variation is a standardized measure of the dispersion of the estimated area proportions, calculated as the ratio of the standard error to the mean estimate. It provides a relative measure of variability, allowing for comparisons across different classes or studies.

- **Lower CV** indicates higher precision of the estimates

Uncertainty encompasses the potential errors and variability inherent in the sampling design, classification accuracy, and reference data used for accuracy assessment. Quantifying this uncertainty is crucial as it measures the reliability and precision of the area estimates.

## Equations and Estimators

Based on the importance of accuracy and area estimation adjustments and recommendations, AcATaMa provides a comprehensive set of analysis results calculated according to the selected sampling design:

| Sampling Design | Component | Source |
|-----------------|-----------|--------|
| **Simple Random (SRS)** | Accuracy | {cite:t}`Stehman2009`: Table 21.3 |
| | Estimating area and confidence intervals | {cite:t}`Stehman2013`: Eq. 13 and 44 |
| | Sample size | {cite:t}`Cochran1977`: Eq. 4.2 |
| **Stratified Random (STR)** | Accuracy | {cite:t}`Olofsson2013`: Eq. 1, 2 and 3 |
| | Estimating area and confidence intervals | {cite:t}`Olofsson2013`: Eq. 10 and 11 |
| | Sample size per strata | {cite:t}`Olofsson2014`: Eq. 13 |
| **Systematic (SYS)** | Accuracy | {cite:t}`Stehman2009`: Table 21.3 |
| | Estimating area and confidence intervals | {cite:t}`Stehman2012`: Eq. 3 |
| | Sample size | {cite:t}`Cochran1977`: Eq. 4.2 |
| **Post-Stratified** | Estimating area and confidence intervals | {cite:t}`Stehman2013`: Eq. 48 |
| **Uncertainty** | All designs | {cite:t}`McMurray2017`: Page 17 |

```{important}
AcATaMa has been rigorously tested using multiple real-world examples across various use cases to ensure the reliability of its results. This involved manually calculating several test cases from scratch and systematically comparing them with AcATaMa's outputs to validate its computational accuracy.
```
