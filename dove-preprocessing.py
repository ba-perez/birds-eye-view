#the following python modules need to be installed:
import rasterio
import numpy as np
from rasterio.plot import show
from scipy.ndimage import binary_dilation
from rasterio import plot
import os
import glob
import pandas as pd
import shapefile
from dbfread import DBF
import json

#define input and output directories
input_directory = r'C:\path\to\input\directory'
output_directory = r'C:\path\to\output\directory'

#function to mask batches of Planet (Dove) imagery
def process_image(img_file, udm2_file, output_directory):
    with rasterio.open(udm2_file) as src:
        shadow_mask = src.read(3).astype(bool)
        cloud_mask = src.read(6).astype(bool)
    mask = shadow_mask + cloud_mask

    buffer_size = 7
    mask_buffered = binary_dilation(mask, iterations=buffer_size)

    with rasterio.open(img_file) as src:
        profile = src.profile
        band_count = profile['count']
        work_data = src.read(list(range(1, band_count + 1)), masked=True) / 10000.0

    work_data.mask = mask_buffered
    masked_data = work_data.filled(fill_value=0)

    output_file = os.path.join(output_directory, f"{os.path.basename(img_file).split('.')[0]}_masked.tif")
    profile.update(count=masked_data.shape[0], dtype=str(masked_data.dtype))

    with rasterio.open(output_file, "w", **profile) as dst_idx:
        dst_idx.write(masked_data)

    print("Image processed successfully:", output_file)

def mask_all_images(input_directory, output_directory):
    udm2_files = glob.glob(os.path.join(input_directory, "*_udm2_clip.tif"))
    print("Files to be processed:", len(udm2_files))

    for udm2_file in udm2_files:
        img_prefix = os.path.basename(udm2_file).split("_udm2_clip.tif")[0]

        img_files = [
            f"{img_prefix}_AnalyticMS_SR_harmonized_clip.tif",
            f"{img_prefix}_AnalyticMS_SR_8b_harmonized_clip.tif",
            f"{img_prefix}_BGRN_SR_clip.tif"
        ]

        for img_file in img_files:
            full_img_path = os.path.join(input_directory, img_file)
            if os.path.exists(full_img_path):
                process_image(full_img_path, udm2_file, output_directory)
                break
        else:
            print(f"Warning: No corresponding image found for {udm2_file}.")

#apply function
mask_all_images(input_directory, output_directory)

#specify directories
masked_files = output_directory #directory with masked Dove images
metadata_files = r'C:\path\to\metadata\files' #metadata files delivered with Planet products
csv_path = r'C:\path\to\output\csv' #path for the output CSV files

#function to turn .dbf files into .csv
def process_dbf_files(masked_files, metadata_path, output_path):
    # Step 1: Locate metadata files
    metadata_files = glob.glob(os.path.join(metadata_path, "*_metadata.json"))

    for metadata_file in metadata_files:
        # Extract base name from the metadata file
        base_name = os.path.splitext(os.path.basename(metadata_file))[0]
        matching_key = '_'.join(base_name.split('_')[:-1])  # Get the matching key up to the last underscore

        # Step 2: Find the matching .dbf file in masked_files
        matching_dbf_file = None

        for dbf_file in os.listdir(masked_files):
            if matching_key in dbf_file and dbf_file.endswith(".dbf"):
                matching_dbf_file = os.path.join(masked_files, dbf_file)
                break

        if matching_dbf_file is not None:
            # Convert the .dbf file to a pandas DataFrame
            table = DBF(matching_dbf_file, encoding='utf-8')
            df = pd.DataFrame(iter(table))

            # Step 3: Add new columns to the DataFrame
            df["date"] = ""

            # Step 4: Extract "acquired" and populate date
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                acquired = metadata["properties"]["acquired"]
                df["date"] = acquired.split("T")[0]

            # Step 5: Filter and rename columns
            df = df[["date", "_median", "field_id"]]
            df = df.rename(columns={"_median": "NDVI"})

            # Step 6: Filter out rows where NDVI is null or missing
            df = df[df["NDVI"].notnull()]

            # Check if there are any rows left
            if not df.empty:
                # Step 8: Convert the DataFrame to CSV and save it
                csv_file = os.path.join(output_path, base_name + ".csv")
                df.to_csv(csv_file, index=False)
            else:
                print(f"No valid rows remaining for {base_name}, skipping CSV generation")

        else:
            print(f"No matching .dbf file found for {metadata_file}")

#apply function
process_dbf_files(masked_files, metadata_files, csv_path)

#function to merge CSV files from each image
def merge_csv_files(csv_dir):
    merged_df = pd.DataFrame()
    csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        merged_df = pd.concat([merged_df, df])
    merged_df = merged_df.reset_index(drop=True)
    return merged_df

#apply function
planet_raw = merge_csv_files(csv_path)

#clean CSV by:
#dropping rows w/ empty NDVI values
#calculating NDVI median for duplicate date-field_id combinations (multiple observations in one day)
unique_planet_raw = (
    planet_raw
    .dropna(subset = "NDVI")
    .groupby(['date', 'field_id'], as_index=False)[["NDVI", "cloud_cover"]]
    .median()
    .pipe(lambda x: x[[c for c in x if c != 'field_id'] + ['field_id']])
    .assign(sat_name='Planet')
)

#save merged, clean CSV
unique_planet_raw.to_csv(r'C:\path\to\clean_dove_dataset.csv', index=False)
