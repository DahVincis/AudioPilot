import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import numpy as np
import matplotlib.pyplot as plt
from threading import Thread, Lock
import time
import nmap

# Initialize the dispatcher
dispatcher = Dispatcher()

# Prepare data storage
# Hardcoded frequencies as per the documentation
frequencies = np.array([
    20, 21, 22, 24, 26, 28, 30, 32, 34, 36,
    39, 42, 45, 48, 52, 55, 59, 63, 68, 73,
    78, 84, 90, 96, 103, 110, 118, 127, 136, 146,
    156, 167, 179, 192, 206, 221, 237, 254, 272, 292,
    313, 335, 359, 385, 412, 442, 474, 508, 544, 583,
    625, 670, 718, 769, 825, 884, 947, 1.02e3, 1.09e3, 1.17e3,
    1.25e3, 1.34e3, 1.44e3, 1.54e3, 1.65e3, 1.77e3, 1.89e3, 2.03e3, 2.18e3, 2.33e3,
    2.50e3, 2.68e3, 2.87e3, 3.08e3, 3.30e3, 3.54e3, 3.79e3, 4.06e3, 4.35e3, 4.67e3,
    5.00e3, 5.36e3, 5.74e3, 6.16e3, 6.60e3, 7.07e3, 7.58e3, 8.12e3, 8.71e3, 9.33e3,
    10.0e3, 10.72e3, 11.49e3, 12.31e3, 13.20e3, 14.14e3, 15.16e3, 16.25e3, 17.41e3, 18.66e3
])

# Initialize dataRTA with zeros to match the length of frequencies array
dataRTA = np.zeros_like(frequencies)

dataLock = Lock()  # Lock for thread-safe operations on dataRTA

# Plotting function to be run in a separate thread
def plotRTA():
    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.semilogx(frequencies, dataRTA, 'b-', label='Channel 19 RTA')
    ax.set_ylim(-15, 15)
    ax.set_xlim(20, 20000)
    ax.set_yticks(np.arange(-15, 20, step=5))
    frequency_ticks = [20, 40, 60, 80, 100, 200, 300, 400, 600, 800, 1e3, 2e3, 3e3, 4e3, 5e3, 6e3, 8e3, 10e3, 20e3]
    ax.set_xticks(frequency_ticks)
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x/1000)}k' if x >= 1000 else int(x)))
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Gain (dB)')
    ax.set_title('RTA Visualization for Channel 19')
    ax.grid(True, which="both", ls="--")
    ax.legend()

    while True:
        with dataLock:
            line.set_ydata(dataRTA)
        ax.relim()
        ax.autoscale_view(True, True, True)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.1)

# Function to handle RTA data for channel 19
def handleRTAData(_, *args):
    global dataRTA
    osc_blob = args[0]
    # The data is in little-endian 16-bit integers, so dtype should be '<i2'
    # and then we reshape to flatten the array of tuples
    new_data = np.frombuffer(osc_blob, dtype='<i2').reshape(-1)
    new_data_float = new_data.astype(np.float32) / 256.0  # Convert to float and scale
    with dataLock:  # Ensure thread-safe update of dataRTA
        # Since we are receiving 100 values, we update dataRTA accordingly
        # This assumes that dataRTA has been appropriately sized to match the 100 frequency bins
        np.copyto(dataRTA[:100], new_data_float)
    print(f"Received RTA data: {new_data_float[:5]}...")  # Print the first 5 values 

# Map the RTA data handler to the /meters/15 OSC address pattern
dispatcher.map("/meters/15", handleRTAData)

# Function to set RTA source to channel 19 and then request RTA data
async def setRTASourceAndRequestData(client):
    print("Setting RTA source and subscribing to /meters/15")
    # Set the RTA source to channel 19 (value is 20)
    client.send_message("/prefs/rta/source", [20])
    # Wait a bit to ensure the command is processed. This delay might need to be adjusted
    await asyncio.sleep(0.5)
    client.send_message("/subscribe", ["/meters/15", 1])  # Subscribe to RTA data
    # Now request RTA data
    client.send_message("/meters/15", [])
    print("Subscription request sent.")

# Correctly schedule setRTASourceAndRequestData within the asyncio event loop
async def requestRTAData(x32_ip, port):
    client = SimpleUDPClient(x32_ip, port)  # Use the X32's IP address here
    await setRTASourceAndRequestData(client)

async def initServer(local_ip, local_port): # Initialize the server
    server = AsyncIOOSCUDPServer((local_ip, local_port), dispatcher, asyncio.get_event_loop()) # Create the server
    transport, protocol = await server.create_serve_endpoint() # Create datagram endpoint and start serving
    return transport # Return the transport object

async def main(local_ip, x32_ip, port, local_port):
    transport = await initServer(local_ip, local_port)  # Use the local IP for the server
    
    # Schedule the RTA source setting and data request as an asyncio task
    asyncio.create_task(requestRTAData(x32_ip, port))

    plotting_thread = Thread(target=plotRTA, daemon=True)
    plotting_thread.start()

    try:
        while True:
            print("Server is running, waiting for OSC messages...")
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        transport.close()
        print("Server stopped.")

if __name__ == "__main__":
    local_ip = "127.0.0.1"  # Local server IP address
    local_port = 1337  # Local server port
    x32_ip = "192.168.0.102"  # X32 mixer IP address
    port = 10023  # OSC port
    asyncio.run(main(local_ip, x32_ip, port, local_port))