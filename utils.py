import threading
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from queue import Empty
import sys
from pythonosc.udp_client import SimpleUDPClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import select
import logging

logging.basicConfig(level=logging.DEBUG)


from Data import frequencies, dataRTA, bandsRangeRTA, bandRanges, qLimits, gainMultis, eqGainValues, qValues, queueRTA

class ApplicationManager:
    def __init__(self, client, server, mixerName):
        self.client = client
        self.server = server
        self.mixerName = mixerName

    def run(self):
        from osc_handlers import RTASubscriber
        mixerManager = MixerManager(self.client)
        threadKeepAlive = threading.Thread(target=mixerManager.keepMixerAwake, daemon=True)
        threadKeepAlive.start()

        subscriberRTA = RTASubscriber(self.client)
        threadRTASub = threading.Thread(target=subscriberRTA.subRenewRTA, daemon=True)
        threadRTASub.start()

        app = QApplication([])
        from ui import AudioPilotUI  # local import to avoid circular dependency
        mixerUI = AudioPilotUI(self.mixerName, self.client)
        mixerUI.show()

        plotMgr = PlotManager(mixerUI.plot)
        mixerUI.plotMgr = plotMgr  # assign the plot manager to the UI

        sys.exit(app.exec())

class MixerManager:
    def __init__(self, client):
        self.client = client

    def keepMixerAwake(self):
        while True:
            self.client.send_message('/xremote', None)
            time.sleep(3)

class PlotManager(QObject):
    plotDataUpdated = pyqtSignal(list)

    def __init__(self, plot):
        super().__init__()
        self.plot = plot
        self.bars = {}
        self.executor = None
        self.lock = threading.Lock()
        self.timer = QTimer()
        self.timer.timeout.connect(self.updatePlot)
        self.plottingActive = False
        self.plotDataUpdated.connect(self.updatePlotUI)

    def start(self):
        if not self.plottingActive:
            print("Starting the plotting timer...")
            self.executor = ThreadPoolExecutor(max_workers=20)
            self.plottingActive = True
            self.timer.start(200)

    def updatePlot(self):
        if self.executor:
            future = self.executor.submit(self.processPlotData)
            future.add_done_callback(self.updatePlotCallback)

    def processPlotData(self):
        try:
            latestData = queueRTA.get_nowait()
            threshUpper = -10
            threshMid = -18
            threshLower = -45
            plot_data = []
            for freq in frequencies:
                dbValues = latestData.get(freq, [-90])
                dbLatest = dbValues[-1] if dbValues else -90
                color = 'r' if dbLatest >= threshUpper else 'y' if threshMid <= dbLatest < threshUpper else 'g' if dbLatest >= threshLower <= threshMid else 'b'
                plot_data.append((freq, dbLatest, color))
            return plot_data
        except Empty:
            return []

    def updatePlotCallback(self, future):
        try:
            plotData = future.result()
            self.plotDataUpdated.emit(plotData)
        except Exception as e:
            print(f"Error updating plot: {e}")

    def updatePlotUI(self, plot_data):
        with self.lock:
            for freq, dbLatest, color in plot_data:
                if freq in self.bars:
                    self.bars[freq].setData([freq, freq], [dbLatest, -90])
                    self.bars[freq].setPen(pg.mkPen(color, width=3))
                else:
                    self.bars[freq] = self.plot.plot([freq, freq], [dbLatest, -90], pen=pg.mkPen(color, width=3))

    def setLogTicks(self):
        customTicks = [
            (20, "20"), (40, "40"), (60, "60"), (80, "80"), (100, "100"),
            (200, "200"), (300, "300"), (400, "400"), (600, "600"), (800, "800"),
            (1000, "1k"), (2000, "2k"), (3000, "3k"), (4000, "4k"), (5000, "5k"),
            (6000, "6k"), (7000, "7k"), (8000, "8k"), (9000, "9k"), (10000, "10k"),
            (20000, "20k")
        ]
        self.plot.getAxis('bottom').setTicks([customTicks])

    def shutdown(self):
        if self.plottingActive:
            print("Stopping the plotting timer and shutting down the executor...")
            self.plottingActive = False
            self.timer.stop()
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

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
                filteredDBValues = [db for db in dbValues if db > -60]
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
        channelFormatted = f"{channel + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelFormatted}/eq/{eqBand}', [2, freqID, gainID, qIDValue])
        print(f"Sent OSC Parameters for channel {channelFormatted}, eqBand {eqBand}: freqID {freqID}, gainID {gainID}, qIDValue {qIDValue}")


    def updateAllBands(self, vocalType, channel):
        logging.debug(f"Updating all bands for vocalType: {vocalType}, channel: {channel}")
        bands = ['Low', 'Low Mid', 'High Mid', 'High']
        for index, band in enumerate(bands):
            multiplier = gainMultis.get(vocalType, {}).get(band, 0)
            logging.debug(f"Processing band: {band}, multiplier: {multiplier}")
            if multiplier > 0:
                targetDB = self.findLowestDBinBand(band)
                targetFreq = self.findLowestFreqinBand(band)
            else:
                targetDB = self.findHighestDBinBand(band)
                targetFreq = self.findHighestFreqinBand(band)
            if targetDB is None or targetFreq is None:
                logging.debug(f"No dB data or frequency data for band {band}. Skipping...")
                continue
            freqID, actualFreq = self.findClosestFrequency(band, targetFreq)
            if freqID is None:
                logging.debug(f"No closest frequency found for band {band}. Skipping...")
                continue
            if multiplier > 0:
                gainValue = self.calculateGainForLowestDB(targetDB, band, vocalType)
            else:
                gainValue = self.calculateGain(targetDB, band, vocalType)
            gainID = eqGainValues[self.getClosestGainValue(gainValue, eqGainValues)]
            qValue = self.calculateQValue(targetFreq, band)
            qIDValue = self.getClosestQIDValue(qValue)
            self.sendOSCParameters(channel, index + 1, freqID, gainID, qIDValue)
            logging.debug(f"Sent OSC Parameters for band {band}, channel {channel}: freqID {freqID}, gainID {gainID}, qIDValue {qIDValue}")


class MixerDiscovery:
    def __init__(self, port=10023):
        self.port = port
        self.subnets = ["192.168.10", "192.168.1", "192.168.56"]

    def checkMixerIP(self, ip):
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
        from osc_handlers import OscHandlers
        discIPs = {}
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(self.checkMixerIP, f"{subnet}.{i}"): f"{subnet}.{i}" for subnet in self.subnets for i in range(256)}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    ip, rawData = result
                    details = OscHandlers().handlerXInfo(rawData)
                    discIPs[ip] = details
        return discIPs
