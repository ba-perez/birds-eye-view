#the following python modules need to be installed:
import pandas as pd
import glob
import os
import shapefile
from dbfread import DBF
import json

#specify directories
masked_files = r'C:\path\to\masked\images' #output from dove-preprocessing.js
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