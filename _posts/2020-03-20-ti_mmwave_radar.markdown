---
layout: post
title:  "TI mmWave Radar"
date:   2020-03-20 14:11:01 -0500
tags: dsp radar challenge paper
categories: grok
---
Concept I developed for with our team at SRC, using an automotive radar as a teaching aid
<!-- excerpt-end -->
I submitted the [paper](/_files/Low Cost COTS Radar.pdf) for the [2020 IEEE Radar Challenge][challenge-news-link].

The idea was to use the LVDS interface on a [mmWave automotive radar](https://www.ti.com/tool/IWR1843BOOST) from Texas Instruments to stream data to an Ultrascale FPGA + ARM CPU. The FPGA would read data in from the radar and DMA it to memory to processing on the CPU. The CPU would run Radar signal processing techniques, allowing us to quiclky demonstrate different techniques. 

[challenge-news-link]: https://ieee-aess.org/radar-challenge/radar-challenge-washington