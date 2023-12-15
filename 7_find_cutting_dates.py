#the following python modules need to be installed:
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os

#load dataset
official_df = pd.read_csv(
            r'path\to\official_dataset.csv',
            parse_dates=['date'])

#function to find cutting dates
def find_cut_dates(dataframe, output_csv):

    dataframe['date'] = pd.to_datetime(dataframe['date'], format="%d/%m/%Y")                   # Convert df dates to datetime
    dataframe = dataframe[(dataframe['date'].dt.month < 3) | (dataframe['date'].dt.month > 4)] # Remove all dates from March and April (no cuts)
    dataframe.sort_values(by='date', inplace=True)                                             # Sort by ascending

    
    grouped_df = dataframe.groupby([dataframe['date'].dt.year, 'field_id'])                    # Form subgroups of year-field ID combinations         

    # Identify clusters of NDVI drop values <= -0.1
    results = {}

    for (year, field_id), group_df in grouped_df:                                              # Find clusters by year-field_id pair
        clusters = []                                                                          # List of all found clusters
        current_cluster = []

        for _, row in group_df.iterrows():
            if row['dif_to_forelast'] <= -0.1:
                current_cluster.append(row)
            elif current_cluster:
                clusters.append(pd.DataFrame(current_cluster))
                current_cluster = []

        if current_cluster:
            clusters.append(pd.DataFrame(current_cluster))

        # Find first date of each cluster
        first_date = []
        for cluster in clusters:
            if not cluster.empty:
                first_date_value = dataframe['date'][cluster.index[0]]
                first_date.append(first_date_value.strftime('%d/%m/%Y'))
                #print(f"First date found for cluster of {year, field_id} at {first_date_value.strftime('%d/%m/%Y')}")
        
        results[year, field_id] = {
            'num_cuts': len(first_date),
            'cutting dates': first_date
        }

    # Create and populate the CSV file
    csv_data = []
    for (year, field_id), result in results.items():
        csv_row = {
            'year': year,
            'field_id': field_id
        }
        
        for i, cut_date in enumerate(result['cutting dates'], start=1):
            csv_row[f'cut_{i}'] = cut_date
        
        csv_data.append(csv_row)
    
    csv_df = pd.DataFrame(csv_data)
    csv_df.to_csv(output_csv, index=False)


#apply function
#save file with cutting dates
find_cut_dates(
    official_df,
    r'path\to\cutting_dates.csv'
    )
