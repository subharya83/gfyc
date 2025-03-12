#!/bin/bash

# Base URL
base_url="https://www.irs.gov/pub/irs-soi"

countyoutflow1112.csv

# Loop over the range of XX values
for XX in {11..21}; do
    # Calculate YY as XX + 1
    YY=$((XX + 1))

    # Construct the file names
    inflow_file="countyinflow${XX}${YY}.csv"
    outflow_file="countyoutflow${XX}${YY}.csv"

    # Construct the full URLs
    inflow_url="${base_url}/${inflow_file}"
    outflow_url="${base_url}/${outflow_file}"

    # Download the files
    wget "$inflow_url"
    wget "$outflow_url"
done
