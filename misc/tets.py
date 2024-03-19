import numpy as np
import matplotlib.pyplot as plt
import time

plt.ion()
fig, ax = plt.subplots()
fig.patch.set_facecolor('white')  # Set the background color of the figure to white
ax.set_facecolor('black')  # Set the background color of the axes to white

# Assuming we're simplifying to 10 bars across the frequency spectrum for demonstration
num_bins = 10
frequencies = np.linspace(20, 20000, 100)
db_values_plot = np.random.rand(100) * 40 - 60  # Random dB values between -60 and -20 for testing

# This function simulates binning and calculates the mean dB value for each bin
def simulate_bar_data(frequencies, db_values, bins):
    # Bin frequencies evenly and calculate the mean dB value for each bin
    freq_bins = np.linspace(frequencies.min(), frequencies.max(), bins+1)
    bin_means = [db_values[(frequencies >= freq_bins[i]) & (frequencies < freq_bins[i+1])].mean() for i in range(len(freq_bins)-1)]
    return freq_bins[:-1], bin_means

# Simulate initial bar data
bin_edges, bin_means = simulate_bar_data(frequencies, db_values_plot, num_bins)

# Plot bars, specify bar color as blue
bars = ax.bar(bin_edges, bin_means, width=np.diff(bin_edges)[0], align='edge', color='blue')

ax.set_ylim(-60, 20)  # This ensures bars start from bottom (-60 dB) upwards
ax.set_xlim(20, 20000)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Level (dB)')
ax.set_title('RTA Visualization')
plt.show(block=False)

while True:
    db_values_plot = np.random.rand(100) * 40 - 60  # Generate random dB values
    _, bin_means = simulate_bar_data(frequencies, db_values_plot, num_bins)

    # Clear the current axes and redraw
    ax.cla()
    ax.set_facecolor('white')  # Ensure the background is reset if changed anywhere else

    # Create new bars with the updated data, specifying bar color as blue
    ax.bar(bin_edges, bin_means, width=np.diff(bin_edges)[0], align='edge', color='blue')

    ax.set_ylim(-60, 20)  # Reconfirm the y-axis limits to ensure consistency
    ax.set_xlim(20, 20000)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Level (dB)')
    ax.set_title('RTA Visualization')

    fig.canvas.draw()
    fig.canvas.flush_events()
    time.sleep(0.1)  # Update periodically
