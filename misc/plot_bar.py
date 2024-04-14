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

# Initial bars setup
bars = []

for updateNumber in range(1, totalUpdates + 1):
    ax.clear()  # Clear the axis for redraw
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('dB Value')
    ax.set_title(f'Frequency Response Histogram Style Update {updateNumber}')
    ax.set_xscale('log')
    ax.grid(True, which='both', ls='--', lw=0.5)
    ax.set_ylim(-90, 0)

    currentUpdateData = updateData[updateData['Update Index'] == updateNumber]
    currentUpdateData = currentUpdateData.sort_values(by='Frequency')
    frequencies = currentUpdateData['Frequency']
    dbValues = currentUpdateData['dB Value']

    # Assign colors based on dB value thresholds
    colors = ['red' if val >= threshold_80_percent else 'yellow' if threshold_80_percent > val >= threshold_75_percent else 'blue' for val in dbValues]

    # Generate dynamic bins based on the frequency values
    bin_edges = np.geomspace(frequencies.min(), frequencies.max(), len(frequencies) + 1)
    bin_widths = np.diff(bin_edges)

    # Draw bars with calculated properties and without black edges
    for freq, height, color in zip(frequencies, dbValues + 90, colors):
        bars.append(ax.bar(freq, height, width=bin_widths[0], bottom=-90, color=color, edgecolor=color, align='edge'))

    # Update x-axis ticks to maintain log scale visibility
    xticks = [int(x) for x in np.logspace(np.log10(min(frequencies)), np.log10(max(frequencies)), num=15)]
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(x) for x in xticks])
    ax.set_xlim(min(frequencies), max(frequencies))

    plt.pause(0.1)  # Short pause to allow for GUI events

plt.ioff()  # Interactive mode off
