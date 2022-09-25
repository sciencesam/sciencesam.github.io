---
layout: post
title:  "RTL-SDR X Band Radar"
date:   2020-03-20 14:11:01 -0500
tags: dsp radar challenge paper
---
Concept I developed for using an RTL-SDR combined with a TV Downconverter to make an cooprative radar. 
<!-- excerpt-end -->
I submitted the [paper](/_files/Cheap X-Band Radar based on RTL-SDR and TV Downconverters.pdf) for the [2020 IEEE Radar Challenge][challenge-news-link].

![Color Image Example](/_img/rtl-sdr-reciever.PNG)

*Figure 1 System Overview*

The idea is to combine multiple RTL-SDRs together to make a coherent reciever. Something like [Kerberos SDR](https://othernet.is/products/kerberossdr-4x-coherent-rtl-sdr) could be used to make this coherent reciever. 

RTL-SDR is only operates in from 0 to 1.7GHz, so the 10GHz signal is downconverted using a [satellite LNB](https://ok2zaw.blogspot.com/2019/02/10ghz-lnb.html). A VCO generates the 10GHz waveforms and the direct path (or direct into the reciever) signal is used as reference. 

[challenge-news-link]: https://ieee-aess.org/radar-challenge/radar-challenge-washington