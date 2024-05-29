from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import time
import threading
import struct
import select
import sys
from Data import frequencies, bandsRangeRTA, bandRanges, qValues, eqGainValues, dataRTA, gainOffset, qLimits, gainMultis
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import numpy as np
from queue import Queue, Empty

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
            #print(f"Discovered mixer at {addr[0]}")
            return addr[0], data
    except Exception as e:
        pass


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
                #print(f"Discovered mixer at {ip} with details: {details}")

    return discIPs

# keep mixer awake by sending xremote and messages to be received
def keepMixerAwake():
    print("Sending keep-alive messages to Behringer")

    while True:
        client.send_message('/xremote', None)
        client.send_message('/xinfo', None)
        #client.send_message('/ch/01/mix/fader', None)
        #client.send_message('/ch/01/dyn/mgain', None)
        time.sleep(3)

# subscribtion and renewal of RTA data (/meters/15)
def subRenewRTA():

    while True:
        client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 99]) # 80 indicates 3 updates, see page 17 of o32-osc.pdf
        time.sleep(0.1)  # renew just before the 10-second timeout

receivedFirstRTA = False
queueRTA = Queue()

# grabs rta data to process into dB values (102 data points)
def handlerRTA(address, *args):
    global receivedFirstRTA

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
            dbValue1 = (shortINT1 / 256.0) + gainOffset
            dbValue2 = (shortINT2 / 256.0) + gainOffset
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

        # Set the flag to True after receiving the first RTA data
        if not receivedFirstRTA:
            receivedFirstRTA = True

        # Put the received RTA data in the queue
        queueRTA.put(dataRTA)

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

# Function to update the plot with the latest dB values
def updatePlot():
    try:
        # Get the latest RTA data from the queue if available
        latestData = queueRTA.get_nowait()
        
        # Define thresholds for coloring
        threshUpper = -10
        threshMid = -18
        threshLower = -45
        # Update the plot with the latest dB values
        for freq in frequencies:
            dbValues = latestData.get(freq, [-90])
            dbLatest = dbValues[-1] if dbValues else -90
            color = 'r' if dbLatest >= threshUpper else 'y' if threshMid <= dbLatest < threshUpper else 'g' if dbLatest >= threshLower <= threshMid else 'b'
            if freq in bars:
                bars[freq].setData([freq, freq], [dbLatest, -90])
                bars[freq].setPen(pg.mkPen(color, width=3))
            else:
                bars[freq] = plot.plot([freq, freq], [dbLatest, -90], pen=pg.mkPen(color, width=3))
    except Empty:
        # If there's no data in the queue, don't update the plot
        pass

# set logarithmic ticks for the x-axis
def setLogTicks():
    ticks = np.logspace(np.log10(frequencies[0]), np.log10(frequencies[-1]), num=20)
    labelTicks = [(tick, f"{int(tick)} Hz") for tick in ticks]
    plot.getAxis('bottom').setTicks([labelTicks])

# Function to check if there are sufficient data points for a given frequency
def hasSufficientData(freq):
    """Check if there are at least 10 dB values for the frequency."""
    return len(dataRTA.get(freq, [])) >= 10

# Function to find the highest frequency in a given band
def findHighestFreqinBand(bandName):
    bandRange = bandsRangeRTA.get(bandName)
    if not bandRange:
        return None  # or raise an error if preferred

    lowBound, upBound = bandRange
    maxDB = -90.0
    maxFreq = None

    for freq, dbValues in dataRTA.items():
        if lowBound <= freq <= upBound:
            currentMaxDB = max(dbValues)
            if currentMaxDB > maxDB:
                maxDB = currentMaxDB
                maxFreq = freq

    return maxFreq

# Function to find the highest dB value in a given band
def findHighestDBinBand(bandName):
    bandRange = bandsRangeRTA.get(bandName)
    if not bandRange:
        return None  # or raise an error if preferred

    lowBound, upBound = bandRange
    maxDB = -90.0

    for freq, dbValues in dataRTA.items():
        if lowBound <= freq <= upBound:
            currentMaxDB = max(dbValues)
            if currentMaxDB > maxDB:
                maxDB = currentMaxDB

    return maxDB

# Function to find the closest frequency in a given band
def findClosestFrequency(bandName, targetFreq):
    frequencies = bandRanges.get(bandName, [])
    if not frequencies or targetFreq is None:
        return None  # Proper handling when no frequencies or target frequency is None
    
    # Find the closest frequency and its ID
    closeFreqData = min(frequencies, key=lambda x: abs(x[1] - targetFreq))
    return closeFreqData  # This now returns the tuple (freqID, frequency)

# Function to calculate the gain value for a given dB value, band, and vocal type
def calculateGain(dbValue, band, vocalType):

    # Define the target dB level for flat response
    freqFlat = -45

    # Calculate the distance from the frequency dB to the flat level
    distance = dbValue - freqFlat

    # Get the multiplier based on vocal type and band
    bandMulti = gainMultis.get(vocalType, {}).get(band, -1) # Default to -1 if not found

    # Calculate the gain
    gain = (distance / 10) * bandMulti

    return round(gain, 2)

# Function to find the frequency closest to the target within the list
def findSimilarFrequencies(frequencies, targetFreq):
    """Find the frequency closest to the target within the list."""
    return min(frequencies, key=lambda x: abs(x - targetFreq))

# Function to calculate the Q value for a given frequency and band
def calculateQValue(freq, band):
    # Retrieve the frequency range for the band
    if band not in bandsRangeRTA:
        print(f"Band {band} not found in bandsRangeRTA.")
        return None
    lowBound, upBound = bandsRangeRTA[band]

    # Filter frequencies within the range that have data
    relevantFreqs = {f: dbs for f, dbs in dataRTA.items() if lowBound <= f <= upBound}

    # Check for the maximum dB at the specific frequency
    if freq not in relevantFreqs or not relevantFreqs[freq]:
        print(f"No data or insufficient data for frequency {freq} in band {band}.")
        return None
    maxDbValue = max(relevantFreqs[freq])

    # Count frequencies with dB values within +/- 6 dB of maxDbValue
    similarFreqCount = sum(1 for dbs in relevantFreqs.values() if any(abs(maxDbValue - db) <= 6 for db in dbs))

    # Calculate the Q value
    qMax, qMin = qLimits[band]
    qRange = qMax - qMin
    bandSize = len(relevantFreqs)
    if bandSize == 0:
        print(f"No frequencies with data in band {band}.")
        return None
    qValue = qMax - (similarFreqCount / bandSize) * qRange

    return round(qValue, 2)

# Function to safely get a Q ID value or return a default if None
def getClosestQIDValue(qValue):
    if qValue is None or not qValues:
        return 0.3380  # Define some default QID value that makes sense for your system
    closestQ = min(qValues.keys(), key=lambda k: abs(k - qValue))
    return qValues[closestQ]

# Function to get the closest gain value from the available gain values
def getClosestGainValue(gain, eqGainValues):
    # List of available gain keys
    gainKeys = list(eqGainValues.keys())
    # Find the closest value by minimizing the absolute difference
    closestGain = min(gainKeys, key=lambda k: abs(k - gain))
    return closestGain

# Function to get a valid channel number from the user
def getValidChannel():
    while True:
        channel = input("Enter the channel number from 01 to 32: ")
        if channel.isdigit() and 1 <= int(channel) <= 32:
            return channel.zfill(2)  # Ensures the channel number is formatted with two digits
        else:
            print("Invalid input. Please enter a number from 01 to 32.")

# Function to send all EQ parameters in one command
def sendOSCParameters(channel, eqBand, freqID, gainID, qIDValue):
    """Send OSC message with all EQ parameters in one command, using frequency id and appropriate IDs for gain and Q."""
    client.send_message(f'/ch/{channel}/eq/{eqBand}', [2, freqID, gainID, qIDValue])

# Function to update all bands for a given vocal type and channel
def updateAllBands(vocalType, channel):
    bands = ['Low', 'Low Mid', 'High Mid', 'High']
    
    for index, band in enumerate(bands):
        highestFreq = findHighestFreqinBand(band)
        if highestFreq is None:
            print(f"No data for band {band}. Skipping...")
            continue
        
        highestDB = findHighestDBinBand(band)
        closestFreqData = findClosestFrequency(band, highestFreq)
        if closestFreqData is None:
            print(f"No closest frequency found for band {band}. Skipping...")
            continue
        
        freqID, actualFreq = closestFreqData
        gainValue = calculateGain(highestDB, band, vocalType)
        gainID = eqGainValues[getClosestGainValue(gainValue, eqGainValues)]
        
        qValue = calculateQValue(highestFreq, band)
        qIDValue = getClosestQIDValue(qValue)
        
        # Send combined parameters via OSC
        sendOSCParameters(channel, index + 1, freqID, gainID, qIDValue)  # Send gain ID instead of gain value
        #print(f"Updated {band} band for channel {channel}: Gain {gainValue} dB (ID: {gainID}), Q {qValue} (ID: {qIDValue}), Freq ID {freqID}")

# Function to continuously update all bands
def threadUpdateBand(vocalType, channel):
    print(f"Starting continuous updates for vocal type {vocalType} on channel {channel}...")
    while True:
        updateAllBands(vocalType, channel)
        time.sleep(0.1)  # Pause 0.1 seconds between updates

# main function
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

    # argument parser for IP and port
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
    args = parser.parse_args()

    # map handlers to OSC addresses
    dispatcher = Dispatcher()
    dispatcher.map("/meters", handlerRTA)
    """ dispatcher.map("/*/*/mix/fader", handlerFader)
    dispatcher.map("/*/*/preamp/trim", handlerPreampTrim)
    dispatcher.set_default_handler(handlerDefault) """

    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    print(f"Serving on {server.server_address}")
    client._sock = server.socket

    # start threads for keep alive and RTA subscription
    threadKeepAlive = threading.Thread(target=keepMixerAwake, daemon=True)
    threadKeepAlive.start()

    channel = getValidChannel()  # Get a valid channel number from the user

    threadRTASub = threading.Thread(target=subRenewRTA, daemon=True)
    threadRTASub.start()

    # Initialize the PyQt application
    app = QApplication([])
    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Frequency Response")
    plot = win.addPlot(title="Frequency Response Histogram")
    plot.setLogMode(x=True, y=False)
    plot.setYRange(-90, 0)
    plot.setLabel('bottom', 'Frequency', units='Hz')
    plot.setLabel('left', 'dB Value')

    # Initialize bars dictionary to hold the plot data
    bars = {}

    # Set up logarithmic ticks for the x-axis
    setLogTicks()

    # Set up timer to update plot periodically
    timer = QTimer()
    timer.timeout.connect(updatePlot)
    timer.start(100)  # Update the plot every 500 milliseconds

    # Start a separate thread to run the OSC server
    threadServerOSC = threading.Thread(target=server.serve_forever, daemon=True)
    threadServerOSC.start()

    # Get the vocal type from the user
    print("Select the vocal type:")
    print("1. Low Pitch")
    print("2. High Pitch")
    print("3. Mid Pitch (Flat)")

    try:
        inputVocalType = int(input("Enter the number for the desired vocal type: "))
        vocalTypes = ['Low Pitch', 'High Pitch', 'Mid Pitch']
        vocalType = vocalTypes[inputVocalType - 1]  # Adjust index for zero-based
    except (IndexError, ValueError):
        print("Invalid input. Defaulting to 'Mid Pitch (Flat)'.")
        vocalType = 'Mid Pitch'

    # Start the continuous update in a separate thread
    threadUpdateBands = threading.Thread(target=threadUpdateBand, args=(vocalType, channel), daemon=True)
    threadUpdateBands.start()

    # Start the PyQtGraph Application
    sys.exit(app.exec_())