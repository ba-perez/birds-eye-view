#the following python modules need to be installed:
import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import re
import random

#functions for minmax normalisation
def extract_region(field_id):
    #extract region code from the field_id
    #KM, LM, AL in this study
    match = re.match(r'^(KM|LM|AL)', field_id)
    if match:
        return match.group()
    return None

def normalise_columns_byYear_Region(df):
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df['year'] = df['date'].dt.year
    
    normalised_df = df.copy()
    
    #extract region from field_id and create a new column 'region'
    normalised_df['region'] = df['field_id'].apply(extract_region)
    
    groups = normalised_df.groupby(['year', 'region'])

    column = 'NDVI'
    scaler = MinMaxScaler()

    column_values = groups[column].transform(
        lambda x: scaler.fit_transform(x.values.reshape(-1, 1)).flatten() if x.notnull().any() else x
    )
    
    normalised_df[column] = column_values

    return normalised_df

#function to clean date-field_id duplicates in dataframe
#usually from overlapping observations
#prioritising specific satellites
def clean_duplicates(df):
    minmax_duplicates = df.duplicated(subset=['date', 'field_id'], keep=False)

    selected_duplicates = df[(minmax_duplicates) & (df['sat_name'] == 'Sen2')]
    if selected_duplicates.empty:
        selected_duplicates = df[(minmax_duplicates) & (df['sat_name'] == 'Planet')]
        if selected_duplicates.empty:
            selected_duplicates = df[(minmax_duplicates) & (df['sat_name'] == 'Lan8')]
            if selected_duplicates.empty:
                selected_duplicates = df[minmax_duplicates]

    clean_df = pd.concat([df[~minmax_duplicates], selected_duplicates])

    sat_name_column = clean_df.pop('sat_name')
    clean_df = clean_df.assign(sat_name=sat_name_column)

    clean_df = clean_df.reset_index(drop=True)

    return clean_df

#function to merge all observations from one satellite into a single csv file
#to be used if each satellite has observations split into several csv files
def combine_csv_files(input_directory, output_directory, sat_name):
    dfs = []
    
    for filename in os.listdir(input_directory):
        if filename.endswith(".csv"):
            file_path = os.path.join(input_directory, filename)
            df = pd.read_csv(file_path)
            dfs.append(df)
    
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df['sat_name'] = sat_name
        
        output_filename = os.path.join(output_directory, f"{sat_name}_complete.csv")
        combined_df.to_csv(output_filename, index=False)
        print(f"Combined CSV file saved to '{output_filename}'")
        
        return combined_df
    else:
        print("No CSV files found in the directory.")
        return None

#function to check if any duplicates remain
def check_duplicates(df):
    duplicate_rows = df[df.duplicated(['date', 'field_id'], keep=False)]
    if not duplicate_rows.empty:
        print("Duplicate date-field_id combinations found:")
        print(duplicate_rows)
    else:
        print("No duplicate date-field_id combinations found.")

#prepare Lan7 dataset for merging
landsat7_raw = combine_csv_files(
    r'input\path\to\lan7\csv\fragments',
    r'output\path\to\merged\lan7\csv',
    "Lan7"
    )

#convert 'date' column to datetime and sort by date
landsat7_raw = (
    landsat7_raw
    .pipe(lambda x: x.assign(date=pd.to_datetime(x['date'])))
    .sort_values('date')
)

#columns containing band and index values
landsat7_column_range = list(landsat7_raw.columns[1:14])

#drop rows with NA values in the specified columns, rename columns, and select columns
landsat7_processed = (
    landsat7_raw
    .dropna(subset=landsat7_column_range)
    .rename(columns={"Satellite": "sat_name"})
    .loc[:, ["date", "NDVI", "field_id", "sat_name"]]
)

#check for duplicate timestamps by field ID
check_duplicates(landsat7_processed)

#check for remaining empty NDVI values
print("Number of NA values in L7 NDVI column:", landsat7_processed['NDVI'].isna().sum())

landsat7_processed.info()

#prepare Lan8 dataset for merging
landsat8_raw = combine_csv_files(
    r'input\path\to\lan8\csv\fragments',
    r'output\path\to\merged\lan8\csv',
    "Lan8"
    )

#convert 'date' column to datetime and sort by date
landsat8_raw = (
    landsat8_raw
    .pipe(lambda x: x.assign(date=pd.to_datetime(x['date'], format = "%d/%m/%Y")))
    .sort_values('date')
)

#columns containing band and index values
landsat8_column_range = list(landsat8_raw.columns[1:14])

#drop rows with NA values in the specified columns, rename columns, and select columns
landsat8_processed = (
    landsat8_raw
    .dropna(subset=landsat8_column_range)
    .rename(columns={"Satellite": "sat_name"})
    .loc[:, ["date", "NDVI", "field_id", "sat_name"]]
)

#check for duplicate timestamps by field ID
check_duplicates(landsat8_processed)

#check for remaining empty NDVI values
print("Number of NA values in L8 NDVI column:", landsat8_processed['NDVI'].isna().sum())

landsat8_processed.info()

#prepare Planet dataset for merging
#for this satellite, only load table, convert 'date' column to datetime and sort by date
#other processes already occurred in previous scripts
planet_processed = (
    pd.read_csv(r'path\to\planet\csv')
    .pipe(lambda x: x.assign(date=pd.to_datetime(x['date'])))
    .sort_values('date')
)

#check for duplicate timestamps by field ID
check_duplicates(planet_processed)

#check for remaining empty NDVI values
print("Number of NA values in Planet NDVI column:", planet_processed['NDVI'].isna().sum())

planet_processed.info()

#prepare Sen2 dataset for merging
sentinel2_raw = combine_csv_files(
    r'input\path\to\sen2\csv\fragments',
    r'output\path\to\merged\sen2\csv',
    "Sen2"
    )

#convert 'date' column to datetime and sort by date
sentinel2_raw = (
    sentinel2_raw
    .pipe(lambda x: x.assign(date=pd.to_datetime(x['date'])))
    .sort_values('date')
)

#columns containing band and index values
sentinel2_column_range = list(sentinel2_raw.columns[1:21])

#drop rows with NA values in the specified columns, rename columns, and select columns
#calculate median of duplicate "date" and "field_id" groups
#since sen2 had repeated daily observations for our study areas
sentinel2_processed = (
    sentinel2_raw
    .dropna(subset=sentinel2_column_range)
    .groupby(['date', 'field_id'], as_index=False)[sentinel2_raw.columns[1:22]]
    .median()
    .pipe(lambda x: x[[c for c in x if c != 'field_id'] + ['field_id']])
    .assign(sat_name="Sen2")
    .loc[:, ["date", "NDVI", "field_id", "sat_name"]]
)

#check for duplicate timestamps by field ID
check_duplicates(sentinel2_processed)

#check for remaining empty NDVI values
print("Number of NA values in S2 NDVI column:", sentinel2_processed['NDVI'].isna().sum())

sentinel2_processed.info()

#merge processed dataframes
def merge_dfs(dataframes_list):
    merged_df = pd.concat(dataframes_list, ignore_index=True)
    unique_df = merged_df.drop_duplicates(subset=['date', 'field_id'], keep='first')
    sorted_df = unique_df.sort_values(by=['date', 'field_id'])
    return sorted_df

#define list of dfs to merge
#order matters for hierarchy of timestamps to be kept in case of duplicate dates
input_list = [sentinel2_processed, planet_processed, landsat8_processed, landsat7_processed]

merged_satellites = merge_dfs(input_list)

#check for duplicate timestamps by field ID
check_duplicates(merged_satellites)

print("Final df length:", len(merged_satellites))

unique_combinations = (
    merged_satellites
    .pipe(lambda df: df.assign(date=pd.to_datetime(df['date'], format='%d/%m/%Y')))
    .assign(year=lambda df: df['date'].dt.year)
    .groupby(['year', 'field_id'])
    .size()
    .reset_index(name='count')
    .drop(columns=['year'])
)

print("Unique year-field_id combinations:", len(unique_combinations))

#remove unrealistic NDVI values to prevent skewed normalisation
merged_satellites_filtered = merged_satellites[merged_satellites['NDVI'] > 0]

#normalise merged df
normalised_merged_satellites = normalise_columns_byYear_Region(merged_satellites_filtered).drop(['year', 'region'], axis=1)

normalised_merged_satellites.info()

#function to create training and validation datasets
#with a random 80/20 split
def generate_train_validation_data(dataframe, seed=42):
    #set the seed
    random.seed(seed)

    #assign group numbers to each combination of field_id and year
    dataframe['group_nr'] = dataframe.groupby(['field_id', pd.to_datetime(dataframe['date']).dt.year]).ngroup()

    #determine the number of groups for training data
    num_train_groups = int(dataframe['group_nr'].nunique() * 0.8)

    #group dataframe by 'group_nr'
    field_groups = dataframe.groupby('group_nr')

    #shuffle the group_nrs
    group_nrs = list(field_groups.groups.keys())
    random.shuffle(group_nrs)

    #initialise train and validation groups
    train_groups = []
    validation_groups = []

    #split data into train and validation groups
    for group_nr in group_nrs:
        group = field_groups.get_group(group_nr)
        if len(train_groups) < num_train_groups:
            train_groups.append(group)
        else:
            validation_groups.append(group)

    #concatenate train and validation groups into train and validation data
    training_data = pd.concat([pd.DataFrame(group, columns=dataframe.columns) for group in train_groups])
    validation_data = pd.concat([pd.DataFrame(group, columns=dataframe.columns) for group in validation_groups])

    return training_data, validation_data

#apply function to merged and normalised df
training_data, validation_data = generate_train_validation_data(normalised_merged_satellites)

training_data.info()
validation_data.info()

#function check validity of training/validation split
def check_split_validity(training_df, validation_df, source_df):
    training_df_combinations = set(zip(training_df['date'], training_df['field_id']))
    validation_df_combinations = set(zip(validation_df['date'], validation_df['field_id']))

    common_combinations = training_df_combinations.intersection(validation_df_combinations)
    is_sum_equal_df = len(training_df) + len(validation_df) == len(source_df)

    def calculate_unique_df(input_df):
        unique_df = (
            input_df
            .pipe(lambda df: df.assign(date=pd.to_datetime(df['date'], format='%d/%m/%Y')))
            .assign(year=lambda df: df['date'].dt.year)
            .groupby(['year', 'field_id'])
            .size()
            .reset_index(name='count')
            .drop(columns=['year'])
        )
        return unique_df

    unique_training = calculate_unique_df(training_df)
    unique_validation = calculate_unique_df(validation_df)
    unique_source = calculate_unique_df(source_df)

    is_sum_combinations_equal = (
        len(unique_training) + len(unique_validation) == len(unique_source)
    )

    if is_sum_combinations_equal and is_sum_equal_df and not common_combinations:
        return "Split is valid"
    else:
        return "Split is not valid"

#apply function
check_split_validity(training_data, validation_data, normalised_merged_satellites)

#save training and validation dataif wished
training_data = training_data.drop('group_nr', axis=1)
validation_data = validation_data.drop('group_nr', axis=1)

training_data.to_csv(r'path\to\training\csv', index=False)
validation_data.to_csv(r'path\to\validation\csv', index=False)
