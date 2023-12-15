#the following python modules need to be installed:
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from sklearn.ensemble import IsolationForest
import os
from scipy import signal

#load training and validation datasets
#validation dataset may be replaced by the official dataset for analysis
training_data = pd.read_csv(
    r'path\to\training\csv',
    parse_dates=['date']
    )

validation_dataset = pd.read_csv(
    r'path\to\validation\csv',
    parse_dates=['date']
    )

#calculate the valley anomaly input
def calculate_valley(df):
    df['valley'] = 0
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
    df['year'] = df['date'].dt.year
    df = df.sort_values('date')

    grouped = df.groupby(['year', 'field_id'])

    for (_, field_data) in grouped:
        for i in range(len(field_data)):
            if i == 0 or i == len(field_data) - 1:
                df.loc[field_data.index[i], 'valley'] = 0
            else:
                diff_prev = field_data.iloc[i]['NDVI'] - field_data.iloc[i-1]['NDVI']
                diff_next = field_data.iloc[i]['NDVI'] - field_data.iloc[i+1]['NDVI']
                
                if diff_prev <= -0.1 and diff_next <= -0.1:
                    df.loc[field_data.index[i], 'valley'] = 1
    
    return df

#apply engineered input on datasets
training_data_wInputs = (
    training_data
    .pipe(calculate_valley)
    .drop(columns=['year'])
)

validation_dataset_wInputs = (
    validation_dataset
    .pipe(calculate_valley)
    .drop(columns=['year'])
)

training_data_wInputs.info()

validation_dataset_wInputs.info()

#specify anomaly inputs for IF
anomaly_inputs = ['NDVI', 'valley']

#set contamination and random_state value
model_IF = IsolationForest(contamination = 0.06, random_state = 42)

#train model
model_IF.fit(training_data_wInputs[anomaly_inputs])

#compute anomaly labels
validation_dataset_wInputs['anomaly'] = model_IF.predict(validation_dataset_wInputs[anomaly_inputs])

#function to calculate NDVI difference between current cell and the one two days before
def calculate_temporal_features(df, value_column):
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Initialise the new columns
    df['dif_to_forelast'] = pd.NA

    # Calculate the temporal features within each group
    groups = df.groupby(['field_id', df['date'].dt.year])
    
    for _, data in groups:
        data['dif_to_forelast'] = data[value_column].diff(periods=2)
        
        df.update(data)
    
    return df

#remove detected outliers
cleaned_validation_dataset = (
    validation_dataset_wInputs
    .loc[validation_dataset_wInputs['anomaly'] != -1]                  # Remove outliers
    .assign(date=pd.to_datetime(validation_dataset_wInputs['date']))   # Convert date to datetime
    .sort_values(by='date')                                            # Sort by ascending date
    .pipe(lambda x: calculate_temporal_features(x, 'NDVI'))            # Calculate temporal features without outliers
    .loc[:, ["date", "field_id", "NDVI", "dif_to_forelast"]]           # Select relevant columns for further processing
)

print("Length of original dataset:", len(validation_dataset_wInputs))
print("Length of cleaned dataset:", len(cleaned_validation_dataset))
print("Percent removed:", (100-((len(cleaned_validation_dataset)/len(validation_dataset_wInputs))*100)))

#place cleaned dataset into a list of dataframes
#as the smoothing function accepts a list
dataframes = {"validation_dataset": cleaned_validation_dataset}

#function to smooth dataframes using the SG filter
def smooth_and_save_dataframes(dataframes, output_directory):
    for df_name, df in dataframes.items():
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
        df.sort_values(by='date', ascending=True, inplace=True)
        df['year'] = df['date'].dt.year

        unique_combinations = df[['year', 'field_id']].drop_duplicates()
        
        for _, row in unique_combinations.iterrows():
            mask = (df['year'] == row['year']) & (df['field_id'] == row['field_id'])
            filtered_rows = df.loc[mask].sort_values(by='date', ascending=True)  # Sort by ascending date
            smoothed_values = signal.savgol_filter(filtered_rows['NDVI'], window_length=5, polyorder=2, mode='nearest')
            df.loc[mask, 'smoothed_NDVI'] = smoothed_values

        df.drop(columns=['NDVI', 'year'], inplace=True)  # Drop the original NDVI column
        df.rename(columns={'smoothed_NDVI': 'NDVI'}, inplace=True)  # Rename the smoothed column

        df = calculate_temporal_features(df, 'NDVI')

        output_filename = os.path.join(output_directory, f"{df_name}_SG.csv")
        df.to_csv(output_filename, index=False)
        print(f"Smoothed DataFrame '{df_name}' saved to '{output_filename}'")

#apply function and save cleaned and smoothed dataframe
smooth_and_save_dataframes(
    dataframes,
    r'path\to\final\dataset'
    )
