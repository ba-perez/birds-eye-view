# Bird’s-eye view: Remote sensing insights into the impact of mowing events on Eurasian Curlew habitat selection

This repository contains the code and related materials for the study titled "Bird’s-eye view: Remote sensing insights into the impact of mowing events on Eurasian Curlew habitat selection". It provides an overview of the project, the codebase, and how to reproduce the developed workflow for mowing event detection. It is intended to be an approachable, reproducible guide for researchers and non-experts working with optical remote sensing in environmental studies.

## Table of Contents
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Usage](#usage)

## Introduction

Eurasian Curlew populations are declining in Europe despite conservation efforts. By creating attractive regions of short vegetation, mowing practices could be used in conservation strategies to guide Curlews towards areas with a higher chance of survival. However, this potential cannot be assessed due to limited documentation on mowing dates. We developed a method for mowing event detection using optical data from four satellites: Landsat-7, Landsat-8, Sentinel-2, and Dove. The workflow builds a time series of NDVI values for each analysed grassland field by first filtering the satellites' image collections, applying the cloud masking techniques standard to each satellite, and merging their datasets. The NDVI values are normalised to the range (0, 1), remaining value interferences are removed by outlier detection via Isolation Forest, and value fluctuations are smoothed out with a Savistky-Golay-Filter. Our algorithm detects mowing dates based on a fixed threhsold for NDVI decreases and outputs a range of possible mowing dates representing the detected date ± 1 observation. Performance analysis of the devised workflow indicated 80% detection accuracy for trained data, and 84% accuracy for validation data.

The developed workflow provided insights into factors influencing Curlews’ field use throughout their breeding season and highlighted the significant impact of mowing events on their habitat choice, suggesting mowing strategies as an innovative conservation approach for the recovery of Curlew populations. The transferable methodology developed for detecting mowing events using optical satellites is present in this repository and can be used in studying small-scale, fast-paced dynamics in environmental research.

## Getting Started

The code used in this study is ran on Google Earth Engine (GEE) JavaScript and Python. Before you begin, make sure you have the following:

**1. Google Earth Engine account:** If you don't have one, sign up for a Google Earth Engine account at [earthengine.google.com](earthengine.google.com).

**2. Python environment:** make sure you have an environment that can run Python scripts. The code in this repository was written using Visual Studio Code, which can be installed from [code.visualstudio.com](code.visualstudio.com).

**3. Google Earth Engine Python API:** Install the Earth Engine Python API by following the instructions [here](https://developers.google.com/earth-engine/guides/python_install).

## Usage

The details about parameter setting are described in each script. 

The JavaScript code runs in the GEE code editor with out the need to install additional packages. Simply copy the desired code to your own repository.

The Python code requires the Google Earth Engine API, as described in [Getting Started](#getting-started), and additional modules which are listed at the beginning of each script. A guide to the installation of Python modules can be found [here](https://docs.python.org/3/installing/index.html).

## Code Structure

The scripts necessary for processing the satellite products and obtaining mowing dates are present below in the order to be executed.

1. [Landsat-7 preprocessing](https://github.com/ba-perez/birds-eye-view/blob/main/1_landsat-7-preprocessing.js)
2. [Landsat-8 preprocessing](https://github.com/ba-perez/birds-eye-view/blob/main/2_landsat-8-preprocessing.js)
3. [Sentinel-2 preprocessing](https://github.com/ba-perez/birds-eye-view/blob/main/3_sentinel-2-preprocessing.py)
4. [Dove preprocessing](https://github.com/ba-perez/birds-eye-view/blob/main/4_dove-preprocessing.py)
5. [Merge satellite products, normalise dataframe, split into training and validation](https://github.com/ba-perez/birds-eye-view/blob/main/5_merge_and_split.py)
6. [Apply Isolation Forest and Savitsky-Golay-filter](https://github.com/ba-perez/birds-eye-view/blob/main/6_IF_and_SG.py)
7. [Find cutting dates](https://github.com/ba-perez/birds-eye-view/blob/main/7_find_cutting_dates.py)


