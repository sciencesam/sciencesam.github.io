---
layout: post
title:  "Color Based Musical Instrument"
date:   2018-03-23 14:11:01 -0500
tags: dsp paper sensors conference
---
I presented my paper "The Development of a Color-based Musical Instrument" at the 2018 IEEE R1 Student Conference.
<!-- excerpt-end -->
The [conference](https://site.ieee.org/r1-sac/r1-student-conference/r1-student-conference2018-ieee-r1-student-conference/) was hosted at the New York Institute of Technology, on Long Island. 

 [The paper](/_files/Stone_Samuel_180308_Color_Instrument.pdf) is  based on my work with Dr. Craver. We wanted to create a musical instrument that allows a user to point at the color of a surface and generate a unique tone. You could make any surface into an instrument or create any instrument you want by printing off different colors of paper. 

![Color Image Example](/_img/color_image_example.PNG)

*Figure 1 Color Image with Saturation thresholds*

Pictures of the surface are taken with a RaspberryPi cameras enclosed in a shrowd. The shrowd lights the surface and allows you to select what part of the surface to sample. 

![HSV Color Space](/_img/hsv_color_space.png)

*Figure 2 HSV Color Space*

The RGB color space samples from the camera are converted to the HSV color space. In HSV, the base color "hue" is a single angle from 0-360 degrees. In order to a tone to the color, we only need to estimate what this angle is and then map angles to tones. 

![Color Distribution](/_img/color_distro.PNG)

*Figure 3 Circular Color Distribution*

By only capturing pixels where the saturation is above a certain threshold, we can easily both isolate the sample region and eliminate any glare caused by the led lights. A saturation threshold is also used to filter out when the surface isn't colorful enough to estimate.  

![Possible Estimates](/_img/88_key_mle.PNG)

*Figure 4 88 Key MLE*

We use the [Von Mises distribution](https://en.wikipedia.org/wiki/Von_Mises_distribution) to derive our maximum likelihood estimator. Von Mises is a circular normal distribution. The possible colors are broken up into 88 discrete tones, based on the 88 tones on a piano, and MLE is used to estimate which tone to assign the sample. 

