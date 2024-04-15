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

# Initial plot setup
fig, ax = plt.subplots(figsize=(20, 6))
plt.ion()  # Interactive mode on
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('dB Value')
ax.set_title('Frequency Response Histogram Style Update')
ax.set_xscale('log')
ax.grid(True, which='both', ls='--', lw=0.5)
ax.set_ylim(-90, 0)  # Correct y-axis scale

# Define the thresholds
threshold_80_percent = -18  # 80% of the way to 0 dB from -90 dB
threshold_75_percent = -22.5  # 75% of the way to 0 dB from -90 dB

# Pre-prepare data to avoid redoing it in every iteration
sorted_data = updateData.sort_values(by='Frequency')
grouped_data = sorted_data.groupby('Update Index')

# Pre-create bars
for updateNumber, currentUpdateData in grouped_data:
    frequencies = currentUpdateData['Frequency']
    bin_edges = np.geomspace(frequencies.min(), frequencies.max(), len(frequencies) + 1)
    bin_widths = np.diff(bin_edges)
    bars = ax.bar(frequencies, currentUpdateData['dB Value'] + 90, width=bin_widths, color='blue', edgecolor='blue', align='edge', bottom=-90)
    break  # Create only once and then update these bars in the loop

for updateNumber, currentUpdateData in grouped_data:
    ax.set_title(f'Frequency Response Histogram Style Update {updateNumber}')
    frequencies = currentUpdateData['Frequency']
    dbValues = currentUpdateData['dB Value']

    # Update bar heights and colors
    for bar, height, color in zip(bars, dbValues + 90, ['red' if val >= threshold_80_percent else 'yellow' if threshold_80_percent > val >= threshold_75_percent else 'blue' for val in dbValues]):
        bar.set_height(height)
        bar.set_color(color)
        bar.set_edgecolor(color)

    plt.pause(0.1)  # Short pause to allow for GUI events

plt.ioff()  # Turn off interactive mode
