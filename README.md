# Bird’s-eye view: Remote sensing insights into the impact of mowing events on Eurasian Curlew habitat selection

This repository contains the code and related materials for the study titled "Bird’s-eye view: Remote sensing insights into the impact of mowing events on Eurasian Curlew habitat selection". It provides an overview of the project, the codebase, and how to reproduce the developed workflow for mowing event detection. It is intended to be an approachable, reproducible guide for researchers and non-experts working with optical remote sensing in environmental studies.

## Table of Contents
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Introduction

Eurasian Curlew populations are declining in Europe despite conservation efforts. By creating attractive regions of short vegetation, mowing practices could be used in conservation strategies to guide Curlews towards areas with a higher chance of survival. However, this potential cannot be assessed due to limited documentation on mowing dates. We developed a method for mowing event detection using optical data from four satellites: Landsat-7, Landsat-8, Sentinel-2, and Dove. The workflow builds a time series of NDVI values for each analysed grassland field by first filtering the satellites' image collections, applying the cloud masking techniques standard to each satellite, and merging their datasets. The NDVI values are normalised to the range (0, 1), remaining value interferences are removed by outlier detection via Isolation Forest, and value fluctuations are smoothed out with a Savistky-Golay-Filter. Our algorithm detects mowing dates based on a fixed threhsold for NDVI decreases and outputs a range of possible mowing dates representing the detected date ± 1 observation. Performance analysis of the devised workflow indicated 80% detection accuracy for trained data, and 84% accuracy for validation data.

The developed workflow provided insights into factors influencing Curlews’ field use throughout their breeding season and highlighted the significant impact of mowing events on their habitat choice, suggesting mowing strategies as an innovative conservation approach for the recovery of Curlew populations. The transferable methodology developed for detecting mowing events using optical satellites is present in this repository and can be used in studying small-scale, fast-paced dynamics in environmental research.

## Getting Started

The code used in this study is ran on Google Earth Engine Javascript and Python. Before you begin, make sure you have the following:

**1. Google Earth Engine account:** If you don't have one, sign up for a Google Earth Engine account at earthengine.google.com.

**2. Google Earth Engine Python API:** Install the Earth Engine Python API by following the instructions [here - WIP].

**3. Python environment:** make sure you have an environment that can run Python scripts. The code in this repository was written using Visual Studio Code, which can be installed from code.visualstudio.com.

## Usage

Step-by-step instructions on how to use the code.Link to each script in order:

1. Image Preprocessing...

