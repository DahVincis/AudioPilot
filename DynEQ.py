from Server import client
from Data import dataRTA, bandsRangeRTA, bandRanges, qValues, eqGainValues

def hasSufficientData(freq):
    """Check if there are at least 10 dB values for the frequency."""
    return len(dataRTA.get(freq, [])) >= 10

def findHighestFreqinBand(bandName):
    bandRange = bandsRangeRTA.get(bandName)
    if not bandRange:
        return None  # or raise an error if preferred

    lowBound, upBound = bandRange
    maxDB = float('-inf')
    maxFreq = None

    for freq, dbValues in dataRTA.items():
        if lowBound <= freq <= upBound:
            currentMaxDB = max(dbValues)
            if currentMaxDB > maxDB:
                maxDB = currentMaxDB
                maxFreq = freq

    return maxFreq

def findHighestDBinBand(bandName):
    bandRange = bandsRangeRTA.get(bandName)
    if not bandRange:
        return None  # or raise an error if preferred

    lowBound, upBound = bandRange
    maxDB = float('-inf')

    for freq, dbValues in dataRTA.items():
        if lowBound <= freq <= upBound:
            currentMaxDB = max(dbValues)
            if currentMaxDB > maxDB:
                maxDB = currentMaxDB

    return maxDB

def findClosestFrequency(bandName, targetFreq):
    frequencies = bandRanges.get(bandName, [])
    if not frequencies or targetFreq is None:
        return None  # Proper handling when no frequencies or target frequency is None
    
    # Find the closest frequency and its ID
    closeFreqData = min(frequencies, key=lambda x: abs(x[1] - targetFreq))
    return closeFreqData  # This now returns the tuple (freqID, frequency)

def calculateGain(dbValue, band, vocalType):
    # Define gain multipliers for different vocal types and bands
    gainMultis = {
        'Low Pitch': {'Low': 1.0, 'Low Mid': 0.8, 'High Mid': 1.2, 'High': 1.2},
        'High Pitch': {'Low': 0.8, 'Low Mid': 0.7, 'High Mid': 0.6, 'High': 0.7},
        'Mid Pitch': {'Low': 0.9, 'Low Mid': 0.85, 'High Mid': 1.1, 'High': 0.9}
    }

    # Define the target dB level for flat response
    freqFlat = -45

    # Calculate the distance from the frequency dB to the flat level
    distance = dbValue - freqFlat

    # Get the multiplier based on vocal type and band
    bandMulti = gainMultis.get(vocalType, {}).get(band, 1)

    # Calculate the gain
    gain = (distance / 10) * bandMulti

    return round(gain, 2)

def calculateQValue(freq, band):
    # Parameters for each band
    qLimits = {
        'Low': (3.0, 7.0),
        'Low Mid': (2.5, 6.0),
        'High Mid': (2.0, 5.5),
        'High': (1.5, 4.5)
    }

    if band not in bandRanges or band not in qLimits:
        return None

    frequencies = [f[1] for f in bandRanges[band]]
    bandSize = len(frequencies)
    qMax, qMin = qLimits[band]
    qLim = qMax - qMin

    # Get dB values for the selected frequency
    dbValue = max(dataRTA.get(freq, []))
    # Count frequencies within the same dB range (-/+ 20 dB)
    freqSize = sum(1 for f in frequencies if f in dataRTA and any(abs(dbValue - db) <= 20 for db in dataRTA[f]))

    # Calculate the Q value
    qValue = freqSize * (qLim / bandSize)

    return round(qValue + qMin, 2)

def getClosestQIDValue(qValue):
    """Return the closest Q OSC float value from the dictionary based on the provided Q value."""
    if not qValues:  # Check if qValues is empty or undefined
        return None
    closestQ = min(qValues.keys(), key=lambda k: abs(k - qValue))
    return qValues[closestQ]


def getClosestGainHex(gainValue):
    """Return the closest gain hexadecimal value from the dictionary based on the provided gain value."""
    if not eqGainValues:  # Check if eqGainValues is empty or undefined
        return None
    # Ensure gain_value is float for comparison
    gainValue = float(gainValue)
    closestGain = min(eqGainValues.keys(), key=lambda k: abs(k - gainValue))
    return eqGainValues[closestGain]

def getValidChannel():
    while True:
        channel = input("Enter the channel number from 01 to 32: ")
        if channel.isdigit() and 1 <= int(channel) <= 32:
            return channel.zfill(2)  # Ensures the channel number is formatted with two digits
        else:
            print("Invalid input. Please enter a number from 01 to 32.")

def sendOSCParameters(channel, eqBand, freqID, gainHex, qIDValue):
    """Send OSC message with all EQ parameters in one command, using frequency id."""
    formatFreqID = round(freqID, 4)  # Ensure it's a float with four decimal places
    client.send_message(f'/ch/{channel}/eq/{eqBand}', [2, formatFreqID, gainHex, qIDValue])
    print(f"Sent OSC message to /ch/{channel}/eq/{eqBand} with parameters: Type 2, Frequency ID {formatFreqID}, Gain {gainHex}, Q {qIDValue}")

def updateAllBands(vocalType, channel):
    bands = ['Low', 'Low Mid', 'High Mid', 'High']
    
    for band in bands:
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
        qValue = calculateQValue(highestFreq, band)
        
        gainHex = getClosestGainHex(gainValue)
        qIDValue = getClosestQIDValue(qValue)
        
        # Send combined parameters via OSC
        sendOSCParameters(channel, band, freqID, gainHex, qIDValue)
        print(f"Updated {band} band for channel {channel}: Gain {gainHex}, Q {qIDValue}, Freq ID {freqID}")