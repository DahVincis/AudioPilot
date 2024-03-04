import numpy as np
import matplotlib.pyplot as plt
import time

plt.ion()
fig, ax = plt.subplots()
frequencies = np.linspace(20, 20000, 100)
db_values_plot = np.random.rand(100) * 40 - 60  # Random dB values between -60 and -20 for testing
line, = ax.semilogx(frequencies, db_values_plot)
ax.set_ylim(-60, 20)
ax.set_xlim(20, 20000)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Level (dB)')
ax.set_title('RTA Visualization')
ax.grid(True)
plt.show(block=False)

while True:
    db_values_plot = np.random.rand(100) * 40 - 60  # Generate new random dB values
    line.set_ydata(db_values_plot)
    fig.canvas.draw()
    fig.canvas.flush_events()
    time.sleep(1)  # Update every second
