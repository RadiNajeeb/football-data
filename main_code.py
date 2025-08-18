import pandas as pd
import numpy as np
import csv

df = pd.read_csv('database.csv')

    
df_athleticclub = df[df['Team'] == 'Athletic Club']
df_barcelona = df[df['Team'] == 'Barcelona']

print(df_barcelona.head())
    
    
# filter the data by team
# and input it into a new csv file that Ive created
 
clean_df = len(df['Team'].unique())
print(clean_df)
    
print(df_athleticclub.head())

with open('athleticclub.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(filtered_data.columns)
    for index, row in filtered_data.iterrows():
        writer.writerow(row)
    