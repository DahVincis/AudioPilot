from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import time
import threading
import logging
import struct
from numpy.polynomial.polynomial import Polynomial
import numpy as np
import matplotlib.pyplot as plt

# Setup logging
logging.basicConfig(level=logging.DEBUG)

X32_IP = '192.168.1.21'
client = SimpleUDPClient(X32_IP, 10023)

# Hardcoded frequencies based on documentation
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


# Initialize plotting (This might be moved or called differently based on your plotting strategy)
plt.ion()
fig, ax = plt.subplots()
ax.set_xscale('log')
ax.set_xlim(20, 20000)
ax.set_ylim(-60, 10)
line, = ax.plot(frequencies, np.zeros_like(frequencies), 'r-')  # Initial plot
plt.show(block=False)

def keep_behringer_awake():
    """Sends keep-alive messages to Behringer."""
    while True:
        logging.debug("Sending keep-alive messages to Behringer")
        client.send_message('/xremote', None)
        client.send_message('/ch/18/mix/fader', None)
        client.send_message('/ch/19/mix/fader', None)
        client.send_message('/ch/20/mix/fader', None)
        client.send_message('/ch/22/mix/fader', None)
        client.send_message('/ch/29/mix/fader', None)
        time.sleep(3)

def subscribe_and_renew_rta():
    """Subscribes to RTA data and periodically renews the subscription."""
    logging.debug("Subscribing to meters/15")
    client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 80]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
    logging.debug("Subscription message sent")
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        logging.debug("Renewing subscription to meters/15")
        client.send_message("/renew", [""])

def process_rta_data(address, *args):
    global line, ax  # These are needed if you're updating the plot objects

    print(f"Entered process_rta_data with address: {address} and args: {args}")
    if not args:
        logging.error(f"No RTA data received on {address}")
        return

    rta_blob = args[0]
    print(f"RTA blob size: {len(rta_blob)}")
    
    # Calculate the number of 32-bit integers (4 bytes each) in the blob
    data_points = len(rta_blob) // 4
    print(f"Number of data points: {data_points}")

    try:
        # Dynamically unpack the blob based on its actual size
        ints = struct.unpack(f'<{data_points}I', rta_blob)
        db_values = []
        for int_value in ints:
            # Process each 32-bit integer into two short integers and convert to dB
            short_int1 = int_value & 0xFFFF
            short_int2 = (int_value >> 16) & 0xFFFF
            # Adjust for signed values
            if short_int1 >= 0x8000: short_int1 -= 0x10000
            if short_int2 >= 0x8000: short_int2 -= 0x10000
            # Convert to dB values
            db_value1 = short_int1 / 256.0
            db_value2 = short_int2 / 256.0
            db_values.extend([db_value1, db_value2])
        
        # Ensure db_values length matches frequencies length for plotting
        db_values = db_values[:len(frequencies)]
        
        # Update the plot
        ax.clear()  # Clear the plot for new data
        ax.set_xscale('log')
        ax.set_xlim(20, 20000)
        ax.set_ylim(-60, 10)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Level (dB)')
        ax.set_title('RTA Visualization')
        
        # Plot the new data
        line, = ax.plot(frequencies, db_values, 'r-')  # Recreate the plot with updated data
        plt.draw()
        plt.pause(0.1)  # Allows the GUI to update

    except Exception as e:
        logging.error(f"Error processing RTA data: {e}")

# data points from mixer to convert to dB
fader_positions = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
db_values = np.array([-90.0, -30.0, -10.0, 0.0, 10.0])

# Fit a polynomial to the data points
p = Polynomial.fit(fader_positions, db_values, deg=4)

def print_fader_handler(address, *args):
    if args and isinstance(args[0], float):
        float_value = args[0]
        db_value = p(float_value)
        print(f"[{address}] ~ Fader value: {db_value:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

def default_handler(address, *args):
    """Default handler for all messages."""
    logging.info(f"Received fader message on {address}. Args: {args}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.map("/meters", process_rta_data)
    dispatcher.map("/*/*/mix/fader", print_fader_handler)
    dispatcher.set_default_handler(default_handler)

    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    logging.info(f"Serving on {server.server_address}")
    client._sock = server.socket

    keep_alive_thread = threading.Thread(target=keep_behringer_awake, daemon=True)
    keep_alive_thread.start()

    # Start the RTA subscription and renewal in a separate thread
    rta_subscription_thread = threading.Thread(target=subscribe_and_renew_rta, daemon=True)
    rta_subscription_thread.start()

    server.serve_forever()
