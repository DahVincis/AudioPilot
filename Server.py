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
    logging.debug("Subscribing to meters/15")
    client.send_message("/batchsubscribe", ["meters/15", "/meters/15", 0, 0, 1])
    logging.debug("Subscription message sent")
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        logging.debug("Renewing subscription to meters/15")
        client.send_message("/renew", ["meters/15"])

def process_rta_data(address, *args):
    print(f"Entered process_rta_data with address: {address} and args: {args}")
    if not args:
        logging.error(f"No RTA data received on {address}")
        return

    rta_blob = args[0]
    print(f"RTA blob size: {len(rta_blob)}")
    print(f"RTA blob content: {rta_blob.hex()}")  # This will print the blob as hexadecimal

    expected_length = 50 * 4  # 50 32-bit integers, each 4 bytes
    if len(rta_blob) != expected_length:
        logging.error(f"On {address} Unexpected RTA blob length: {len(rta_blob)}. Expected {expected_length}.")
        return

    try:
        # Unpack the blob into 50 32-bit integers
        ints = struct.unpack('<50I', rta_blob)
        # Process each 32-bit integer into two short integers and convert to dB
        db_values = []
        for int_value in ints:
            # Mask and shift to get the two short integers from the 32-bit integer
            short_int1 = int_value & 0xFFFF
            short_int2 = (int_value >> 16) & 0xFFFF
            # Convert short integers to signed values
            if short_int1 >= 0x8000:
                short_int1 -= 0x10000
            if short_int2 >= 0x8000:
                short_int2 -= 0x10000
            # Calculate dB values
            db_value1 = short_int1 / 256.0
            db_value2 = short_int2 / 256.0
            db_values.extend([db_value1, db_value2])

        for i, db_value in enumerate(db_values):
            print(f"{address} ~ RTA Frequency Band {i+1}: {db_value} dB")
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