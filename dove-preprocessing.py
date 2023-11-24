#the following python modules need to be installed:
import rasterio
import numpy as np
from rasterio.plot import show
from scipy.ndimage import binary_dilation
from rasterio import plot
import os
import glob

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