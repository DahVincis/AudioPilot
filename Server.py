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
        min_db = -90
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

def subscribe_and_renew_rta():
    """Subscribes to RTA data and periodically renews the subscription."""
    client.send_message("/batchsubscribe", ["meters/15", "/meters/15", 0, 0, 1])
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        client.send_message("/renew", ["meters/15"])

def process_rta_data(args):
    """Processes RTA data received from the X32."""
    rta_blob = args[0]
    short_ints = struct.unpack('<100h', rta_blob)
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

    # Start the RTA subscription and renewal in a separate thread
    rta_subscription_thread = threading.Thread(target=subscribe_and_renew_rta, daemon=True)
    rta_subscription_thread.start()

    server.serve_forever()
