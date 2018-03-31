# How to use

AcATaMa is divided and ordered by four tabs/sections:

1. [Thematic](#1-thematic-map)
2. [Sampling](#2-sampling-desing)
3. [Classification](#3-classification)
4. [Accuracy Assessment](#4-accuracy-assessment)

<img src="../img/dock_main.png" width="40%">

At the bottom of the plugin there are 3 buttons:

- `Docs` for open the CloudMasking documentation online in a web-browser
- `Clear/Reload` for clear all temporal and used files for process and reset all fields in the plugin
- `AcATaMa version` open the about dialog.

## 1. Thematic map

The `Thematic` section you can set the thematic map (needed for some process, see more in [use cases](use_cases.md)).

Optionally you can clip the thematic raster selected in an area of interest. After clipping the new thematic raster cut is automatically loaded.

<img src="../img/1a.png" width="100%">

!!! warning "Important!"
    Clip the thematic map in an area of interest (or load the thematic map clipped) can be (or not) very important for the sampling design and the accuracy assessment result, because the area by classes changes and some parts of AcATaMa depend on the area by classes.

### Types of thematic rasters accepted in AcATaMa

It must be a categorical thematic layer **with byte or integer as data type** with a specific pixel-value/color associated. There are two types, respect to pixel-value/color associated, accepted in AcATaMa:

1. **Raster with pseudocolor style**:

    You can use any raster (of byte or integer as data type) with specific style so that AcATaMa acquire the categorical information from the raster. Go to `properties` of the raster, then go to `style`, select `singleband pseudocolor` and generate the desired pixel-value/color associated (manually or generated automatically using the several options that Qgis have to do this) with only one requirement: **the pixel-values associated must be integers**.

    <img src="../img/1b.png" width="90%">

    (Optional) After configure the style in Qgis for the raster is recommended save it in `.qml` Qgis style file, else Qgis save it in temporal file (or on the fly) and if you restart the Qgis and load the raster again you lost the pixel-value/color style associated. For save the style go to `Style` menu and click in `Save as default` Qgis save it in the same place and name of the raster with extension `.qml`.

    <img src="../img/1c.png" width="65%">

    (Optional) Alternative (or additional) to the above, you can save all layers style and config saving it in a Qgis project.

2. **Raster with color table**:

    You can use any raster (of byte or integer as data type) with pixel-values/color associated through a color table inside it as metadata. You can see it using `gdalinfo` or in `style` in layer `properties` this is shown as `paletted`.

    <img src="../img/1d.png" width="65%">

!!! note
    The thematic map is the raster layer to which the accuracy assessment will be applied (for example a land cover map) and also is the base to generate the random sampling.

## 2. Sampling desing

The sampling design defines how to select the sampled for the accuracy assessment (or any others uses). The `Sampling` section you can make and design the sampling using two categories for that: `Simple Random Sampling` and `Stratified Random Sampling`:

### Simple Random Sampling

In the `simple random sampling`, every points (each x, y coordinates combination) has an equal chance of being selected. The size sample (number of points) that you define (Field: *"Number of samples"*), will be created pick randomly coordinates into the area of the thematic map, without taking into account the class or category to which it belongs. You can restrain the sites where the points will be crated with the follow options:

* Indicating the value in the thematic raster of the No Data pixels (Tab: *"Thematic"*), AcATaMa will not generate point on these pixels
* Selecting the classes in the thematic raster. If you define some classes in the: *"Tab Sampling / Simple Random Sampling / Sampling in categorical raster"* (Field: "Set pixel values") AcATaMa only will create points into the pixels that belongs to these classes

<img src="../img/2a.png" width="70%">


### Stratified Random Sampling

In the `stratified random sampling` you divide the area of interest into smaller areas (strata), with a specific number of samples for each stratum. The strata need to be mutually exclusive and inclusive of the entire study area (FAO, 2016).

According to Olofsson et al. (2013, 2014), the stratiﬁcation is recommended to improve the precision of the accuracy and area estimates. When strata are created for the objective of reporting accuracy by strata, the stratiﬁed design allows ensuring that a precise estimate is obtained for each stratum. In this way, a land change or other category that occupies a small proportion of the landscape can be identiﬁed and the sample size allocated to this stratum can be large enough to produce a small standard error for the user's accuracy estimate.

In the basic case, each stratum could be a class or category of the thematic map; for this option you should select the thematic raster in the drop-down menu in *"Categorical raster"* block. If you want generate a stratified sample using other criteria (geographical sub-regions for example), you have to include an additional thematic raster layer with classes representing the strata and select it in the drop-down menu.


The stratified random may be:

- `Stratified random sampling using a fixed number of sample`: The sample size for each stratum is defined by the user. In the table selecting the option *"Fixed values by category (manually)"* in *"stratified random Sampling Method"*, you can write the number of points desired for each stratum. If you do not want set points in any stratum, you should write 0.

    <img src="../img/2b.png" width="70%">

- `Stratified random sampling using area based proportion`: Designed to apply the proportional approaches sample allocations methodologies suggested by Olofsson et al. (2013, 2014), using the Cochran´s (1977) sample size formula for stratified random sampling in the option *"Area based proportion using std error"* in *"stratified random Sampling Method"*. The overall sample size and the number of point for each stratum is calculated according to:

    - The area proportion of each stratum in the map (Wi): This is automatically calculated by AcATaMa. You can see the Wi values in the table of accuracy assessment results
    - The standard error of the estimated overall accuracy that we would like to achieve. You write the value desired in the Field: "Overall expected standard error"
    - Standard deviation of each stratum: You define the values in the table

    <img src="../img/2c.png" width="70%">

If you want to define a specific sample size for one or more stratum, you can write it in the table and AcATaMa will modify the number of points in the others strata proportionally to the area, in order to keep the overall sample size; this allow perform the simplified approach of sample size allocation suggested by Olofsson et al.(2014), in which you define a specific sample size for the rare classes and the remain samples is allocated proportionally to the area of each other strata. If you want allocate a equal size sample for all strata, you can use this option to calculate the overall sample size, and assigning the number of points in each stratum in the Fixed values by category (manually) option.

You can *"turn off"* strata by deselecting in the last column of the table (*"On"*); these strata will not be taking into account to calculate the proportion of the area (Wi) or the sample size.

### Sampling options

Optionally, in any type of sampling you can restrain the allocation of the points according to these criteria::

<img src="../img/2d.png" width="45%">

 - In `Sampling options` you can set the minimum distance between the point generated respect to all points generated (in meters)
 - In `With neighbors aggregation` you can set the number of nearest neighbors pixels that belong to the same class:
    - *Number of neighbors*: It is the number of neighbors that AcATaMa evaluate to decide if a point can be included or not in the sample
    - *Min neighbors with the same class*: It is the minimum number of neighbors (according to the number of neighbors selected above) that must belong to the same class so that a point can be included in the sample

### Other options

Both `Simple Random Sampling` and `Stratified Random Sampling` at bottom has the following options:

<img src="../img/2e.png" width="45%">

 - `Generate sampling options`: Set the number of attempts for to do the sampling, the difficulty of making the sampling depend on some conditions suck as; minimum distance, neighbors aggregations, total number of samples and the area for do this.
 - `Save sampling config`: Save in a plain text (ini format) all configuration with which the sampling was generated, it is only information for the user such as metadata for the sampling generated, this does not work for load the sampling config in the AcATaMa.

## 3. Classification

For the classification follow these steps:

* In `Classification` tab select the sampling file
* Set the `Grid setting` it depends on the number of images to compare
* Click in `Open the classification dialog`

<img src="../img/3a.png" width="70%">

### Classification dialog

For the classification follow these steps (in classification dialog):

* Select/browse the images in views, set the scale factor, name, etc.
* Set the `fit to sample`, you can test it clicking in `current sample`
* Set all classification buttons in `Set Classification`
* Now you can classified the samples with the buttons created

<img src="../img/3b.png" width="100%">

!!! note "Nota: Samples order"
    For the classify the samples AcATaMa shuffles the list of samples for each file (the samples ID are not in order), this is to ensure randomization in the classification.

#### Configuration buttons

The configuration buttons dialog you can set all buttons for classify the samples, you can set the name, the color and (optionally) the thematic raster class.

- `Without thematic raster classes`: You must define the classification name and the color (the color is not mandatory). This configuration is for some case of use like as sampling design and others that don't need the thematic raster.

    <img src="../img/3c.png" width="40%">

- `With thematic raster classes`: You must define the classification name, thematic raster class and the color, the color is auto filled when you pick the thematic raster class, after that you can change it if you want.

    <img src="../img/3d.png" width="60%">

!!! warning "Important!"
    The column `Thematic raster class` is available only if you set the thematic raster in [Thematic](#1-thematic) tab before open the dialog. You must configure the thematic raster class for all buttons if you want accuracy assessment result.


## 4. Accuracy Assessment

<img src="../img/4a.png" width="40%">

Accuracy is defined as the degree to which the map produced agrees with the reference classification.

<img src="../img/4b.png" width="80%">

AcATaMa calculated the accuracy assessment using the formulas included in Olofsson et al. (2013, 2014), the results are presented in five tables:


1. `Error Matrix`: The error matrix is a cross-tabulation of the class labels allocated by the classification of the remotely sensed data against the reference data (thematic map) for the sample sites. The main diagonal of the error matrix highlights correct classifications while the off-diagonal elements show omission and commission errors. The values of the error matrix are fundamental to both accuracy assessment and area estimation Olofsson et al. 2014). The column Wi is the area proportion of each stratum in the map.

    <img src="../img/4c.png" width="75%">

2. `Error matrix of estimated area proportion`: The absolute counts of the sample are converted into estimated area proportions using the equation (9) in Olofsson et al. (2014) for simple random, systematic or stratified random sampling with the map classes defined as the strata.

    <img src="../img/4d.png" width="35%">

3. `Quadratic error matrix for estimated area proportion`: Correspond to the standard error estimated by the equation (10) in Olofsson et al. (2014)

    <img src="../img/4e.png" width="35%">

4. `Accuracy Matrices`:

    * `User´s accuracy matrix of estimated area proportion`: User´s accuracy is the proportion of the area mapped as a particular category that is actually that category "on the ground" where the reference classification is the best assessment of ground condition. User's accuracy is the complement of the probability of commission error (Olofsson et al. 2013). The user´s accuracy is calculated by the equation (2) in Olofsson et al. (2014). In the report, the user´s accuracy for each class or category correspond to the diagonal of the matrix, that means, the fields in which the class of the thematic raster map and the classified category (reference) are equals.

        <img src="../img/4f.png" width="35%">

    * `Producer´s accuracy matrix of estimated area proportion`: Producer's accuracy is the proportion of the area that is a particular category on the ground that is also mapped as that category. Producer's accuracy is the complement of the probability of omission error (Olofsson et al. 2013). The producer's accuracy is calculated by the equation (3) in Olofsson et al. (2014). In the report, the accuracy for each class or category correspond to the diagonal of the matrix, the fields in which the class of the thematic raster map and the classified category (reference) are equals.

        <img src="../img/4g.png" width="35%">

    * `Overall accuracy`: Is the proportion of the area mapped correctly. It provides the user of the map with the probability that a randomly selected location on the map is correctly classified (Olofsson et al. 2013). It is important use carefully this value because the overall map accuracy is not always representative of the the accuracy of the individual classes or strata (FAO, 2016). The overall map accuracy is calculated by the equation (1) in Olofsson et al. (2014)


5. `Classes area adjusted table`: The accuracy assessment serves to derive the uncertainty of the map area estimates. Whereas the map provides a single area estimate for each class without confidence interval, the accuracy estimates adjusts this estimate and also provides confidence intervals as estimates of uncertainty . The adjusted area estimates can be considerably higher or lower than the map estimates (FAO, 2016).

    The estimated area for each class or stratum and the standard error of the estimated area is given by the equation (11) in Olofsson et al. (2014); they allow to obtain the confidence interval with the percent defined by the z-score value. By default AcATaMa calculate a 95% confidence interval (Z=1,96), but you can modify the z- score value according to the desired percent (Settings options in the report of results).

    <img src="../img/4h.png" width="35%">

## References

+ *Cochran, W. G., 1977. Sampling techniques. John Wiley & Sons. New York.*
+ *FAO. 2016. Map accuracy assessment and area estimation. A practical guide. National forest monitoring assessment working paper No.46/E. Rome. [Link](http://www.fao.org/3/a-i5601e.pdf)*
+ *Olofsson, P., Herold, M., Stehman, S. V., Woodcock, C. E. & , M. A. Wulder. 2014. Good practices for estimating area and assessing accuracy of land change. Remote Sensing of Environment, 148:42–57. [Link](https://www.sciencedirect.com/science/article/pii/S0034425714000704)*
+ *Olofsson, P., Foody, G. M., Stehman, S. V. & C. E. Woodcock. 2013. Making better use of accuracy data in land change studies: Estimating accuracy and area and quantifying uncertainty using stratified estimation. Remote Sensing of Environment, 129:122–131. [Link](https://www.sciencedirect.com/science/article/pii/S0034425712004191?via%3Dihub)*