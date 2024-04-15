import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the CSV data
csvPath = 'rta_db_values2.csv'
updateData = pd.read_csv(csvPath)

# Convert frequency band to numeric and calculate update indexes
updateData['Frequency'] = pd.to_numeric(updateData['Frequency Band'], errors='coerce')
resets = updateData['Frequency'] == 20
updateData['Update Index'] = resets.cumsum()
totalUpdates = updateData['Update Index'].max()

# Set up the plot outside the loop
plt.figure(figsize=(20, 6))
plt.ion()  # Turn on interactive mode

# Create initial plot
line, = plt.plot([], [], marker='o', linestyle='-')
plt.xscale('log')
plt.xlabel('Frequency (Hz)')
plt.ylabel('dB Value')
plt.grid(True, which='both', ls='--', lw=0.5)
plt.ylim(-90, 0)

# Iterate over each update
for updateNumber in range(1, totalUpdates + 1):
    currentUpdateData = updateData[updateData['Update Index'] == updateNumber]
    
    # Update the data for the line
    line.set_data(currentUpdateData['Frequency'], currentUpdateData['dB Value'])
    plt.title(f'Frequency Response Update {updateNumber}')
    
    # Update xticks dynamically
    if not currentUpdateData['Frequency'].empty:
        xticks = [int(x) for x in np.logspace(np.log10(min(currentUpdateData['Frequency'])), np.log10(max(currentUpdateData['Frequency'])), num=15)]
        plt.xticks(xticks, [str(x) for x in xticks])
        plt.xlim(min(currentUpdateData['Frequency']), max(currentUpdateData['Frequency']))
    
    plt.draw()
    plt.pause(0.1)  # Pause for 0.1 second

plt.ioff()  # Turn off interactive mode
