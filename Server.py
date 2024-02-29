from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import time
import threading
import logging
import math
import struct

# Setup logging
logging.basicConfig(level=logging.DEBUG)

behringer_addr = '26.11.225.132'
client = SimpleUDPClient(behringer_addr, 10023)

def linear_to_db(linear_value):
    """Converts a linear fader value to dB."""
    if linear_value <= 0:
        return "-inf"
    else:
        min_db = -90  # Assuming -90 dB to 0 dB mapping for 0.0 to 1.0 linear scale.
        max_db = 0
        range_db = max_db - min_db
        return min_db + (math.log10(linear_value) / math.log10(1.0)) * range_db

def keep_behringer_awake():
    """Sends keep-alive messages to Behringer."""
    while True:
        logging.debug("Sending keep-alive messages to Behringer")
        client.send_message('/xremote', None)
        client.send_message('/mtx/02/mix/fader', None)
        client.send_message('/mtx/01/mix/fader', None)
        client.send_message('/mtx/01/mix/on', None)
        time.sleep(5)

def process_rta_data(args):
    """Processes RTA data received from the X32."""
    rta_blob = args[0]  # RTA data is expected to be the first argument
    # Decode the blob into 100 short ints (50 32-bit values representing 100 short ints)
    short_ints = struct.unpack('<100h', rta_blob)  # Little-endian format
    db_values = [short_int / 256.0 for short_int in short_ints]
    for i, db_value in enumerate(db_values):
        logging.info(f"RTA Frequency Band {i+1}: {db_value} dB")

def default_handler(address, *args):
    """Default handler for all messages."""
    if "/mix/fader" in address:
        linear_value = args[0]
        db_value = linear_to_db(linear_value)
        logging.info(f"Received fader message on {address}. Linear: {linear_value}, in dB: {db_value}")
    elif address == "/meters/15":
        process_rta_data(args)
    else:
        logging.info(f"Received message on {address} with args: {args}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(default_handler)

    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    logging.info(f"Serving on {server.server_address}")
    client._sock = server.socket

    keep_alive_thread = threading.Thread(target=keep_behringer_awake, daemon=True)
    keep_alive_thread.start()

    # Subscribe to RTA data
    subscribe_to_rta_thread = threading.Thread(target=lambda: 
        client.send_message("/meters/subscribe", ["/meters/15", 1]), daemon=True)
    subscribe_to_rta_thread.start()

    server.serve_forever()
