import numpy as np
import matplotlib.pyplot as plt
import time

# Hardcoded frequencies for demonstration
frequencies = np.linspace(20, 20000, 100)  # Adjust as needed

# Initialize plotting
plt.ion()
fig, ax = plt.subplots()
ax.set_xscale('log')
ax.set_xlim(20, 20000)
ax.set_ylim(-60, 10)

# Initially, no histogram, so we don't create one outside the update function
plt.show(block=False)

simulate_data = True  # Toggle for simulation mode

def update_plot(db_values):
    """Updates the plot with new dB values displayed as a histogram."""
    ax.clear()  # Clear existing content
    ax.set_xscale('log')
    ax.set_xlim(20, 20000)
    ax.set_ylim(-60, 10)
    ax.hist(frequencies, bins=np.logspace(np.log10(20), np.log10(20000), num=len(frequencies)), weights=db_values, log=True)
    plt.draw()
    plt.pause(0.5)

def simulate_data_processing():
    """Simulates data processing by generating random dB values for histogram."""
    while True:
        db_values = np.random.rand(len(frequencies)) * 40 - 30  # Random dB values for testing
        update_plot(db_values)
        time.sleep(0.1)  # Simulate delay

if simulate_data:
    simulate_data_processing()
