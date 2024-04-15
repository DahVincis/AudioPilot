import sys
import pandas as pd
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Load and prepare data from the CSV file
csvPath = 'rta_db_values2.csv'
updateData = pd.read_csv(csvPath)
updateData['Frequency'] = pd.to_numeric(updateData['Frequency Band'], errors='coerce')
resets = updateData['Frequency'] == 20
updateData['Update Index'] = resets.cumsum()
totalUpdates = updateData['Update Index'].max()

# Define thresholds for coloring
threshold_80_percent = -18
threshold_75_percent = -22.5

# PyQtGraph setup
app = QApplication([])
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Bar Plot with PyQtGraph")
plot = win.addPlot(title="Frequency Response Histogram Style Update")
plot.setLogMode(x=True, y=False)
plot.setYRange(-90, 0)
plot.setLabel('bottom', 'Frequency', units='Hz')
plot.setLabel('left', 'dB Value')

bars = []

# Pre-calculate x-axis ticks
min_freq = updateData['Frequency'].min()
max_freq = updateData['Frequency'].max()
xticks = np.logspace(np.log10(min_freq), np.log10(max_freq), num=20)
plot.getAxis('bottom').setTicks([[(np.log10(v), str(int(v))) for v in xticks]])

# Function to update the plot
def update(updateNumber):
    if updateNumber > totalUpdates:  # Stop updating if no more data
        timer.stop()
        return

    # Select current segment of data
    currentUpdateData = updateData[updateData['Update Index'] == updateNumber]
    frequencies = currentUpdateData['Frequency'].values
    dbValues = currentUpdateData['dB Value'].values
    
    # Calculate color based on dB value
    colors = ['r' if db >= threshold_80_percent else 'y' if threshold_80_percent > db >= threshold_75_percent else 'b' for db in dbValues]
    
    if not bars:  # First update
        for freq, db, color in zip(frequencies, dbValues, colors):
            bar = plot.plot([freq, freq], [db, -90], pen=pg.mkPen(color, width=3))
            bars.append(bar)
    else:  # Update existing bars
        for bar, freq, db, color in zip(bars, frequencies, dbValues, colors):
            bar.setData([freq, freq], [db, -90])
            bar.setPen(pg.mkPen(color, width=3))

updateNumber = 1  # Start from the first segment

# Timer for periodic update
timer = QTimer()
timer.timeout.connect(lambda: update(updateNumber))
timer.start(100)  # Update every 0.1 seconds

# Increase update number for next cycle
def increment_update_number():
    global updateNumber
    updateNumber += 1

timer.timeout.connect(increment_update_number)

if __name__ == '__main__':
    sys.exit(app.exec_())
