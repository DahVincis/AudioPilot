import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the CSV file with multiple updates
csv_path = 'rta_db_values.csv'  # Update this path as needed
updates_data = pd.read_csv(csv_path)

# Extract the numeric part from the 'Frequency Band' column
updates_data['Frequency'] = updates_data['Frequency Band'].str.extract(r'(\d+)').astype(int)

# Find rows where the frequency resets to 20 to mark the start of a new update
resets = updates_data['Frequency'] == 20
updates_data['Update Index'] = resets.cumsum()  # Cumulative sum of resets marks each update uniquely

# Identify the total number of updates
total_updates = updates_data['Update Index'].max()

# Loop through each update and plot the data
for update_number in range(1, total_updates + 1):
    update_data = updates_data[updates_data['Update Index'] == update_number]
    
    plt.figure(figsize=(15, 6))
    plt.plot(update_data['Frequency'], update_data['dB Value'], marker='o', linestyle='-')
    plt.xscale('log')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('dB Value')
    plt.title(f'Frequency Response Update {update_number}')
    plt.grid(True, which='both', ls='--', lw=0.5)
    xticks = [int(x) for x in np.logspace(np.log10(min(update_data['Frequency'])), np.log10(max(update_data['Frequency'])), num=15)]
    plt.xticks(xticks, [str(x) for x in xticks])
    plt.ylim(-128, 0)
    plt.tight_layout()
    plt.show()
