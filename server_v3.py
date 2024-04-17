from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import time
import threading
import struct
import select
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import numpy as np

# hardcoded frequencies based on /meters/15 data
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

# check a single IP for a mixer
def checkMixerIP(ip, port):
    try:
        # start a temporary client to search for mixers
        tempClient = SimpleUDPClient(ip, port)
        tempClient.send_message('/xinfo', None)

        # set a timeout for the socket to wait for a response
        ready = select.select([tempClient._sock], [], [], 0.1)
        if ready[0]:
            data, addr = tempClient._sock.recvfrom(1024)
            print(f"Discovered mixer at {addr[0]}")
            return addr[0], data
    except Exception as e:
        print(f"No mixer at {ip}: {e}")
    return None

def discMixers():
    discIPs = {}
    discPort = 10023  # The port where mixers listen for OSC messages
    subnets = ["192.168.10", "192.168.1"]

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = {}
        for subnet in subnets:
            for i in range(256):
                ipAddr = f"{subnet}.{i}"
                futures[executor.submit(checkMixerIP, ipAddr, discPort)] = ipAddr
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                ip, rawData = result
                details = handlerXInfo(rawData)
                discIPs[ip] = details
                print(f"Discovered mixer at {ip} with details: {details}")

    return discIPs

# keep mixer awake by sending xremote and messages to be received
def keepMixerAwake():
    print("Sending keep-alive messages to Behringer")

    while True:
        client.send_message('/xremote', None)
        client.send_message('/xinfo', None)
        client.send_message('/ch/01/mix/fader', None)
        client.send_message('/ch/01/dyn/mgain', None)
        time.sleep(3)

# subscribtion and renewal of RTA data (/meters/15)
def subRenewRTA():

    while True:
        client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 99]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
        time.sleep(1)  # renew just before the 10-second timeout

# offest for dB values
gain = 38
# Initialize dataRTA with all frequencies set to a default list with a placeholder dB value
dataRTA = {freq: [-90] for freq in frequencies}

# grabs rta data to process into dB values (102 data points)
def handlerRTA(address, *args):
    if not args:
        print(f"No RTA data received on {address}")
        return

    blobRTA = args[0]
    dataPoints = len(blobRTA) // 4

    try:
        # dynamically unpack the blob based on its actual size
        ints = struct.unpack(f'<{dataPoints}I', blobRTA)
        dbValues = []
        for intValue in ints:
            # process each 32-bit integer into two short integers and convert to dB
            shortINT1 = intValue & 0xFFFF
            shortINT2 = (intValue >> 16) & 0xFFFF
            # adjusting for signed values
            if shortINT1 >= 0x8000: shortINT1 -= 0x10000
            if shortINT2 >= 0x8000: shortINT2 -= 0x10000
            # convert to dB values
            dbValue1 = (shortINT1 / 256.0) + gain
            dbValue2 = (shortINT2 / 256.0) + gain
            dbValues.append(dbValue1)
            dbValues.append(dbValue2)

        # process the dB values into the dataRTA dictionary
        for i, dbValue in enumerate(dbValues[2:len(frequencies)+2]):
            freqLabel = frequencies[i] if i < len(frequencies) else "Unknown"
            if freqLabel in dataRTA:
                dataRTA[freqLabel].append(dbValue)
                # Keep only the last 10 values
                if len(dataRTA[freqLabel]) > 10:
                    dataRTA[freqLabel].pop(0)
            else:
                dataRTA[freqLabel] = [dbValue]
            print(f"{address} ~ RTA Frequency {freqLabel}Hz: {dbValue} dB")

        print(f"{dataRTA}")

    except Exception as e:
        print(f"Error processing RTA data: {e}")

# handler for converting to dB and printing all fader type data, based on C code in x32-osc.pdf (page 133)
def handlerFader(address, *args):
    if args and isinstance(args[0], float):
        f = args[0]
        if f > 0.75:
            d = f * 40.0 - 30.0  # max dB value: +10
        elif f > 0.5:
            d = f * 80.0 - 50.0
        elif f > 0.25:
            d = f * 160.0 - 70.0
        elif f >= 0.0:
            d = f * 480.0 - 90.0  # min dB value: -90 or -oo
        else:
            print(f"Invalid fader value: {f}")
            return
        print(f"[{address}] ~ Fader value: {d:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

# Function to convert float value to dB for preamp trim
def floatToDB(trimFloat):
    # Define the scale boundaries for preamp trim
    floatMin = 0.0
    floatMax = 0.25
    dbMin = -18.0
    dbMax = 18.0

    # Linear interpolation within the range
    if 0 <= trimFloat <= 0.25:
        dbValue = (trimFloat - floatMin) * (dbMax - dbMin) / (floatMax - floatMin) + dbMin
    else:
        # Handle values outside the range, if any
        dbValue = "Out of range"
    return dbValue

# Handler for the preamp trim messages
def handlerPreampTrim(address, *args):
    if args and isinstance(args[0], float):
        trimFloat = args[0]  # Assuming the trim float value is the first argument
        dbValue = floatToDB(trimFloat)
        if isinstance(dbValue, str):
            print(f"[{address}] ~ Preamp trim value: {dbValue}")
        else:
            print(f"[{address}] ~ Preamp trim value: {dbValue:.2f} dB")
    else:
        print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

# handler for xinfo data
def handlerXInfo(data):
    try:
        # look for the first null character which ends the address pattern
        addressEnd = data.find(b'\x00')
        data = data[(addressEnd + 4) & ~3:]  # move past the address and align to the next 4-byte boundary

        # extract type tags starting right after the first comma
        startTypeTag = data.find(b',') + 1
        endTypeTag = data.find(b'\x00', startTypeTag)
        typeTag = data[startTypeTag:endTypeTag].decode()

        # move to the argument data
        data = data[(endTypeTag + 4) & ~3:]  # align to 4-byte boundary

        # process arguments according to type tags
        arguments = []
        for tag in typeTag:
            if tag == 's':  # check if string
                endString = data.find(b'\x00')
                argument = data[:endString].decode()
                arguments.append(argument)
                data = data[(endString + 4) & ~3:]  # move past the string and align

        return " | ".join(arguments)
    except Exception as e:
        print(f"Error parsing data: {e}")
        return "Error parsing data"

# if message received does not have a mapped handler, use default
def handlerDefault(address, *args):
    print(f"Received fader message on {address}. Args: {args}")

app = QApplication([])
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Frequency Response")
plot = win.addPlot(title="Frequency Response Histogram")
plot.setLogMode(x=True, y=False)
plot.setYRange(-90, 0)
plot.setLabel('bottom', 'Frequency', units='Hz')
plot.setLabel('left', 'dB Value')
bars = []

# update the plot with the latest dB values
def updatePlot():
    for freq in frequencies:
        dbValues = dataRTA.get(freq, [-90])
        dbLatest = dbValues[-1] if dbValues else -90
        color = 'r' if dbLatest >= -18 else 'y' if -22.5 <= dbLatest < -18 else 'b'
        if freq in bars:
            bars[freq].setData([freq, freq], [dbLatest, -90])
            bars[freq].setPen(pg.mkPen(color, width=3))
        else:
            bars[freq] = plot.plot([freq, freq], [dbLatest, -90], pen=pg.mkPen(color, width=3))

# set logarithmic ticks for the x-axis
def setLogTicks():
    # Use logarithmic spacing or pick specific frequencies that are representative
    ticks = np.logspace(np.log10(frequencies[0]), np.log10(frequencies[-1]), num=20)
    tick_labels = [(tick, f"{int(tick)} Hz") for tick in ticks]
    plot.getAxis('bottom').setTicks([tick_labels])


if __name__ == "__main__":
    # search mixers on the network
    mixers = discMixers()
    if not mixers:
        print("No mixers found.")
        exit()

    # options for user
    for idx, (ip, details) in enumerate(mixers.items(), start=1):
        print(f"{idx}: Mixer at IP {ip} with details: {details}")

    # user selects mixer
    chosen = int(input("Select the number for the desired mixer: ")) - 1
    chosenIP = list(mixers.keys())[chosen]

    # set the mixer IP
    X32IP = chosenIP
    client = SimpleUDPClient(X32IP, 10023)

    setLogTicks()

    # argument parser for IP and port
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
    args = parser.parse_args()

    # map handlers to OSC addresses
    dispatcher = Dispatcher()
    dispatcher.map("/meters", handlerRTA)
    dispatcher.map("/*/*/mix/fader", handlerFader)
    dispatcher.map("/*/*/preamp/trim", handlerPreampTrim)
    dispatcher.set_default_handler(handlerDefault)

    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    print(f"Serving on {server.server_address}")
    client._sock = server.socket

    # start threads for keep alive and RTA subscription
    threadKeepAlive = threading.Thread(target=keepMixerAwake, daemon=True)
    threadKeepAlive.start()

    threadRTASub = threading.Thread(target=subRenewRTA, daemon=True)
    threadRTASub.start()

    timer = QTimer()
    timer.timeout.connect(updatePlot)
    timer.start(500)  # Update the plot every second

    # Start the PyQtGraph Application and OSC server
    sys.exit(app.exec_())