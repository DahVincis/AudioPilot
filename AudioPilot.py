from Server import discMixers, keepMixerAwake, subRenewRTA, handlerRTA, handlerFader, handlerPreampTrim, handlerDefault, argparse, threading, pg, sys, time, setLogTicks, updatePlot
from DynEQ import getValidChannel, updateAllBands
import argparse
import threading
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# search mixers on the network
mixers = discMixers()
if not mixers:
    print("No mixers found.")
    exit()

# options for user
for idx, (ip, details) in enumerate(mixers.items(), start=1):
    print(f"{idx}: Mixer at IP {ip} with details: {details}")

# user selects mixer
chosen = int(input("Select the number for the desired mixer: ")) - 1
chosenIP = list(mixers.keys())[chosen]

# set the mixer IP
X32IP = chosenIP
client = SimpleUDPClient(X32IP, 10023)

# argument parser for IP and port
parser = argparse.ArgumentParser()
parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
args = parser.parse_args()

# map handlers to OSC addresses
dispatcher = Dispatcher()
dispatcher.map("/meters", handlerRTA)
dispatcher.map("/*/*/mix/fader", handlerFader)
dispatcher.map("/*/*/preamp/trim", handlerPreampTrim)
dispatcher.set_default_handler(handlerDefault)

server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
print(f"Serving on {server.server_address}")
client._sock = server.socket

# start threads for keep alive and RTA subscription
threadKeepAlive = threading.Thread(target=keepMixerAwake, daemon=True)
threadKeepAlive.start()

threadRTASub = threading.Thread(target=subRenewRTA, daemon=True)
threadRTASub.start()

# Initialize the PyQt application
app = QApplication([])
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Frequency Response")
plot = win.addPlot(title="Frequency Response Histogram")
plot.setLogMode(x=True, y=False)
plot.setYRange(-90, 0)
plot.setLabel('bottom', 'Frequency', units='Hz')
plot.setLabel('left', 'dB Value')

# Initialize bars dictionary to hold the plot data
bars = {}

# Set up logarithmic ticks for the x-axis
setLogTicks()

# Set up timer to update plot periodically
timer = QTimer()
timer.timeout.connect(updatePlot)
timer.start(100)  # Update the plot every 500 milliseconds

# Start a separate thread to run the OSC server
threadServerOSC = threading.Thread(target=server.serve_forever, daemon=True)
threadServerOSC.start()

print("Select the vocal type:")
print("1. Low Pitch")
print("2. High Pitch")
print("3. Mid Pitch (Flat)")

try:
    inputVocalType = int(input("Enter the number for the desired vocal type: "))
    vocalTypes = ['Low Pitch', 'High Pitch', 'Mid Pitch']
    vocalType = vocalTypes[inputVocalType - 1]  # Adjust index for zero-based
except (IndexError, ValueError):
    print("Invalid input. Defaulting to 'Mid Pitch (Flat)'.")
    vocalType = 'Mid Pitch'

channel = getValidChannel()  # Get a valid channel number from the user

print(f"Updating bands for vocal type {vocalType} on channel {channel}...")
try:
    while True:
        updateAllBands(vocalType, channel)
        print("Waiting for next update cycle...")
        time.sleep(1)  # Pause 10 seconds between updates
except KeyboardInterrupt:
    print("Updates stopped by user.")

# Start the PyQtGraph Application
sys.exit(app.exec_())