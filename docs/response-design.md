---
layout: default
---

# Response Design

<img src="img/response_design.webp" width="100%" style="margin: auto;display: block;">

The responsive design is defined as the protocol for determining the baseline classification at the selected sample
sites (Olofsson, et al., 2014). Conceptually it is useful to separate the response design into two components:

<img src="img/response_design_components.png" height="200px" style="margin: auto;display: block;">

**A)** The evaluation protocol with the procedures used to gather information that contributes to the determination of
the reference classification.

<img src="img/response_design_part_A.webp" width="85%" style="margin: auto;display: block;">

### Sampling unit

The sampling unit is a structure that defines a specified space that defines the basis for the comparison of the
thematic map and reference data and with that defines the space for labeling protocol. The sampling unit in an accuracy
assessment protocol is crucial because it determines how the landscape is partitioned and represented, influencing the
measurement of agreement and disagreement between the map and reference data. When a single pixel is used as the spatial
unit, a critical decision must be made regarding the labeling process—whether to assign labels based solely on what is
observed within each individual pixel or to consider the surrounding context. (Stehman and Czaplewski, 1998)

When using blocks of pixels (e.g., a 3x3 pixel block) as the sampling unit, the surrounding area is considered, which
can reduce sensitivity to geo-referencing errors, smooth out small-scale misalignment's, and provide a more accurate
representation of the land cover. However, blocks can introduce heterogeneity within the sampling unit, which could
complicate analysis. On the other hand, pixel-based sampling units are better suited for very detailed assessments. 
(Stehman and Wickham, 2011)

There is not a universally "best" spatial assessment unit for accuracy assessment in thematic maps. The choice should be
based on the specific needs of the assessment. If minimizing location errors is critical, a larger unit like a block of
pixels might be preferred. If precision and detail are more important, pixel-based assessments might be the best option.

### Reference data

Collection of reference observations or other types of data sources characterized as having the most accurate available
assessment of the "true" condition at the sample location, and with the help of the sampling unit space and the
expertise of the evaluator, to contribute to the reference classification determination and the labeling protocol.

**B)** The labeling protocol that implies the classification of the sampling unit based on the information obtained from
the evaluation protocol (Stehman & Czaplewski, 1998).

### Reference classification

Available assessment of the condition of a population unit. The classes available come from the thematic map, the
evaluator must select the reference classes as a labeling buttons using the "Labeling setup" option in AcATaMa.

<img src="img/labeling_buttons_setup.webp" width="75%" style="margin: auto;display: block;">

### Labeling protocol

The labeling protocol assigns a label from the reference classification (through labeling buttons) to the sampling unit,
supported by the reference data and the evaluation protocol.

<img src="img/response_design_evaluation.webp" width="85%" style="margin: auto;display: block;">

### Evaluation protocol

Procedures used to define a class from the reference classification to a sampling unit based on the space of the
sampling unit and the experience of the evaluator with the help of reference data and observations.

At most of the cases (and recommend) the evaluation protocol use the reference classification to apply to the sampling
unit and its space and not only to the sample itself (as a point unit). In some cases, the evaluator may visually scan
the sampling unit and record qualitative observations that contribute to an eventual classification of the sampling
unit. In other cases, the assessment protocol may specify the recording of species composition, canopy closure, or 
tree size distribution, or require other quantitative data necessary to distinguish the reference classification for 
that sampling unit (Stehman & Czaplewski, 1998).

### Keyboard Shortcuts

The following keyboard shortcuts are available in the Response Design Window to facilitate quick navigation between 
samples, zoom in/out, and label buttons:

#### Sample Navigation

- Left/Right Arrow Key: Navigate to the previous/next sample
- Ctrl + Left/Right Arrow Key: Navigate to the previous/next unlabeled sample
- Up/Down Arrow Key: Zoom in/out in all active view widget canvases

#### Labeling Button Keyboard Shortcuts

AcATaMa supports custom keyboard shortcuts for labeling buttons to improve efficiency during the labeling process.

<img src="img/labeling_button_shortcuts.webp" width="40%" style="margin: auto;display: block;">

- Supported: letters, numbers, function keys, and combinations with Ctrl, Alt, Shift, or Meta.

> <span style="color:orange">WARNING!</span>  
> Avoid using keys or key combinations that are already assigned by your operating system or QGIS to prevent shortcut conflicts.

Next >> [Analysis](./analysis)
