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

X32_IP = '192.168.1.21'
client = SimpleUDPClient(X32_IP, 10023)

frequencies = [
    20, 21, 22, 24, 26, 28, 30, 32, 34, 36,
    39, 42, 45, 48, 52, 55, 59, 63, 68, 73,
    78, 84, 90, 96, 103, 110, 118, 127, 136, 146,
    156, 167, 179, 192, 206, 221, 237, 254, 272, 292,
    313, 335, 359, 385, 412, 442, 474, 508, 544, 583,
    625, 670, 718, 769, 825, 884, 947, 1020, 1090, 1170,
    1250, 1340, 1440, 1540, 1650, 1770, 1890, 2030, 2180, 2330,
    2500, 2680, 2870, 3080, 3300, 3540, 3790, 4060, 4350, 4670,
    5000, 5360, 5740, 6160, 6600, 7070, 7580, 8120, 8710, 9330,
    10000, 10720, 11490, 12310, 13200, 14140, 15160, 16250, 17410, 18660
]

# Initialize CSV files with headers outside of the functions
def initCSVFiles():
    with open(argsDataCSVPath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Address', 'Args'])
    
    with open(dbValueCSVPath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Address', 'Fader', 'dB Value'])
    
    with open(RTAdbValuePath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Frequency Band', 'dB Value'])

argsDataCSVPath = 'args_data.csv'
dbValueCSVPath = 'db_values.csv'
RTAdbValuePath = 'rta_db_values1.csv'

# keep mixer awake by sending xremote and messages to be received
def keepMixerAwake():
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
def subRenewRTA():
    """Subscribes to RTA data and periodically renews the subscription."""
    logging.debug("Subscribing to meters/15")
    client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 40]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
    logging.debug("Subscription message sent")
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        logging.debug("Renewing subscription to meters/15")
        client.send_message("/renew", [""])

# grabs rta data to process into dB values (102 data points)
def handlerRTA(address, *args):
    print(f"Entered process_rta_data with address: {address} and args: {args}")
    if not args:
        logging.error(f"No RTA data received on {address}")
        return

    blobRTA = args[0]
    print(f"RTA blob size: {len(blobRTA)}")
    print(f"RTA blob content: {blobRTA.hex()}")

    # Calculate the number of 32-bit integers (4 bytes each) in the blob
    dataPoints = len(blobRTA) // 4
    print(f"Number of data points: {dataPoints}")

    try:
        # Dynamically unpack the blob based on its actual size
        ints = struct.unpack(f'<{dataPoints}I', blobRTA)
        dbValues = []
        for intValue in ints:
            # Process each 32-bit integer into two short integers and convert to dB
            shortINT1 = intValue & 0xFFFF
            shortINT2 = (intValue >> 16) & 0xFFFF
            # Adjusting for signed values
            if shortINT1 >= 0x8000: shortINT1 -= 0x10000
            if shortINT2 >= 0x8000: shortINT2 -= 0x10000
            # Convert to dB values
            dbValue1 = (shortINT1 / 256.0) + 24
            dbValue2 = (shortINT2 / 256.0) + 24
            dbValues.append(dbValue1)
            dbValues.append(dbValue2)

        # Print the dB values for the RTA frequency bands
        for i, dbValue in enumerate(dbValues[2:]):
            freqLabel = frequencies[i] if i < len(frequencies) else "Unknown"
            print(f"{address} ~ RTA Frequency {freqLabel}Hz: {dbValue} dB")

        with open(RTAdbValuePath, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for i, dbValue in enumerate(dbValues[2:]):
                freqLabel = frequencies[i] if i < len(frequencies) else "Unknown"
                csvwriter.writerow([f'Band {freqLabel}', dbValue])

    except Exception as e:
        logging.error(f"Error processing RTA data: {e}")

# data points from mixer to convert to dB (fader)
faderPOS = np.array([0.0000, 0.2502, 0.5005, 0.6256, 0.6999, 0.7478, 0.8250, 0.9003, 0.9501, 1.0000])
dbValues = np.array([-90.0, -30.0, -10.0, -5.0, -2.0, 0.0, 3.0, 6.0, 8.0, 10.0])

# fit a polynomial to the data points
p = Polynomial.fit(faderPOS, dbValues, deg=4)

# handler for converting to dB and printing all fader type data
def handlerFader(address, *args):
    if args and isinstance(args[0], float):
        float_value = args[0]
        db_value = p(float_value)
        print(f"[{address}] ~ Fader value: {db_value:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")
    with open(dbValueCSVPath, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([address, 'Fader', db_value])


# if message received does not have a mapped handler, use default
def handlerDefault(address, *args):
    """Default handler for all messages."""
    logging.info(f"Received fader message on {address}. Args: {args}")
    # Modify default_handler to write args data to CSV
    with open(argsDataCSVPath, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([address, args])


argsDataCSVPath = 'args_data.csv'
dbValueCSVPath = 'db_values.csv'

# Initialize CSV files with headers
with open(argsDataCSVPath, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Address', 'Args'])

with open(dbValueCSVPath, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Address', 'Frequency Band', 'dB Value'])

if __name__ == "__main__":
    initCSVFiles()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.map("/meters", handlerRTA)
    dispatcher.map("/*/*/mix/fader", handlerFader)
    dispatcher.set_default_handler(handlerDefault)

    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    logging.info(f"Serving on {server.server_address}")
    client._sock = server.socket

    keep_alive_thread = threading.Thread(target=keepMixerAwake, daemon=True)
    keep_alive_thread.start()

    # start the RTA subscription and renewal in a separate thread
    rta_subscription_thread = threading.Thread(target=subRenewRTA, daemon=True)
    rta_subscription_thread.start()

    server.serve_forever()