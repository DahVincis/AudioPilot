import pandas as pd

# Load the CSV file
df = pd.read_csv('C:/Users/pedro/OneDrive/Desktop/Python-OSC/misc/rta_db_values.csv')

# Check and extract band number with error handling
def extract_band_number(x):
    try:
        return int(x.split(' ')[1])
    except (IndexError, ValueError):
        return None  # Return None for rows that don't match the expected format

df['Band Number'] = df['Frequency Band'].apply(extract_band_number)

# Remove rows with None in 'Band Number'
df = df.dropna(subset=['Band Number'])

# Calculate updates assuming Band 1 marks the beginning of a new update
df['Update'] = (df['Band Number'] == 1).cumsum()

# Continue as before
df_filtered = df[df['Band Number'] > 2]

frequencies = [20, 21, 22, 24, 26, 28, 30, 32, 34, 36, 39, 42, 45, 48, 52, 55, 59, 63, 68, 73, 78, 84, 90, 96, 103, 110, 118, 127, 136, 146, 156, 167, 179, 192, 206, 221, 237, 254, 272, 292, 313, 335, 359, 385, 412, 442, 474, 508, 544, 583, 625, 670, 718, 769, 825, 884, 947, 1020, 1090, 1170, 1250, 1340, 1440, 1540, 1650, 1770, 1890, 2030, 2180, 2330, 2500, 2680, 2870, 3080, 3300, 3540, 3790, 4060, 4350, 4670, 5000, 5360, 5740, 6160, 6600, 7070, 7580, 8120, 8710, 9330, 10000, 10720, 11490, 12310, 13200, 14140, 15160, 16250, 17410, 18660]

updates = df_filtered['Update'].max()
columns = ['Update'] + frequencies[:100]  # Adjusted to match the number of bands
excel_df = pd.DataFrame(columns=columns)

for update in range(1, updates + 1):
    update_data = df_filtered[df_filtered['Update'] == update]['dB Value'].values
    excel_df = excel_df._append(pd.DataFrame([[update] + list(update_data)], columns=columns), ignore_index=True)

# Save the processed data to an Excel file
excel_df.to_excel('processed_rta_db_values.xlsx', index=False)

print('Excel file created successfully!')
