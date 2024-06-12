import threading
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from queue import Empty
import sys
from pythonosc.udp_client import SimpleUDPClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import select

from Data import frequencies, dataRTA, bandsRangeRTA, bandRanges, qLimits, gainMultis, eqGainValues, qValues, queueRTA

class ApplicationManager:
    def __init__(self, client, server):
        self.client = client
        self.server = server

    def run(self, mixerIP):
        from osc_handlers import RTASubscriber
        mixerManager = MixerManager(self.client)
        threadKeepAlive = threading.Thread(target=mixerManager.keepMixerAwake, daemon=True)
        threadKeepAlive.start()

        subscriberRTA = RTASubscriber(self.client)
        threadRTASub = threading.Thread(target=subscriberRTA.subRenewRTA, daemon=True)
        threadRTASub.start()

        app = QApplication([])
        from ui import AudioPilotUI  # local import to avoid circular dependency
        mixerUI = AudioPilotUI(mixerIP, self.client)

        plotMgr = PlotManager(mixerUI.plot)
        mixerUI.plotMgr = plotMgr  # assign the plot manager to the UI

        threadServerOSC = threading.Thread(target=self.server.serve_forever, daemon=True)
        threadServerOSC.start()

        sys.exit(app.exec())

class MixerManager:
    def __init__(self, client):
        self.client = client

    def keepMixerAwake(self):
        while True:
            self.client.send_message('/xremote', None)
            time.sleep(9)

class PlotManager:
    def __init__(self, plot):
        self.plot = plot
        self.bars = {}
        self.initializeBars()
        self.setCustomTicks()

    def initializeBars(self):
        # Initialize bars with default values
        for freq in frequencies:
            self.bars[freq] = self.plot.plot([freq, freq], [-90, -90], pen=pg.mkPen('b', width=3))

    def updatePlot(self):
        try:
            latestData = queueRTA.get_nowait()
            threshUpper = -10
            threshMid = -18
            threshLower = -45
            
            # Prepare data for batch update
            freqData = []
            dbData = []
            colors = []

            for freq in frequencies:
                dbValues = latestData.get(freq, [-90])
                dbLatest = dbValues[-1] if dbValues else -90
                if dbLatest == -90:
                    continue  # Skip if no audio

                color = 'r' if dbLatest >= threshUpper else 'y' if threshMid <= dbLatest < threshUpper else 'g' if dbLatest >= threshLower <= threshMid else 'b'
                freqData.append([freq, freq])
                dbData.append([dbLatest, -90])
                colors.append(color)

            # Update all bars in a batch
            for i, freq in enumerate(frequencies):
                if freq in freqData:
                    self.bars[freq].setData(freqData[i], dbData[i], pen=pg.mkPen(colors[i], width=3))
                else:
                    self.bars[freq].setData([freq, freq], [-90, -90], pen=pg.mkPen('b', width=3))

        except Empty:
            pass

    def setCustomTicks(self):
        # Select a subset of frequencies for the x-axis ticks
        major_ticks = [20, 40, 60, 80, 100, 200, 300, 400, 600, 800, 1000, 2000, 3000, 4000, 5000, 8000, 10000, 20000]
        labelTicks = [(freq, f"{freq/1000:.1f}kHz" if freq >= 1000 else f"{int(freq)} Hz") for freq in major_ticks]
        self.plot.getAxis('bottom').setTicks([labelTicks])

class BandManager:
    def __init__(self, client):
        self.client = client

    def hasSufficientData(self, freq):
        return len(dataRTA.get(freq, [])) >= 10

    def findHighestFreqinBand(self, bandName):
        bandRange = bandsRangeRTA.get(bandName)
        if not bandRange:
            return None
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

    def findLowestFreqinBand(self, bandName):
        bandRange = bandsRangeRTA.get(bandName)
        if not bandRange:
            return None
        lowBound, upBound = bandRange
        minDB = 0.0
        minFreq = None
        for freq, dbValues in dataRTA.items():
            if lowBound <= freq <= upBound:
                currentMinDB = min(dbValues)
                if currentMinDB < minDB:
                    minDB = currentMinDB
                    minFreq = freq
        return minFreq

    def findHighestDBinBand(self, bandName):
        bandRange = bandsRangeRTA.get(bandName)
        if not bandRange:
            return None
        lowBound, upBound = bandRange
        maxDB = -90.0
        for freq, dbValues in dataRTA.items():
            if lowBound <= freq <= upBound:
                currentMaxDB = max(dbValues)
                if currentMaxDB > maxDB:
                    maxDB = currentMaxDB
        return maxDB

    def findLowestDBinBand(self, bandName):
        bandRange = bandsRangeRTA.get(bandName)
        if not bandRange:
            return None
        lowBound, upBound = bandRange
        minDB = None
        for freq, dbValues in dataRTA.items():
            if lowBound <= freq <= upBound:
                filteredDBValues = [db for db in dbValues if db > -90]
                if filteredDBValues:
                    currentMinDB = min(filteredDBValues)
                    if minDB is None or currentMinDB < minDB:
                        minDB = currentMinDB
        return minDB

    def findClosestFrequency(self, bandName, targetFreq):
        frequencies = bandRanges.get(bandName, [])
        if not frequencies or targetFreq is None:
            return None
        closeFreqData = min(frequencies, key=lambda x: abs(x[1] - targetFreq))
        return closeFreqData

    def calculateGain(self, dbValue, band, vocalType):
        freqFlat = -45
        distance = dbValue - freqFlat
        bandMulti = gainMultis.get(vocalType, {}).get(band, -1)
        gain = (distance / 10) * bandMulti
        return round(gain, 2)

    def calculateGainForLowestDB(self, dbValue, band, vocalType):
        freqFlat = -45
        distance = dbValue - freqFlat
        bandMulti = gainMultis.get(vocalType, {}).get(band, 0)
        gain = np.log(distance - freqFlat * 2) * bandMulti
        return round(gain, 2)

    def calculateQValue(self, freq, band):
        if band not in bandsRangeRTA:
            print(f"Band {band} not found in bandsRangeRTA.")
            return None
        lowBound, upBound = bandsRangeRTA[band]
        relevantFreqs = {f: dbs for f, dbs in dataRTA.items() if lowBound <= f <= upBound}
        if freq not in relevantFreqs or not relevantFreqs[freq]:
            print(f"No data or insufficient data for frequency {freq} in band {band}.")
            return None
        maxDbValue = max(relevantFreqs[freq])
        similarFreqCount = sum(1 for dbs in relevantFreqs.values() if any(abs(maxDbValue - db) <= 5 for db in dbs))
        qMax, qMin = qLimits[band]
        qRange = qMax - qMin
        bandSize = len(relevantFreqs)
        if bandSize == 0:
            print(f"No frequencies with data in band {band}.")
            return None
        qValue = qMax - (similarFreqCount / bandSize) * qRange
        return round(qValue, 2)

    def getClosestQIDValue(self, qValue):
        if qValue is None or not qValues:
            return 0.3380
        closestQ = min(qValues.keys(), key=lambda k: abs(k - qValue))
        return qValues[closestQ]

    def getClosestGainValue(self, gain, eqGainValues):
        gainKeys = list(eqGainValues.keys())
        closestGain = min(gainKeys, key=lambda k: abs(k - gain))
        return closestGain

    def sendOSCParameters(self, channel, eqBand, freqID, gainID, qIDValue):
        self.client.send_message(f'/ch/{channel + 1}/eq/{eqBand}', [2, freqID, gainID, qIDValue])

    def updateAllBands(self, vocalType, channel):
        bands = ['Low', 'Low Mid', 'High Mid', 'High']
        for index, band in enumerate(bands):
            multiplier = gainMultis.get(vocalType, {}).get(band, 0)
            if multiplier > 0:
                targetDB = self.findLowestDBinBand(band)
                targetFreq = self.findLowestFreqinBand(band)
            else:
                targetDB = self.findHighestDBinBand(band)
                targetFreq = self.findHighestFreqinBand(band)
            if targetDB is None or targetFreq is None:
                print(f"No dB data or frequency data for band {band}. Skipping...")
                continue
            freqID, actualFreq = self.findClosestFrequency(band, targetFreq)
            if freqID is None:
                print(f"No closest frequency found for band {band}. Skipping...")
                continue
            if multiplier > 0:
                gainValue = self.calculateGainForLowestDB(targetDB, band, vocalType)
            else:
                gainValue = self.calculateGain(targetDB, band, vocalType)
            gainID = eqGainValues[self.getClosestGainValue(gainValue, eqGainValues)]
            qValue = self.calculateQValue(targetFreq, band)
            qIDValue = self.getClosestQIDValue(qValue)
            self.sendOSCParameters(channel, index + 1, freqID, gainID, qIDValue)

    def threadUpdateBand(self, vocalType, channel):
        print(f"Starting continuous updates for vocal type {vocalType} on channel {channel}...")
        while True:
            if not self.band_manager_thread_running:
                break
            self.updateAllBands(vocalType, channel)
            time.sleep(0.3)

class MixerDiscovery:
    def __init__(self, port=10023):
        self.port = port
        self.subnets = ["192.168.10", "192.168.1", "192.168.56"]
        self.discovery_running = True  # Add a flag to control discovery

    def checkMixerIP(self, ip):
        if not self.discovery_running:
            return None
        try:
            tempClient = SimpleUDPClient(ip, self.port)
            tempClient.send_message('/xinfo', None)
            ready = select.select([tempClient._sock], [], [], 0.1)
            if ready[0]:
                data, addr = tempClient._sock.recvfrom(1024)
                return addr[0], data
        except Exception:
            pass

    def discoverMixers(self):
        from osc_handlers import FaderHandler
        discIPs = {}
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(self.checkMixerIP, f"{subnet}.{i}"): f"{subnet}.{i}" for subnet in self.subnets for i in range(256)}
            for future in as_completed(futures):
                if not self.discovery_running:
                    break
                result = future.result()
                if result:
                    ip, rawData = result
                    details = FaderHandler().handlerXInfo(rawData)
                    discIPs[ip] = details
        return discIPs

    def stopDiscovery(self):
        self.discovery_running = False  # Method to stop discovery
