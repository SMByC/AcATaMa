---
layout: default
---

# Analysis

<img src="img/accuracy_assessment.webp" width="100%" style="margin: auto;display: block;">

The main objective of the accuracy evaluation is the estimation of the area. It seeks to ensure that each land cover
class is correctly classified, as well as the confidence intervals of the accuracy measurements for said cover classes.
For this, the analysis component should focus on organizing and summarizing information to quantify accuracy. And later,
estimate the accuracy and the area, from the sample data.

Accuracy assessment focuses on three types of analysis and parameters. The first at a global level, defined as general
accuracy or Kappa coefficient. The second that focuses on the specific accuracy of the class and is classified as the
accuracy of the user or the producer. And, the third, which corresponds to the estimation of the proportion of area by
a class. In practice, the analysis should focus on easily interpretable accuracy measures, and thus the error matrix
should reflect the area proportional representation of the study region. The main requirements for the analysis to
satisfy the criterion of statistical rigor involve using consistent estimators and quantifying the variability of the
accuracy and area estimates, using standard errors or confidence intervals.

## Estimators

The area estimate should be based on the available reference classification for the pixels in the sample; so it is
essential to estimate the sample area (Stehman & Foody, 2019).

(in progress)

## Accuracy assessment

### Error matrix

The confusion matrix is the most widely used method for assessing accuracy. The matrix should remain a cornerstone of
the analysis protocol due to its ease of interpretation and valuable descriptive information. Typically, the map data
is arranged in rows and the reference data is arranged in columns in the matrix. The values arranged on the diagonal of
the confusion matrix indicate the degree of agreement between the two data sets.

This matrix is essential for the analysis of the area and variance estimators. The row and column totals of the
population error matrix are important because they quantify the distribution, by area, of different land cover classes.
The row totals represent the proportion of area of each class, according to the map classification. On the other hand,
the totals of the columns represent the proportion of area, according to the reference classification. Accuracy
assessment focuses on three types of analysis and parameters. The first at a global level, defined as general accuracy.
The second that focuses on the specific accuracy of the class and is classified as the accuracy of the user or the
producer. And, the third, which corresponds to the estimation of the proportion of area by a class.

> *About **Kappa**:* AcATaMa does not have the Kappa coefficient in the results, because in general we don't recommend
> to use it. The kappa coefficient is widely used as a measure of thematic accuracy in remote sensing. However,
> Foody (2020), Pontius and Millones (2011) have shown that the Kappa coefficient is not a good measure of accuracy.
> Pontius and Millones (2011) have argued that Kappa indices are redundant, useless, and/or flawed and should be
> abandoned because they do not provide any information helping in the purpose of accuracy assessment and map
> comparison. Foody (2020) said that while Kappa is a useful measure of agreement, it is not a good measure of accuracy.
> The kappa coefficient is an inappropriate index to use to describe classification accuracy.

### Accuracy

* **Overall accuracy**: The global accuracy has a direct interpretation in terms of area, since it represents the
  proportion of area correctly classified. Overall accuracy hides important information specific to each class. The
  limitation to overall accuracy is not how it weights or represents class-specific information, but rather that it
  does not provide class-specific information.

* **User's accuracy**: In it, the number of correctly classified sampling units (nii) in a class is divided by the total
  number of sampling units of that same class in the map (nk+). In this case, this accuracy is associated with the
  measurement of commission errors, which are defined as the inclusion of a map area in a land cover class in which that
  area should not be included.

* **Producer's accuracy**: Where the number of correctly classified sampling units (njj) in a class is divided by the
  total number of sampling units in the reference data n+j, for that class. Omission errors occur when an area is
  excluded on the map from the land cover class to which it should belong.

Errors of omission and errors of commission can be problematic to different degrees depending on the goals of a given
application of the map. Therefore, it is advisable to have separate estimates of user and producer accuracies. If
general measures are reported, they must be accompanied by specific measures of each class. In any case, the presented
formulas can only be applied if they evaluate the same map classes in the reference data. On the contrary, if other
classes are classified, it is advisable to use the formulas proposed by Stehman S. V. (2014). (Stehman S.V., 2014).
The variances of the general, user and producer accuracy are estimated with reference to the article Stehman & Foody,
2019

### Accuracy matrix of estimated area proportions

* **User´s accuracy matrix of estimated area proportion**: User´s accuracy is the proportion of the area mapped as a
  particular category that is actually that category "on the ground" where the reference classification is the best
  assessment of ground condition. User's accuracy is the complement of the probability of commission error (Olofsson
  et al. 2013). The user´s accuracy is calculated by the equation (2) in Olofsson et al. (2014). In the report, the
  user´s accuracy for each class or category correspond to the diagonal of the matrix, that means, the fields in
  which the class of the thematic map and the classified category (reference) are equals.

* **Producer´s accuracy matrix of estimated area proportion**: Producer's accuracy is the proportion of the area that is
  a particular category on the ground that is also mapped as that category. Producer's accuracy is the complement of the
  probability of omission error (Olofsson et al. 2013). The producer's accuracy is calculated by the equation (3) in
  Olofsson et al. (2014). In the report, the accuracy for each class or category correspond to the diagonal of the
  matrix, the fields in which the class of the thematic map and the classified category (reference) are equals.

### Error matrix of estimated area proportion

The absolute counts of the sample are converted into estimated area proportions using the equation (9) in Olofsson et
al. (2014) for post-stratification simple or systematic sampling or stratified sampling with the map classes defined as the
strata.

### Quadratic error matrix for estimated area proportion

Correspond to the standard error estimated by the equation (10) in Olofsson et al. (2014)

### Class area adjusted

The accuracy assessment serves to derive the uncertainty of the map area estimates. Whereas the map provides a single
area estimate for each class without confidence interval, the accuracy estimates adjusts this estimate and also provides
confidence intervals as estimates of uncertainty. The adjusted area estimates can be considerably higher or lower than
the map estimates (FAO, 2016).

The estimated area for each class or stratum and the standard error of the estimated area is given by the equation (11)
in Olofsson et al. (2014); they allow to obtain the confidence interval with the percent defined by the z-score value.
It is typically represented by confidence intervals, which indicate the range within which the true area proportions 
are expected to lie with a specified level of confidence, such as 95% (Z=1,96). Reporting these confidence intervals 
helps in understanding the potential error margins and ensures that the estimates are robust and transparent.

The coefficient of variation and uncertainty in the estimated area proportions table are metrics for assessing the 
reliability and precision of land cover or land change area estimates. The coefficient of variation is a 
standardized measure of the dispersion of the estimated area proportions, calculated as the ratio of the standard error 
to the mean estimate. It provides a relative measure of variability, indicating the extent of variability in relation 
to the mean, thus allowing for comparisons across different classes or studies. A lower CV indicates higher precision 
of the estimates. Uncertainty, on the other hand, encompasses the potential errors and variability inherent in the 
sampling design, classification accuracy, and reference data used for accuracy assessment. Quantifying this 
uncertainty is crucial as it measures the reliability and precision of the area estimates.

#### References

* Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for
  estimating area and assessing accuracy of land change. Remote Sensing of Environment, 148, 42-57.
* Stehman, S. V. (2014). Estimating area from an accuracy assessment of land cover. Remote Sensing of Environment, 148,
  42-57.
* Stehman, S. V., & Foody, G. M. (2019). Accuracy assessment: a user's perspective. CRC Press.
* FAO. (2016). Collect Earth: Land Use and Land Cover Assessment through Augmented Visual Interpretation. Rome, Italy:
  Food and Agriculture Organization of the United Nations.
* Pontius Jr, R. G., & Millones, M. (2011). Death to Kappa: birth of quantity disagreement and allocation disagreement
  for accuracy assessment. International Journal of Remote Sensing, 32(15), 4407-4429.
* Foody, G. M. (2020). Explaining the unsuitability of the kappa coefficient in the assessment and comparison of the
  accuracy of thematic maps obtained by image classification. Remote Sensing of Environment, 239, 111630.

Next >> [Examples](./examples)
