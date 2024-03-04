from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import time
import threading
import logging
import math
import struct
from numpy.polynomial.polynomial import Polynomial
import numpy as np

# Setup logging
logging.basicConfig(level=logging.DEBUG)

X32_IP = '192.168.0.101'
client = SimpleUDPClient(X32_IP, 10023)

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
    client.send_message("/batchsubscribe", ["meters/15", "/meters/15", 0, 0, 1])
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        client.send_message("/renew", ["meters/15"])

def process_rta_data(address, *args):
    """Processes RTA data received from the X32."""
    # Ensure there's at least one argument (the rta_blob)
    if not args:
        logging.error(f"No RTA data received on {address}")
        return

    # The rta_blob is expected to be the first argument
    rta_blob = args[0]

    # Ensure the rta_blob is of the expected length to avoid unpacking errors
    expected_length = 100 * 2  # 100 short integers, each 2 bytes
    if len(rta_blob) != expected_length:
        logging.error(f"On {address} Unexpected RTA blob length: {len(rta_blob)}. Expected {expected_length}.")
        return

    try:
        # Unpack the blob into 100 short integers
        short_ints = struct.unpack('<100h', rta_blob)
        # Convert to dB values (example conversion, adjust as necessary)
        db_values = [short_int / 256.0 for short_int in short_ints]
        for i, db_value in enumerate(db_values):
            logging.info(f"{address} ~ RTA Frequency Band {i+1}: {db_value} dB")
    except struct.error as e:
        logging.error(f"{address} ~ Error unpacking RTA data: {e}")

# Example calibration data points for a channel
# Replace these with your actual measured data points
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
    dispatcher.map("meters/15", process_rta_data)
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
