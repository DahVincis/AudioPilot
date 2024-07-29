from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QHBoxLayout, QSlider, QDial, QButtonGroup,
    QGraphicsBlurEffect, QGraphicsDropShadowEffect, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap
import pyqtgraph as pg
import threading
import time
from pythonosc.udp_client import SimpleUDPClient

from utils import MixerDiscovery, PlotManager, BandManager
from Data import faderData, eqGainValues, lowcutFreq, eqFreq, qValues, trimValues
import logging

logging.basicConfig(level=logging.DEBUG)

def rPath(relativePath):
    import sys
    import os
    """ Get the absolute path to a resource, works for dev and PyInstaller """
    basePath = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basePath, relativePath)

def widgetShadow(widget, shadowRadius=15, xOffset=3, yOffset=3, color=QColor(0, 0, 0, 160)):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(shadowRadius)
    shadow.setXOffset(xOffset)
    shadow.setYOffset(yOffset)
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)

class MixerDiscoveryWorker(QThread):
    mixersFound = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.mixerScanner = MixerDiscovery()

    def run(self):
        availableMixers = self.mixerScanner.discoverMixers()
        self.mixersFound.emit(availableMixers)

class MixerDiscoveryUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mixer Discovery")
        self.setWindowIcon(QIcon(rPath("AudioPilot_Logo2.png")))
        self.setGeometry(100, 100, 400, 200)
        self.initUI()
        self.mixerWorker = MixerDiscoveryWorker()
        self.mixerWorker.mixersFound.connect(self.updateMixerGrid)
        self.mixerWorker.start()

    def initUI(self):
        self.loadStylesheet(rPath("styles.qss"))
        self.layout = QVBoxLayout()
        self.infoLabel = QLabel("Searching for mixers...")
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.infoLabel)
        self.mixerGridLayout = QGridLayout()
        self.layout.addLayout(self.mixerGridLayout)

        # Search Again button
        self.searchAgainButton = QPushButton("Search Again")
        self.searchAgainButton.clicked.connect(self.searchAgain)
        widgetShadow(self.searchAgainButton)  # Apply shadow effect
        self.layout.addWidget(self.searchAgainButton, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(self.layout)

    def loadStylesheet(self, stylesheet):
        with open(stylesheet, "r") as f:
            self.setStyleSheet(f.read())

    def searchAgain(self):
        self.infoLabel.setText("Searching for mixers...")
        self.mixerWorker.start()

    @pyqtSlot(dict)
    def updateMixerGrid(self, availableMixers):
        for i in reversed(range(self.mixerGridLayout.count())): 
            widget = self.mixerGridLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if not availableMixers:
            self.infoLabel.setText("No mixers found.")
        else:
            self.infoLabel.setText("Select a mixer from the list below:")

        row = 0
        for ip, details in availableMixers.items():
            mixerLabel = QLabel(f"Mixer at {ip} - {details}")
            mixerLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mixerButton = QPushButton("Select")
            mixerButton.clicked.connect(lambda _, ip=ip, name=details.split('|')[1].strip(): self.chooseMixer(ip, name))
            widgetShadow(mixerButton)  # Apply shadow effect
            self.mixerGridLayout.addWidget(mixerLabel, row, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            self.mixerGridLayout.addWidget(mixerButton, row, 1)
            row += 1

    def chooseMixer(self, ip, name):
        self.selectedMixerIp = ip
        self.selectedMixerName = name
        self.accept()

class CustomFader(QSlider):
    valueChangedSignal = pyqtSignal(float)

    def __init__(self, client, channelNumber, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.channelNumber = channelNumber
        self.scaleFactor = 100  # Scale factor to convert float to int
        self.precisionLevel = 1.5  # Default precision factor
        self.adjustedKeys = [key.replace('‐', '-') for key in faderData.keys()]
        self.minVal = min(map(lambda x: int(float(x) * self.scaleFactor), self.adjustedKeys))
        self.maxVal = max(map(lambda x: int(float(x) * self.scaleFactor), self.adjustedKeys))
        self.setRange(self.minVal, self.maxVal)
        self.setValue(0)
        self.valueChanged.connect(self.sendOscMessage)
        self.tickInterval = (self.maximum() - self.minimum()) / 10

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tickColor = QColor(211, 211, 211)  # light gray color for ticks
        painter.setPen(tickColor)

        rect = self.rect()
        interval = (rect.height() - 20) / (self.maximum() - self.minimum())

        # Define the positions and values for the labels we want to show
        positionTicks = [10, 5, 0, -10, -20, -40, -60, -70, -90]
        scaledTicks = [int(tick * self.scaleFactor) for tick in positionTicks]
        for tick in scaledTicks:
            y = rect.height() - ((tick - self.minimum()) * interval) - 9
            painter.drawLine(30, int(y), rect.width(), int(y))  # Adjusted the line position
            painter.drawText(-1, int(y) + 5, str(tick / self.scaleFactor))  # Adjusted the label position

        painter.end()

    def sizeHint(self):
        return QSize(120, 220)  # Increase width to ensure labels fit

    def setFineMode(self, isFine):
        self.precisionLevel = 0.7 if isFine else 1.5

    def sendOscMessage(self):
        scaledDbValue = self.value() / self.scaleFactor
        updatedKeys = {key.replace('‐', '-'): value for key, value in faderData.items()}
        oscFloatID = updatedKeys.get(str(scaledDbValue), None)
        if oscFloatID is not None and self.channelNumber is not None:
            channelNumberFormatted = f"{self.channelNumber+1:02}"  # Format channel_num as two-digit
            self.client.send_message(f'/ch/{channelNumberFormatted}/mix/fader', [oscFloatID])
            self.valueChangedSignal.emit(oscFloatID)
            logging.debug(f'Sent OSC message: /ch/{channelNumberFormatted}/mix/fader {oscFloatID}')

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        updatedValue = self.value() + int(steps * self.precisionLevel * self.scaleFactor)
        updatedValue = max(self.minimum(), min(self.maximum(), updatedValue))
        if updatedValue != self.value():
            self.setValue(updatedValue)
            self.sendOscMessage()  # Send OSC message when scrolling

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            scaledValue = self.minimum() + ((self.maximum() - self.minimum()) * (self.height() - event.position().y()) / self.height())
            scaledValue = int(scaledValue / self.precisionLevel) * self.precisionLevel
            if scaledValue != self.value():
                self.setValue(int(scaledValue))
                self.sendOscMessage()  # Send OSC message when dragging

class AudioPilotUI(QWidget):
    def __init__(self, mixerName, client):
        super().__init__()
        self.mixerName = mixerName
        self.client = client
        self.plotMgr = None
        self.channelNum = None
        self.bandManagerThread = None
        self.bandThreadRunning = threading.Event()
        self.isMuted = True  # Initial state is muted
        self.selectedBand = 1  # Default to the first band
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Audio Pilot')
        self.setWindowIcon(QIcon(rPath("AudioPilot_Logo2.png")))
        self.setGeometry(100, 100, 1280, 720)  # Adjust the initial window size
        self.loadStylesheet(rPath("styles.qss"))

        self.mainLayout = QVBoxLayout()

        headerLayout = QHBoxLayout()
        self.mixerLabel = QLabel(f"Connected to Mixer: {self.mixerName}")
        self.mixerLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        headerLayout.addWidget(self.mixerLabel)
        
        # Disconnect button
        self.disconnectButton = QPushButton("Disconnect")
        self.disconnectButton.setObjectName("disconnectButton")  # Set the object name
        self.disconnectButton.setFixedSize(90, 30)  # Smaller size for disconnect button
        self.disconnectButton.clicked.connect(self.disconnect)
        widgetShadow(self.disconnectButton)  # Apply shadow effect
        headerLayout.addWidget(self.disconnectButton, alignment=Qt.AlignmentFlag.AlignTop)
        headerLayout.addStretch(1)

        self.mainLayout.addLayout(headerLayout)

        topLayout = QHBoxLayout()

        leftPanelLayout = QVBoxLayout()

        # Mute Button
        self.toggleMuteButton = QPushButton("Mute")
        self.toggleMuteButton.setObjectName("muteButton")
        self.toggleMuteButton.setCheckable(True)
        self.toggleMuteButton.setChecked(True)  # Set to checked initially
        self.toggleMuteButton.clicked.connect(self.toggleMute)
        widgetShadow(self.toggleMuteButton)  # Apply shadow effect
        leftPanelLayout.addWidget(self.toggleMuteButton)

        # Fine Mode Button
        self.fineButton = QPushButton("Fine")
        self.fineButton.setCheckable(True)
        self.fineButton.setChecked(False)
        self.fineButton.clicked.connect(self.toggleFineMode)
        widgetShadow(self.fineButton)  # Apply shadow effect
        leftPanelLayout.addWidget(self.fineButton)

        # Fader
        self.fader = CustomFader(self.client, self.channelNum, Qt.Orientation.Vertical)
        leftPanelLayout.addWidget(self.fader)

        # Channel Selector
        self.selectChannelButton = QPushButton("Channel")
        self.selectChannelButton.clicked.connect(self.showChannelSelector)
        widgetShadow(self.selectChannelButton)  # Apply shadow effect
        leftPanelLayout.addWidget(self.selectChannelButton)

        topLayout.addLayout(leftPanelLayout)

        # RTA Plot
        self.graphWidget = pg.GraphicsLayoutWidget(show=True)
        self.plot = self.graphWidget.addPlot(title="")
        self.plot.setLogMode(x=True, y=False)
        self.plot.setYRange(-90, 0)
        self.plot.setLabel('bottom', 'Frequency', units='Hz')
        self.plot.setLabel('left', 'dB')
        self.plot.showGrid(x=True, y=True)
        topLayout.addWidget(self.graphWidget)

        eqControls = QVBoxLayout()

        # RTA Control
        self.rtaToggle = QPushButton("RTA")
        self.rtaToggle.setCheckable(True)
        self.rtaToggle.setChecked(False)
        self.rtaToggle.clicked.connect(self.togglePlotUpdates)
        widgetShadow(self.rtaToggle)  # Apply shadow effect
        eqControls.addWidget(self.rtaToggle)

        # AudioPilot Control
        pitchLayout = QVBoxLayout()
        pitchLayout.addStretch(1)
        self.pitchToggle = QPushButton("AudioPilot")
        self.pitchToggle.setCheckable(True)
        self.pitchToggle.setChecked(False)
        self.pitchToggle.clicked.connect(self.togglePitchCorrection)
        widgetShadow(self.pitchToggle)  # Apply shadow effect
        pitchLayout.addWidget(self.pitchToggle, alignment=Qt.AlignmentFlag.AlignCenter)
        
        pitchLayout.setSpacing(2)

        # Pitch Type Selector
        self.pitchButtonGroup = QButtonGroup(self)
        pitchTypes = ["Low Pitch", "Mid Pitch", "High Pitch"]
        for pitch in pitchTypes:
            btn = QPushButton(pitch)
            btn.setCheckable(True)
            btn.setFixedSize(105, 40)
            btn.setStyleSheet("font-size: 12px;")
            self.pitchButtonGroup.addButton(btn)
            pitchLayout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            widgetShadow(btn)  # Apply shadow effect

        # Set the default pitch button to be checked and update its style
        defaultPitchButton = self.pitchButtonGroup.buttons()[0]  # Set the first pitch as default
        if defaultPitchButton:
            defaultPitchButton.setChecked(True)
        eqControls.addLayout(pitchLayout)

        pitchLayout.addStretch(1)  # Add stretch after the pitch type selector

        # Trim Control
        trimLayout = QVBoxLayout()
        trimLabel = QLabel("Trim")
        trimLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trimLayout.addWidget(trimLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        self.trimDial = QDial()
        self.trimDial.setRange(int(min(trimValues.keys())), int(max(trimValues.keys())))
        self.trimDial.setValue(0)
        self.trimDial.valueChanged.connect(self.changeTrim)
        widgetShadow(self.trimDial)  # Apply shadow effect
        trimLayout.addWidget(self.trimDial, alignment=Qt.AlignmentFlag.AlignCenter)

        trimLayout.addStretch(1)  # Add stretch after the trim dial
        eqControls.addLayout(trimLayout)

        topLayout.addLayout(eqControls)
        self.mainLayout.addLayout(topLayout)

        eqControlsLayout = QVBoxLayout()

        bandSelectionLayout = QHBoxLayout()
        bandSelectionLayout.setSpacing(2)

        bandSelectionLayout.addStretch(6)  # Add stretch to the left side

        # Band buttons
        self.bandButtons = QButtonGroup(self)
        bands = ["Low", "LoMid", "HiMid", "High"]
        for index, band in enumerate(bands):
            btn = QPushButton(band)
            btn.setCheckable(True)
            btn.setFixedSize(120, 40)
            self.bandButtons.addButton(btn, index + 1)
            bandSelectionLayout.addWidget(btn)
        self.bandButtons.buttonClicked.connect(self.changeBand)
        widgetShadow(self.bandButtons.button(1))  # Apply shadow effect to the first band button
        widgetShadow(self.bandButtons.button(2))  # Apply shadow effect to the second band button
        widgetShadow(self.bandButtons.button(3))  # Apply shadow effect to the third band button
        widgetShadow(self.bandButtons.button(4))  # Apply shadow effect to the fourth band button

        bandSelectionLayout.addStretch(1)  # Add stretch after the band buttons

        # Add EQ Mode Control and EQ Toggle next to Band Buttons
        self.eqTypeDropdown = QComboBox()
        self.eqTypeDropdown.addItems(["LCut", "LShv", "PEQ", "VEQ", "HShv", "HCut"])
        self.eqTypeDropdown.currentIndexChanged.connect(self.changeEQMode)  # Connect the signal to the handler
        widgetShadow(self.eqTypeDropdown)  # Apply shadow effect
        bandSelectionLayout.addWidget(self.eqTypeDropdown)

        # EQ Button
        self.eqToggleButton = QPushButton("EQ")
        self.eqToggleButton.setCheckable(True)
        self.eqToggleButton.setChecked(False)
        self.eqToggleButton.clicked.connect(self.toggleEQ)
        widgetShadow(self.eqToggleButton)  # Apply shadow effect
        bandSelectionLayout.addWidget(self.eqToggleButton)

        bandSelectionLayout.addStretch(2)  # Add stretch to the right side
        eqControlsLayout.addLayout(bandSelectionLayout)

        dialsLayout = QHBoxLayout()
        dialsLayout.setSpacing(5)

        # Low Cut Control 
        lowcutLayout = QVBoxLayout()

        self.lowCutToggleButton = QPushButton("Low Cut")
        self.lowCutToggleButton.setCheckable(True)
        self.lowCutToggleButton.setChecked(False)
        self.lowCutToggleButton.clicked.connect(self.toggleLowCut)
        widgetShadow(self.lowCutToggleButton)  # Apply shadow effect
        lowcutLayout.addWidget(self.lowCutToggleButton, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Low Cut Dial
        self.lowcutDial = QDial()
        self.lowcutDial.setRange(int(min(lowcutFreq.keys())), int(max(lowcutFreq.keys())))
        self.lowcutDial.setValue(100)
        self.lowcutDial.setFixedSize(80, 80)  # Decrease size of the lowcut dial
        self.lowcutDial.valueChanged.connect(self.changeLowCut)
        widgetShadow(self.lowcutDial)  # Apply shadow effect
        lowcutLayout.addWidget(self.lowcutDial, alignment=Qt.AlignmentFlag.AlignCenter)
        dialsLayout.addStretch(1) # Add stretch to the right of the lowcut dial

        dialsLayout.addLayout(lowcutLayout)

        dialsLayout.addStretch(1) # Add stretch to the left side

        # Frequency Control
        freqLayout = QVBoxLayout()
        freqLabel = QLabel("Frequency")
        freqLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.freqDial = QDial()
        self.freqDial.setRange(int(min(map(float, eqFreq.keys()))), int(max(map(float, eqFreq.keys()))))
        self.freqDial.setValue(1000)
        self.freqDial.setFixedSize(80, 80)
        self.freqDial.valueChanged.connect(self.changeFreq)
        widgetShadow(self.freqDial)  # Apply shadow effect
        freqLayout.addWidget(freqLabel)
        freqLayout.addWidget(self.freqDial)
        dialsLayout.addLayout(freqLayout)

        # Quality Control
        qLayout = QVBoxLayout()
        qLabel = QLabel("Quality")
        qLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qDial = QDial()
        self.qDial.setRange(int(min(qValues.keys())), int(max(qValues.keys())))
        self.qDial.setValue(5)
        self.qDial.setFixedSize(80, 80)
        self.qDial.valueChanged.connect(self.changeQ)
        widgetShadow(self.qDial)  # Apply shadow effect
        qLayout.addWidget(qLabel)
        qLayout.addWidget(self.qDial)
        dialsLayout.addLayout(qLayout)

        # Gain Control
        smallGainLayout = QVBoxLayout()
        smallGainLabel = QLabel("Gain")
        smallGainLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.smallGainDial = QDial()
        self.smallGainDial.setRange(int(min(eqGainValues.keys())), int(max(eqGainValues.keys())))
        self.smallGainDial.setValue(0)
        self.smallGainDial.setFixedSize(80, 80)
        self.smallGainDial.valueChanged.connect(self.changeEqGain)
        widgetShadow(self.smallGainDial)  # Apply shadow effect
        smallGainLayout.addWidget(smallGainLabel)
        smallGainLayout.addWidget(self.smallGainDial)
        dialsLayout.addLayout(smallGainLayout)

        dialsLayout.addStretch(2) # Add stretch to the right side

        eqControlsLayout.addLayout(dialsLayout)
        self.mainLayout.addLayout(eqControlsLayout)

        self.setLayout(self.mainLayout)

        # Set the default band button to be checked and update its style
        defaultBandButton = self.bandButtons.button(self.selectedBand)
        if defaultBandButton:
            defaultBandButton.setChecked(True)
            self.changeBand(defaultBandButton)  # Ensure the changeBand function is called

        self.setLayout(self.mainLayout)
        self.setWindowTitle('Audio Pilot')

    def loadStylesheet(self, stylesheet):
        with open(stylesheet, "r") as f:
            self.setStyleSheet(f.read())
    
    def changeBand(self, button):
        self.selectedBand = self.bandButtons.id(button)

    def changeEQMode(self, index):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        
        eqModeId = index  # Since the index corresponds to the enum value 0..5
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/eq/{self.selectedBand}/type', [eqModeId])
        print(f'Sent OSC message: /ch/{channelNumFormatted}/eq/{self.selectedBand}/type {eqModeId}')

    def toggleFineMode(self):
        isFine = self.fineButton.isChecked()
        self.fader.setFineMode(isFine)

    def togglePlotUpdates(self):
        if self.rtaToggle.isChecked() and self.plotMgr is not None:
            if not self.plotMgr.plottingActive:
                self.plotMgr.start()
        else:
            if self.plotMgr is not None and self.plotMgr.plottingActive:
                self.plotMgr.shutdown()
                self.clearPlot()

    def clearPlot(self):
        if self.plotMgr:
            for bar in self.plotMgr.bars.values():
                bar.clear()

    def redrawPlot(self):
        if self.plotMgr:
            self.plotMgr.updatePlot()

    def showChannelSelector(self):
        self.channelSelectorDialog = ChannelSelectorDialog(self)
        if self.channelSelectorDialog.exec() == QDialog.DialogCode.Accepted:
            self.selectChannelButton.setText(self.channelSelectorDialog.selectedChannel)
            self.channelNum = int(self.channelSelectorDialog.selectedChannel.split()[1]) - 1
            self.client.send_message('/-action/setrtasrc', [self.channelNum])
            self.fader.channelNumber = self.channelNum  # Set channel number for fader
            self.startPlotting()

    def startPlotting(self):
        if self.channelNum is not None:
            if not self.plotMgr:
                print("Starting Plot Manager...")
                self.plotMgr = PlotManager(self.plot)
                self.plotMgr.setLogTicks()
            if self.rtaToggle.isChecked():
                self.plotMgr.start()

    def stopPlotting(self):
        if self.plotMgr:
            print("Stopping Plot Manager...")
            self.plotMgr.shutdown()
            self.plotMgr = None

    def toggleMute(self):
        if self.channelNum is not None:  # Ensure channelNum is set
            channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
            if self.toggleMuteButton.isChecked():
                self.client.send_message(f'/ch/{channelNumFormatted}/mix/on', 0)
                print(f"Channel {channelNumFormatted} is muted.")
            else:
                self.client.send_message(f'/ch/{channelNumFormatted}/mix/on', 1)
                print(f"Channel {channelNumFormatted} is unmuted.")

    def togglePitchCorrection(self):
        if self.pitchToggle.isChecked():
            checkedButton = self.pitchButtonGroup.checkedButton()
            if checkedButton:
                vocalType = checkedButton.text()
                self.startBandManager(vocalType)
        else:
            self.stopBandManager()

    def startBandManager(self, vocalType):
        if self.channelNum is not None:
            self.bandThreadRunning.set()
            self.bandMgr = BandManager(self.client)
            self.bandManagerThread = threading.Thread(target=self.runBandManager, args=(vocalType, self.channelNum), daemon=True)
            self.bandManagerThread.start()

    def stopBandManager(self):
        if self.bandManagerThread is not None:
            self.bandThreadRunning.clear()

    def runBandManager(self, vocalType, channel):
        while self.bandThreadRunning.is_set():
            self.bandMgr.updateAllBands(vocalType, channel)
            time.sleep(0.3)

    def changeEqGain(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closestGainValue = min(eqGainValues.keys(), key=lambda k: abs(k - value))
        oscGainID = eqGainValues[closestGainValue]
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/eq/{self.selectedBand}/g', [oscGainID])

    def changeLowCut(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closeestFreqValue = min(lowcutFreq.keys(), key=lambda k: abs(k - value))
        oscFreqID = lowcutFreq[closeestFreqValue]
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/preamp/hpf', [oscFreqID])

    def changeFreq(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        def freqToFloat(freq):
            return float(freq)

        floatFrequencies = [freqToFloat(k) for k in eqFreq.keys()]
        closestFreq = min(floatFrequencies, key=lambda k: abs(k - value))
        # Find the closest key in its original string format
        closestFreqKey = min(eqFreq.keys(), key=lambda k: abs(float(k) - closestFreq))
        oscFrequencyID = eqFreq[closestFreqKey]
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/eq/{self.selectedBand}/f', [oscFrequencyID])

    def changeQ(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closestValue = min(qValues.keys(), key=lambda k: abs(k - value))
        oscQID = qValues[closestValue]
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/eq/{self.selectedBand}/q', [oscQID])

    def changeTrim(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closestValue = min(trimValues.keys(), key=lambda k: abs(k - value))
        oscTrimID = trimValues[closestValue]
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/preamp/trim', [oscTrimID])

    def toggleEQ(self):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        state = 1 if self.eqToggleButton.isChecked() else 0
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/eq/on/', [state])

    def toggleLowCut(self):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        state = 1 if self.lowCutToggleButton.isChecked() else 0
        channelNumFormatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channelNumFormatted}/preamp/hpon', [state])

    def applyBlurEffect(self):
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(20)
        self.setGraphicsEffect(blur)

    def removeBlurEffect(self):
        self.setGraphicsEffect(None)

    def updateUI(self):
        self.mixerLabel.setText(f"Connected to Mixer: {self.mixerName}")
        self.removeBlurEffect()

    def disconnect(self):
        from PyQt6.QtWidgets import QApplication
        from main import alignWidgetCenter
        self.stopPlotting()
        self.applyBlurEffect()  # Apply blur effect before showing MixerDiscoveryUI
        self.mixerDiscovery = MixerDiscoveryUI(self)  # Pass self as parent to keep it modal
        alignWidgetCenter(self.mixerDiscovery, self)
        self.mixerDiscovery.exec()
        if self.mixerDiscovery.result() == QDialog.DialogCode.Accepted:
            self.mixerName = self.mixerDiscovery.selectedMixerName
            self.client = SimpleUDPClient(self.mixerDiscovery.selectedMixerIp, 10023)
            self.updateUI()
        else:
            QApplication.quit()

class ChannelSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Channel")
        self.initUI()

    def initUI(self):
        self.loadStylesheet(rPath("styles.qss"))
        layout = QGridLayout()
        self.channelButtonGroup = QButtonGroup(self)

        for i in range(1, 33):
            btn = QPushButton(f"CH {i:02}")
            btn.setCheckable(True)
            btn.clicked.connect(self.chooseChannel)
            self.channelButtonGroup.addButton(btn, i)
            layout.addWidget(btn, (i-1)//8, (i-1)%8)

        self.setLayout(layout)

    def loadStylesheet(self, stylesheet):
        with open(stylesheet, "r") as f:
            self.setStyleSheet(f.read())

    def chooseChannel(self):
        selectedButton = self.channelButtonGroup.checkedButton()
        if selectedButton:
            self.selectedChannel = selectedButton.text()
            self.accept()
