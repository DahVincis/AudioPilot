import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time

# Load the CSV file with multiple updates
csvPath = 'rta_db_values1.csv'  # Update this path as needed
updateData = pd.read_csv(csvPath)

# Extract the numeric part from the 'Frequency Band' column
updateData['Frequency'] = updateData['Frequency Band'].str.extract(r'(\d+)').astype(int)

# Find rows where the frequency resets to 20 to mark the start of a new update
resets = updateData['Frequency'] == 20
updateData['Update Index'] = resets.cumsum()  # Cumulative sum of resets marks each update uniquely

# Identify the total number of updates
totalUpdates = updateData['Update Index'].max()

# Loop through each update and plot the data
for updateNumber in range(1, totalUpdates + 1):
    updateData = updateData[updateData['Update Index'] == updateNumber]
    
    plt.figure(figsize=(20, 6))
    plt.plot(updateData['Frequency'], updateData['dB Value'], marker='o', linestyle='-')
    plt.xscale('log')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('dB Value')
    plt.title(f'Frequency Response Update {updateNumber}')
    plt.grid(True, which='both', ls='--', lw=0.5)
    xticks = [int(x) for x in np.logspace(np.log10(min(updateData['Frequency'])), np.log10(max(updateData['Frequency'])), num=15)]
    plt.xticks(xticks, [str(x) for x in xticks])
    plt.ylim(-128, 0)
    plt.tight_layout()
    plt.show()