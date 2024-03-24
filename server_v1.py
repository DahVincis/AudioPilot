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

X32IP = '192.168.1.24'
client = SimpleUDPClient(X32IP, 10023)

# keep mixer awake by sending xremote and messages to be received
def keepMixerAwake():
    while True:
        logging.debug("Sending keep-alive messages to Behringer")
        client.send_message('/xremote', None)
        client.send_message('/ch/04/mix/fader', None)
        client.send_message('/ch/05/mix/fader', None)
        client.send_message('/ch/06/mix/fader', None)
        client.send_message('/ch/07/mix/fader', None)
        client.send_message('/ch/08/mix/fader', None)
        time.sleep(3)

# subscribtion and renewal of RTA data (/meters/15)
def subRenewRTA():
    logging.debug("Subscribing to meters/15")
    client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 40]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
    logging.debug("Subscription message sent")
    while True:
        time.sleep(9)  # Renew just before the 10-second timeout
        logging.debug("Renewing subscription to meters/15")
        client.send_message("/renew", [""])

# grabs rta data to process into dB values (102 data points)
def handlerRTA(address, *args):
    print(f"Entered handlerRTA with address: {address} and args: {args}")
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
            dbValue1 = shortINT1 / 256.0
            dbValue2 = shortINT2 / 256.0
            dbValues.append(dbValue1)
            dbValues.append(dbValue2)

        # Print the dB values for the RTA frequency bands
        for i, dbValue in enumerate(dbValues):
            print(f"{address} ~ RTA Frequency Band {i+1}: {dbValue} dB")
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
        floatVal = args[0]
        dbVal = p(floatVal)
        print(f"[{address}] ~ Fader value: {dbVal:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

# if message received does not have a mapped handler, use default
def handlerDefault(address, *args):
    logging.info(f"Received fader message on {address}. Args: {args}")

if __name__ == "__main__":
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

    threadKeepAlive = threading.Thread(target=keepMixerAwake, daemon=True)
    threadKeepAlive.start()

    # start the RTA subscription and renewal in a separate thread
    threadRTASub = threading.Thread(target=subRenewRTA, daemon=True)
    threadRTASub.start()

    server.serve_forever()