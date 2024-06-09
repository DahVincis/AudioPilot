import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGridLayout, QDialog, QGraphicsRectItem, QMainWindow,
    QSlider, QComboBox, QDial, QButtonGroup, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSlot
import pyqtgraph as pg
import numpy as np
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import threading
import select
import time
import struct
from Data import frequencies, bandsRangeRTA, bandRanges, qValues, eqGainValues, dataRTA, gainOffset, qLimits, gainMultis
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

# Global variables
queueRTA = Queue()
receivedFirstRTA = False
bars = {}

class MixerDiscoveryUI(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mixer Discovery")
        self.setGeometry(100, 100, 400, 200)
        self.initUI()
        self.mixerScanner = MixerDiscovery()
        self.timer = QTimer()
        self.timer.timeout.connect(self.scanAndUpdateMixerGrid)
        self.timer.start(1000)  # Update every second
        self.availableMixers = {}
        self.discoveryPhrases = ["Searching for mixers.", "Searching for mixers..", "Searching for mixers..."]
        self.animationIndex = 0
        self.searchingTimer = QTimer()
        self.searchingTimer.timeout.connect(self.updateSearchingAnimation)
        self.searchingTimer.start(500)  # Update every half second

    def initUI(self):
        self.layout = QVBoxLayout()
        self.infoLabel = QLabel("Searching for mixers...")
        self.layout.addWidget(self.infoLabel)
        self.mixerGridLayout = QGridLayout()
        self.layout.addLayout(self.mixerGridLayout)
        self.setLayout(self.layout)

    @pyqtSlot()
    def scanAndUpdateMixerGrid(self):
        self.availableMixers = self.mixerScanner.discoverMixers()
        self.updateMixerGrid()

    def updateMixerGrid(self):
        for i in reversed(range(self.mixerGridLayout.count())): 
            widget = self.mixerGridLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if not self.availableMixers:
            self.infoLabel.setText(self.discoveryPhrases[self.animationIndex])
        else:
            self.infoLabel.setText("Select a mixer from the list below:")

        row = 0
        for ip, details in self.availableMixers.items():
            mixerLabel = QLabel(f"Mixer at {ip} - {details}")
            mixerButton = QPushButton("Select")
            mixerButton.clicked.connect(lambda _, ip=ip: self.chooseMixer(ip))
            self.mixerGridLayout.addWidget(mixerLabel, row, 0)
            self.mixerGridLayout.addWidget(mixerButton, row, 1)
            row += 1

    def updateSearchingAnimation(self):
        self.animationIndex = (self.animationIndex + 1) % len(self.discoveryPhrases)
        self.infoLabel.setText(self.discoveryPhrases[self.animationIndex])

    def chooseMixer(self, ip):
        self.selectedMixerIp = ip
        self.accept()

class MixerDiscovery:
    def __init__(self, port=10023):
        self.port = port
        self.subnets = ["192.168.10", "192.168.1"]

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
        discIPs = {}
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(self.checkMixerIP, f"{subnet}.{i}"): f"{subnet}.{i}" for subnet in self.subnets for i in range(256)}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    ip, rawData = result
                    details = FaderHandler().handlerXInfo(rawData)
                    discIPs[ip] = details
        return discIPs

class MixerManager:
    def __init__(self, client):
        self.client = client

    def keepMixerAwake(self):
        while True:
            self.client.send_message('/xremote', None)
            self.client.send_message('/xinfo', None)
            time.sleep(3)

class RTASubscriber:
    def __init__(self, client):
        self.client = client

    def subRenewRTA(self):
        while True:
            self.client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 99])
            time.sleep(0.1)

    def handlerRTA(self, address, *args):
        global receivedFirstRTA
        if not args:
            print(f"No RTA data received on {address}")
            return

        blobRTA = args[0]
        dataPoints = len(blobRTA) // 4

        try:
            ints = struct.unpack(f'<{dataPoints}I', blobRTA)
            dbValues = []
            for intValue in ints:
                shortINT1 = intValue & 0xFFFF
                shortINT2 = (intValue >> 16) & 0xFFFF
                if shortINT1 >= 0x8000: shortINT1 -= 0x10000
                if shortINT2 >= 0x8000: shortINT2 -= 0x10000
                dbValue1 = (shortINT1 / 256.0) + gainOffset
                dbValue2 = (shortINT2 / 256.0) + gainOffset
                dbValues.append(dbValue1)
                dbValues.append(dbValue2)

            for i, dbValue in enumerate(dbValues[2:len(frequencies) + 2]):
                freqLabel = frequencies[i] if i < len(frequencies) else "Unknown"
                if freqLabel in dataRTA:
                    dataRTA[freqLabel].append(dbValue)
                    if len(dataRTA[freqLabel]) > 10:
                        dataRTA[freqLabel].pop(0)
                else:
                    dataRTA[freqLabel] = [dbValue]

            if not receivedFirstRTA:
                receivedFirstRTA = True

            queueRTA.put(dataRTA)
        except Exception as e:
            print(f"Error processing RTA data: {e}")

class FaderHandler:
    def handlerFader(self, address, *args):
        if args and isinstance(args[0], float):
            f = args[0]
            if f > 0.75:
                d = f * 40.0 - 30.0
            elif f > 0.5:
                d = f * 80.0 - 50.0
            elif f > 0.25:
                d = f * 160.0 - 70.0
            elif f >= 0.0:
                d = f * 480.0 - 90.0
            else:
                print(f"Invalid fader value: {f}")
                return
            print(f"[{address}] ~ Fader value: {d:.2f} dB")
        else:
            print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

    def floatToDB(self, trimFloat):
        floatMin = 0.0
        floatMax = 0.25
        dbMin = -18.0
        dbMax = 18.0
        if 0 <= trimFloat <= 0.25:
            dbValue = (trimFloat - floatMin) * (dbMax - dbMin) / (floatMax - floatMin) + dbMin
        else:
            dbValue = "Out of range"
        return dbValue

    def handlerPreampTrim(self, address, *args):
        if args and isinstance(args[0], float):
            trimFloat = args[0]
            dbValue = self.floatToDB(trimFloat)
            if isinstance(dbValue, str):
                print(f"[{address}] ~ Preamp trim value: {dbValue}")
            else:
                print(f"[{address}] ~ Preamp trim value: {dbValue:.2f} dB")
        else:
            print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

    def handlerXInfo(self, data):
        try:
            addressEnd = data.find(b'\x00')
            data = data[(addressEnd + 4) & ~3:]
            startTypeTag = data.find(b',') + 1
            endTypeTag = data.find(b'\x00', startTypeTag)
            typeTag = data[startTypeTag:endTypeTag].decode()
            data = data[(endTypeTag + 4) & ~3:]
            arguments = []
            for tag in typeTag:
                if tag == 's':
                    endString = data.find(b'\x00')
                    argument = data[:endString].decode()
                    arguments.append(argument)
                    data = data[(endString + 4) & ~3:]
            return " | ".join(arguments)
        except Exception as e:
            print(f"Error parsing data: {e}")
            return "Error parsing data"

    def handlerDefault(self, address, *args):
        print(f"Received fader message on {address}. Args: {args}")

class PlotManager:
    def __init__(self, plot):
        self.plot = plot
        self.bars = {}

    def updatePlot(self):
        try:
            latestData = queueRTA.get_nowait()
            threshUpper = -10
            threshMid = -18
            threshLower = -45
            for freq in frequencies:
                dbValues = latestData.get(freq, [-90])
                dbLatest = dbValues[-1] if dbValues else -90
                color = 'r' if dbLatest >= threshUpper else 'y' if threshMid <= dbLatest < threshUpper else 'g' if dbLatest >= threshLower <= threshMid else 'b'
                if freq in self.bars:
                    self.bars[freq].setData([freq, freq], [dbLatest, -90])
                    self.bars[freq].setPen(pg.mkPen(color, width=3))
                else:
                    self.bars[freq] = self.plot.plot([freq, freq], [dbLatest, -90], pen=pg.mkPen(color, width=3))
        except Empty:
            pass

    def setLogTicks(self):
        ticks = np.logspace(np.log10(frequencies[0]), np.log10(frequencies[-1]), num=20)
        labelTicks = [(tick, f"{int(tick)} Hz") for tick in ticks]
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
class ApplicationManager:
    def __init__(self, client, server):
        self.client = client
        self.server = server

    def run(self, mixer_ip):
        mixer_manager = MixerManager(self.client)
        threadKeepAlive = threading.Thread(target=mixer_manager.keepMixerAwake, daemon=True)
        threadKeepAlive.start()

        rta_subscriber = RTASubscriber(self.client)
        threadRTASub = threading.Thread(target=rta_subscriber.subRenewRTA, daemon=True)
        threadRTASub.start()

        app = QApplication([])
        audio_mixer_ui = AudioPilotUI(mixer_ip, self.client)

        plot_manager = PlotManager(audio_mixer_ui.plot)
        audio_mixer_ui.plot_manager = plot_manager  # Assign the plot_manager to the UI

        threadServerOSC = threading.Thread(target=self.server.serve_forever, daemon=True)
        threadServerOSC.start()

        sys.exit(app.exec())

class ChannelSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Channel")
        self.initUI()

    def initUI(self):
        layout = QGridLayout()
        self.button_group = QButtonGroup(self)

        for i in range(1, 33):
            btn = QPushButton(f"CH {i:02}")
            btn.setCheckable(True)
            btn.clicked.connect(self.chooseChannel)
            self.button_group.addButton(btn, i)
            layout.addWidget(btn, (i-1)//8, (i-1)%8)

        self.setLayout(layout)

    def chooseChannel(self):
        selected_button = self.button_group.checkedButton()
        if selected_button:
            self.selectedChannel = selected_button.text()
            self.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.pitchTypeSelector = QComboBox()
        self.pitchTypeSelector.addItems(["Low Pitch", "Mid Pitch", "High Pitch"])
        layout.addRow("Pitch Type:", self.pitchTypeSelector)

        self.lowcutDial = QDial()
        self.lowcutDial.setRange(20, 400)  # Frequency range in Hz
        self.lowcutDial.setValue(100)
        layout.addRow("Lowcut Frequency:", self.lowcutDial)

        self.setLayout(layout)

class AudioPilotUI(QWidget):
    def __init__(self, mixerIP, client):
        super().__init__()
        self.mixerAddress = mixerIP
        self.client = client
        self.plot_manager = None  # Initialize plot_manager
        self.channel_num = None  # Initialize channel number
        self.band_manager_thread = None  # To handle the band manager thread
        self.band_manager_thread_running = threading.Event()  # To track the state of the band manager thread
        self.initUI()

    def initUI(self):
        # Main layout
        mainLayout = QVBoxLayout()

        # Header
        headerLayout = QHBoxLayout()
        self.mixerLabel = QLabel(f"Connected to Mixer: {self.mixerAddress}")
        headerLayout.addWidget(self.mixerLabel)
        mainLayout.addLayout(headerLayout)

        # Top layout
        topLayout = QHBoxLayout()

        # Left panel: Fader and channel controls
        leftPanelLayout = QVBoxLayout()

        self.toggleMuteButton = QPushButton("Mute")
        self.toggleMuteButton.setCheckable(True)
        self.toggleMuteButton.clicked.connect(self.toggleMute)
        leftPanelLayout.addWidget(self.toggleMuteButton)

        self.fader = QSlider(Qt.Orientation.Vertical)
        self.fader.setRange(-90, 10)  # dB range
        self.fader.setValue(0)
        leftPanelLayout.addWidget(self.fader)

        self.selectChannelButton = QPushButton("Select Channel")
        self.selectChannelButton.clicked.connect(self.showChannelSelector)
        leftPanelLayout.addWidget(self.selectChannelButton)

        topLayout.addLayout(leftPanelLayout)

        # Middle panel: RTA plot
        self.graphWidget = pg.GraphicsLayoutWidget(show=True)
        self.plot = self.graphWidget.addPlot(title="RTA")
        self.plot.setLogMode(x=True, y=False)
        self.plot.setYRange(-90, 0)
        self.plot.setLabel('bottom', 'Frequency', units='Hz')
        self.plot.setLabel('left', 'dB')
        self.plot.showGrid(x=True, y=True)
        topLayout.addWidget(self.graphWidget)

        # Add a semi-transparent rectangle for dimming effect
        self.dimmingRectangle = QGraphicsRectItem(QRectF(self.plot.vb.viewRect()))
        self.dimmingRectangle.setBrush(pg.mkBrush((0, 0, 0, 100)))  # Semi-transparent black
        self.dimmingRectangle.setZValue(10)  # Ensure it is on top
        self.plot.addItem(self.dimmingRectangle)
        self.dimmingRectangle.hide()

        # Right panel: EQ controls and settings
        eqControls = QVBoxLayout()

        self.eqToggle = QPushButton("EQ On/Off")
        self.eqToggle.setCheckable(True)
        self.eqToggle.clicked.connect(self.toggleEQ)
        eqControls.addWidget(self.eqToggle)

        gainLayout = QVBoxLayout()
        gainLabel = QLabel("Gain Level")
        gainLayout.addWidget(gainLabel)
        self.gainDial = QDial()
        self.gainDial.setRange(-15, 15)  # Gain range in dB
        self.gainDial.setValue(0)
        gainLayout.addWidget(self.gainDial)
        eqControls.addLayout(gainLayout)

        lowcutLayout = QVBoxLayout()
        lowcutLabel = QLabel("Lowcut Frequency")
        lowcutLayout.addWidget(lowcutLabel)
        self.lowcutDial = QDial()
        self.lowcutDial.setRange(20, 400)  # Frequency range in Hz
        self.lowcutDial.setValue(100)
        lowcutLayout.addWidget(self.lowcutDial)
        eqControls.addLayout(lowcutLayout)

        # Pitch Type Selector and Toggle
        pitchLayout = QVBoxLayout()
        self.pitchTypeSelector = QComboBox()
        self.pitchTypeSelector.addItems(["Low Pitch", "Mid Pitch", "High Pitch"])
        pitchLayout.addWidget(self.pitchTypeSelector)
        
        self.pitchToggle = QPushButton("Pitch Correction On/Off")
        self.pitchToggle.setCheckable(True)
        self.pitchToggle.clicked.connect(self.togglePitchCorrection)
        pitchLayout.addWidget(self.pitchToggle)
        
        eqControls.addLayout(pitchLayout)

        topLayout.addLayout(eqControls)

        mainLayout.addLayout(topLayout)

        # Bottom layout for EQ dials
        eqControlsLayout = QHBoxLayout()
        
        freqLayout = QVBoxLayout()
        freqLabel = QLabel("Freq")
        self.freqDial = QDial()
        self.freqDial.setRange(20, 20000)  # Frequency range in Hz
        self.freqDial.setValue(1000)
        self.freqDial.setFixedSize(50, 50)
        freqLayout.addWidget(freqLabel)
        freqLayout.addWidget(self.freqDial)
        eqControlsLayout.addLayout(freqLayout)

        qLayout = QVBoxLayout()
        qLabel = QLabel("Q")
        self.qDial = QDial()
        self.qDial.setRange(1, 10)  # Q range
        self.qDial.setValue(5)
        self.qDial.setFixedSize(50, 50)
        qLayout.addWidget(qLabel)
        qLayout.addWidget(self.qDial)
        eqControlsLayout.addLayout(qLayout)

        smallGainLayout = QVBoxLayout()
        smallGainLabel = QLabel("Gain")
        self.smallGainDial = QDial()
        self.smallGainDial.setRange(-12, 12)  # Gain range in dB
        self.smallGainDial.setValue(0)
        self.smallGainDial.setFixedSize(50, 50)
        smallGainLayout.addWidget(smallGainLabel)
        smallGainLayout.addWidget(self.smallGainDial)
        eqControlsLayout.addLayout(smallGainLayout)

        mainLayout.addLayout(eqControlsLayout)

        self.setLayout(mainLayout)

        self.setWindowTitle('Audio Mixer')
        self.show()

    def redrawPlot(self):
        if self.plot_manager:
            self.plot_manager.updatePlot()

    def showChannelSelector(self):
        self.channelSelectorDialog = ChannelSelectorDialog(self)
        if self.channelSelectorDialog.exec() == QDialog.DialogCode.Accepted:
            self.selectChannelButton.setText(self.channelSelectorDialog.selectedChannel)
            self.channel_num = int(self.channelSelectorDialog.selectedChannel.split()[1]) - 1
            self.client.send_message('/-action/setrtasrc', [self.channel_num])
            # Now start receiving and updating data for the selected channel
            self.startPlotting()

    def startPlotting(self):
        if not self.plot_manager:
            self.plot_manager = PlotManager(self.plot)
        self.timer = QTimer()
        self.timer.timeout.connect(self.redrawPlot)
        self.timer.start(100)

    def toggleMute(self):
        if self.toggleMuteButton.isChecked():
            self.toggleMuteButton.setStyleSheet("background-color: red")
            print("Channel is muted.")
        else:
            self.toggleMuteButton.setStyleSheet("background-color: gray")
            print("Channel is unmuted.")

    def toggleEQ(self):
        if self.eqToggle.isChecked():
            self.dimmingRectangle.hide()
            print("EQ is on.")
        else:
            self.dimmingRectangle.show()
            print("EQ is off.")

    def togglePitchCorrection(self):
        if self.pitchToggle.isChecked():
            vocalType = self.pitchTypeSelector.currentText()
            self.startBandManager(vocalType)
        else:
            self.stopBandManager()

    def startBandManager(self, vocalType):
        if self.channel_num is not None:
            self.band_manager_thread_running.set()  # Set the event to start the thread
            self.band_manager = BandManager(self.client)
            self.band_manager_thread = threading.Thread(target=self.runBandManager, args=(vocalType, self.channel_num), daemon=True)
            self.band_manager_thread.start()

    def stopBandManager(self):
        if self.band_manager_thread is not None:
            self.band_manager_thread_running.clear()  # Clear the event to stop the thread

    def runBandManager(self, vocalType, channel):
        while self.band_manager_thread_running.is_set():
            self.band_manager.updateAllBands(vocalType, channel)
            time.sleep(0.3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mixerDiscoveryDialog = MixerDiscoveryUI()
    if mixerDiscoveryDialog.exec() == QDialog.DialogCode.Accepted:
        chosenIP = mixerDiscoveryDialog.selectedMixerIp
        client = SimpleUDPClient(chosenIP, 10023)

        parser = argparse.ArgumentParser()
        parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
        parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
        args = parser.parse_args()

        dispatcher = Dispatcher()
        subRTA = RTASubscriber(client)
        faderHandler = FaderHandler()
        dispatcher.map("/meters", subRTA.handlerRTA)
        #dispatcher.map("/*/*/mix/fader", faderHandler.handlerFader)
        #dispatcher.map("/*/*/preamp/trim", faderHandler.handlerPreampTrim)
        #dispatcher.set_default_handler(faderHandler.handlerDefault)

        server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
        print(f"Serving on {server.server_address}")
        client._sock = server.socket

        appManager = ApplicationManager(client, server)
        appManager.run(chosenIP)
    else:
        sys.exit()
