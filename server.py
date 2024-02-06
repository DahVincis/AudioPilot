import struct
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import matplotlib.pyplot as plt
import numpy as np
import threading

# Initialize storage for levels
chLVL = {18: [], 19: [], 22: []}

def handle_audio_level(address, *args):
    print(f"Received {address}: {args}")
    # args[0] will be the blob containing the 4 floats
    if len(args) > 0 and isinstance(args[0], bytes):
        # Decode the blob assuming it's in the format described: size followed by data
        blob = args[0]
        # The first 4 bytes are the size, but we already know the blob's structure, so we skip this part
        # Directly unpack the 4 float values from the blob
        values = struct.unpack('>4f', blob[4:20])  # Adjust according to the actual size and content of your blob
        print("Decoded values:", values)
        # Here, you would implement logic to associate these values with the specific channel


# Set up OSC server
dispatcher = Dispatcher()
dispatcher.map("/meters/6", handle_audio_level, needs_reply_address=True)
server = ThreadingOSCUDPServer(('0.0.0.0', 10123), dispatcher)

def update_plot():
    plt.ion()
    fig, ax = plt.subplots()
    while True:
        ax.clear()
        for ch_id, levels in chLVL.items():
            if levels:
                ax.plot(levels, label=f"Channel {ch_id}")
        ax.legend()
        plt.draw()
        plt.pause(1)

print(f"Serving on {server.server_address}")

# Start the OSC server in a separate thread
threadServer = threading.Thread(target=server.serve_forever)
threadServer.start()

# Keep the plotting on the main thread
update_plot()