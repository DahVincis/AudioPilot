import csv
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

X32_IP = '192.168.1.24'
client = SimpleUDPClient(X32_IP, 10023)

# Initialize CSV files with headers outside of the functions
def initialize_csv_files():
    with open(args_data_csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Address', 'Args'])
    
    with open(db_values_csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Address', 'Fader', 'dB Value'])
    
    with open(rta_db_values_csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Frequency Band', 'dB Value'])

args_data_csv_file_path = 'args_data.csv'
db_values_csv_file_path = 'db_values.csv'
rta_db_values_csv_file_path = 'rta_db_values.csv'

# keep mixer awake by sending xremote and messages to be received
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

# subscribtion and renewal of RTA data (/meters/15)
def subscribe_and_renew_rta():
    """Subscribes to RTA data and periodically renews the subscription."""
    logging.debug("Subscribing to meters/15")
    client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 40]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
    logging.debug("Subscription message sent")
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        logging.debug("Renewing subscription to meters/15")
        client.send_message("/renew", [""])

# grabs rta data to process into dB values (102 data points)
def process_rta_data(address, *args):
    print(f"Entered process_rta_data with address: {address} and args: {args}")
    if not args:
        logging.error(f"No RTA data received on {address}")
        return

    rta_blob = args[0]
    print(f"RTA blob size: {len(rta_blob)}")
    print(f"RTA blob content: {rta_blob.hex()}")

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
            # Adjusting for signed values
            if short_int1 >= 0x8000: short_int1 -= 0x10000
            if short_int2 >= 0x8000: short_int2 -= 0x10000
            # Convert to dB values
            db_value1 = short_int1 / 256.0
            db_value2 = short_int2 / 256.0
            db_values.append(db_value1)
            db_values.append(db_value2)

        # Print the dB values for the RTA frequency bands
        for i, db_value in enumerate(db_values[2:]):
            print(f"{address} ~ RTA Frequency Band {i+1}: {db_value} dB")

        with open(rta_db_values_csv_file_path, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for i, db_value in enumerate(db_values[2:]):
                csvwriter.writerow([f'Band {i+1}', db_value])
    except Exception as e:
        logging.error(f"Error processing RTA data: {e}")

    # Save args to CSV file
"""     with open(rta_db_values_csv_file_path, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        # Convert args to string for easy CSV writing, or handle individually
        args_str = ', '.join(str(arg) for arg in args)
        csvwriter.writerow([address, args_str]) """

# data points from mixer to convert to dB (fader)
fader_positions = np.array([0.0000, 0.2502, 0.5005, 0.6256, 0.6999, 0.7478, 0.8250, 0.9003, 0.9501, 1.0000])
db_values = np.array([-90.0, -30.0, -10.0, -5.0, -2.0, 0.0, 3.0, 6.0, 8.0, 10.0])

# fit a polynomial to the data points
p = Polynomial.fit(fader_positions, db_values, deg=4)

# handler for converting to dB and printing all fader type data
def print_fader_handler(address, *args):
    if args and isinstance(args[0], float):
        float_value = args[0]
        db_value = p(float_value)
        print(f"[{address}] ~ Fader value: {db_value:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")
    with open(db_values_csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([address, 'Fader', db_value])


# if message received does not have a mapped handler, use default
def default_handler(address, *args):
    """Default handler for all messages."""
    logging.info(f"Received fader message on {address}. Args: {args}")
    # Modify default_handler to write args data to CSV
    with open(args_data_csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([address, args])


args_data_csv_file_path = 'args_data.csv'
db_values_csv_file_path = 'db_values.csv'

# Initialize CSV files with headers
with open(args_data_csv_file_path, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Address', 'Args'])

with open(db_values_csv_file_path, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Address', 'Frequency Band', 'dB Value'])

if __name__ == "__main__":
    initialize_csv_files()
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

    # start the RTA subscription and renewal in a separate thread
    rta_subscription_thread = threading.Thread(target=subscribe_and_renew_rta, daemon=True)
    rta_subscription_thread.start()

    server.serve_forever()