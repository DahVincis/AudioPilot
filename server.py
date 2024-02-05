import struct
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import threading
import matplotlib.pyplot as plt

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

def plot_levels():
    plt.ion()
    while True:
        plt.clf()
        for ch_id, levels in chLVL.items():
            if levels:
                plt.plot(levels, label=f"Channel {ch_id}")
        plt.legend()
        plt.pause(1)  # Update the plot every second

# Set up OSC server
dispatcher = Dispatcher()
dispatcher.map("/meters/6", handle_audio_level, needs_reply_address=True)
server = ThreadingOSCUDPServer(('0.0.0.0', 10123), dispatcher)
print(f"Serving on {server.server_address}")

# Start the plotting in a separate thread
threadPlot = threading.Thread(target=plot_levels)
threadPlot.start()

# Start the OSC server
server.serve_forever()