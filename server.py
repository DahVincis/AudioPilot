import struct
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import matplotlib.pyplot as plt
import numpy as np
import threading
import keyboard

# Initialize storage for levels
chLVL = {18: [], 19: [], 22: []}
chMapping = {17: 18, 18: 19, 21: 22}  # Mapping of index to channel number

def handle_audio_level(address, *args):
    print(f"Received {address}: {args}")
    if len(args) > 0 and isinstance(args[0], bytes):
        blob = args[0]
        # The first 4 bytes are the size, but we already know the blob's structure, so we skip this part
        # Directly unpack the 4 float values from the blob
        values = struct.unpack('>4f', blob[4:20])
        print("Decoded values:", values)
        channel_index = args[1]  # This is a placeholder; you need to get the channel index from somewhere.
        if channel_index in chMapping:
            channel_id = chMapping[channel_index]
            chLVL[channel_id].append(values[0])  # Just an example using the first value

# Set up OSC server
dispatcher = Dispatcher()
dispatcher.map("/meters/6", handle_audio_level, needs_reply_address=True)
server = ThreadingOSCUDPServer(('0.0.0.0', 10123), dispatcher)

def update_plot():
    plt.ion()
    fig, ax = plt.subplots()
    plt.show(block=False)
    while True:
        ax.clear()
        for ch_id, levels in chLVL.items():
            if levels:
                ax.plot(levels, label=f"Channel {ch_id}")
        ax.legend()
        plt.draw()
        if keyboard.is_pressed('esc'):
            print("Quitting plot loop.")
            break
        plt.pause(1)
    plt.close(fig)

print(f"Serving on {server.server_address}")

# Start the OSC server in a separate thread
threadServer = threading.Thread(target=server.serve_forever)
threadServer.start()

# Keep the plotting on the main thread
update_plot()