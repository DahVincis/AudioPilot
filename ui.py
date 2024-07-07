from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QHBoxLayout, QSlider, QComboBox, QDial, QButtonGroup, QGraphicsBlurEffect
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor, QIcon
import pyqtgraph as pg
import threading
import time
from pythonosc.udp_client import SimpleUDPClient

from utils import MixerDiscovery, PlotManager, BandManager
from Data import faderData, eqGainValues, lowcutFreq, eqFreq, qValues, trimValues
import logging

logging.basicConfig(level=logging.DEBUG)

# Styling constants
BACKGROUND_COLOR = "#191714"
HEADER_COLOR = "#D98324"
TEXT_COLOR = "#D3D3D3"
FONT_FAMILY = "Verdana, Helvetica, sans-serif"
BUTTON_COLOR = "#001e7b"
BUTTON_SELECTED_COLOR = "#cb4c00"
FONT_SIZE = 14
FONT_WEIGHT = 565

font_style = f"font-family: {FONT_FAMILY}; font-size: {FONT_SIZE}px; font-weight: {FONT_WEIGHT};"

LOGO_PATH = "AudioPilot_Logo2.png"

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
        self.setWindowIcon(QIcon(LOGO_PATH))
        self.setGeometry(100, 100, 400, 200)
        self.initUI()
        self.mixerWorker = MixerDiscoveryWorker()
        self.mixerWorker.mixersFound.connect(self.updateMixerGrid)
        self.mixerWorker.start()

    def initUI(self):
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.layout = QVBoxLayout()
        self.infoLabel = QLabel("Searching for mixers...")
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.infoLabel)
        self.mixerGridLayout = QGridLayout()
        self.layout.addLayout(self.mixerGridLayout)

        # Search Again button
        self.searchAgainButton = QPushButton("Search Again")
        self.searchAgainButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.searchAgainButton.clicked.connect(self.searchAgain)
        self.layout.addWidget(self.searchAgainButton, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(self.layout)

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
            mixerButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
            mixerButton.clicked.connect(lambda _, ip=ip, name=details.split('|')[1].strip(): self.chooseMixer(ip, name))
            self.mixerGridLayout.addWidget(mixerLabel, row, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            self.mixerGridLayout.addWidget(mixerButton, row, 1)
            row += 1

    def chooseMixer(self, ip, name):
        self.selectedMixerIp = ip
        self.selectedMixerName = name
        self.accept()

class CustomFader(QSlider):
    valueChangedSignal = pyqtSignal(float)

    def __init__(self, client, channel_num, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.channel_num = channel_num
        self.scale_factor = 100  # Scale factor to convert float to int
        self.precision_factor = 2  # Default precision factor
        self.corrected_keys = [key.replace('‐', '-') for key in faderData.keys()]
        self.min_value = min(map(lambda x: int(float(x) * self.scale_factor), self.corrected_keys))
        self.max_value = max(map(lambda x: int(float(x) * self.scale_factor), self.corrected_keys))
        self.setRange(self.min_value, self.max_value)
        self.setValue(0)
        self.valueChanged.connect(self.sendOscMessage)
        self.tick_interval = (self.maximum() - self.minimum()) / 10

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tickColor = QColor(211, 211, 211)  # light gray color for ticks
        painter.setPen(tickColor)

        rect = self.rect()
        interval = (rect.height() - 20) / (self.maximum() - self.minimum())

        # Define the positions and values for the labels we want to show
        tick_positions = [10, 5, 0, -10, -20, -30, -40, -50, -70, -90]
        scaled_ticks = [int(tick * self.scale_factor) for tick in tick_positions]
        for tick in scaled_ticks:
            y = rect.height() - ((tick - self.minimum()) * interval) - 10
            painter.drawLine(30, int(y), rect.width(), int(y))  # Adjusted the line position
            painter.drawText(-1, int(y) + 5, str(tick / self.scale_factor))  # Adjusted the label position

        painter.end()

    def sizeHint(self):
        return QSize(120, 220)  # Increase width to ensure labels fit

    def setFineMode(self, is_fine):
        self.precision_factor = 0.7 if is_fine else 2

    def sendOscMessage(self):
        db_value = self.value() / self.scale_factor
        corrected_keys = {key.replace('‐', '-'): value for key, value in faderData.items()}
        float_id = corrected_keys.get(str(db_value), None)
        if float_id is not None and self.channel_num is not None:
            channel_num_formatted = f"{self.channel_num+1:02}"  # Format channel_num as two-digit
            self.client.send_message(f'/ch/{channel_num_formatted}/mix/fader', [float_id])
            self.valueChangedSignal.emit(float_id)
            logging.debug(f'Sent OSC message: /ch/{channel_num_formatted}/mix/fader {float_id}')

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        new_value = self.value() + int(steps * self.precision_factor * self.scale_factor)
        new_value = max(self.minimum(), min(self.maximum(), new_value))
        if new_value != self.value():
            self.setValue(new_value)
            self.sendOscMessage()  # Send OSC message when scrolling

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_value = self.minimum() + ((self.maximum() - self.minimum()) * (self.height() - event.position().y()) / self.height())
            new_value = int(new_value / self.precision_factor) * self.precision_factor
            if new_value != self.value():
                self.setValue(int(new_value))
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
        self.setWindowIcon(QIcon(LOGO_PATH))
        self.setGeometry(100, 100, 1366, 768)  # Adjust the initial window size
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; {font_style}")

        self.mainLayout = QVBoxLayout()

        headerLayout = QHBoxLayout()
        self.mixerLabel = QLabel(f"Connected to Mixer: {self.mixerName}")
        self.mixerLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.mixerLabel.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; {font_style}")
        headerLayout.addWidget(self.mixerLabel)
        
        # Disconnect button
        self.disconnectButton = QPushButton("Disconnect")
        self.disconnectButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.disconnectButton.clicked.connect(self.disconnect)
        headerLayout.addWidget(self.disconnectButton, alignment=Qt.AlignmentFlag.AlignRight)

        self.mainLayout.addLayout(headerLayout)

        topLayout = QHBoxLayout()

        leftPanelLayout = QVBoxLayout()

        self.toggleMuteButton = QPushButton("Mute")
        self.toggleMuteButton.setCheckable(True)
        self.toggleMuteButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.toggleMuteButton.clicked.connect(self.toggleMute)
        leftPanelLayout.addWidget(self.toggleMuteButton)

        self.fader = CustomFader(self.client, self.channelNum, Qt.Orientation.Vertical)
        leftPanelLayout.addWidget(self.fader)

        self.selectChannelButton = QPushButton("Channel")
        self.selectChannelButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.selectChannelButton.clicked.connect(self.showChannelSelector)
        leftPanelLayout.addWidget(self.selectChannelButton)

        topLayout.addLayout(leftPanelLayout)

        self.graphWidget = pg.GraphicsLayoutWidget(show=True)
        self.plot = self.graphWidget.addPlot(title="RTA")
        self.plot.setLogMode(x=True, y=False)
        self.plot.setYRange(-90, 0)
        self.plot.setLabel('bottom', 'Frequency', units='Hz')
        self.plot.setLabel('left', 'dB')
        self.plot.showGrid(x=True, y=True)
        topLayout.addWidget(self.graphWidget)

        eqControls = QVBoxLayout()

        self.rtaToggle = QPushButton("RTA")
        self.rtaToggle.setCheckable(True)
        self.rtaToggle.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.rtaToggle.setChecked(False)
        self.rtaToggle.clicked.connect(self.togglePlotUpdates)
        eqControls.addWidget(self.rtaToggle)

        self.fineButton = QPushButton("Fine")
        self.fineButton.setCheckable(True)
        self.fineButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.fineButton.setChecked(False)
        self.fineButton.clicked.connect(self.toggleFineMode)
        eqControls.addWidget(self.fineButton)

        self.eqToggleButton = QPushButton("EQ")
        self.eqToggleButton.setCheckable(True)
        self.eqToggleButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.eqToggleButton.setChecked(False)
        self.eqToggleButton.clicked.connect(self.toggleEQ)
        eqControls.addWidget(self.eqToggleButton)

        # Trim Control
        trimLayout = QVBoxLayout()
        trimLabel = QLabel("Trim")
        trimLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trimLayout.addWidget(trimLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        self.trimDial = QDial()
        self.trimDial.setRange(int(min(trimValues.keys())), int(max(trimValues.keys())))
        self.trimDial.setValue(0)
        self.trimDial.valueChanged.connect(self.changeTrim)
        trimLayout.addWidget(self.trimDial, alignment=Qt.AlignmentFlag.AlignCenter)
        eqControls.addLayout(trimLayout)

        # Low Cut Control
        lowcutLayout = QVBoxLayout()
        lowcutLabel = QLabel("Low Cut")
        lowcutLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lowcutLayout.addWidget(lowcutLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lowcutDial = QDial()
        self.lowcutDial.setRange(int(min(lowcutFreq.keys())), int(max(lowcutFreq.keys())))
        self.lowcutDial.setValue(100)
        self.lowcutDial.valueChanged.connect(self.changeLowCut)
        lowcutLayout.addWidget(self.lowcutDial, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lowCutToggleButton = QPushButton("Low Cut")
        self.lowCutToggleButton.setCheckable(True)
        self.lowCutToggleButton.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.lowCutToggleButton.setChecked(False)
        self.lowCutToggleButton.clicked.connect(self.toggleLowCut)
        lowcutLayout.addWidget(self.lowCutToggleButton, alignment=Qt.AlignmentFlag.AlignCenter)
        eqControls.addLayout(lowcutLayout)

        # EQ Mode Control
        eqTypeLayout = QVBoxLayout()
        eqTypeLabel = QLabel("EQ Mode")
        eqTypeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eqTypeLayout.addWidget(eqTypeLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        self.eqTypeDropdown = QComboBox()
        self.eqTypeDropdown.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.eqTypeDropdown.addItems(["LCut", "LShv", "PEQ", "VEQ", "HShv", "HCut"])
        self.eqTypeDropdown.currentIndexChanged.connect(self.changeEQMode)  # Connect the signal to the handler
        eqTypeLayout.addWidget(self.eqTypeDropdown, alignment=Qt.AlignmentFlag.AlignCenter)
        eqControls.addLayout(eqTypeLayout)

        # AudioPilot Control
        pitchLayout = QVBoxLayout()
        self.pitchToggle = QPushButton("AudioPilot")
        self.pitchToggle.setCheckable(True)
        self.pitchToggle.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.pitchToggle.setChecked(False)
        self.pitchToggle.clicked.connect(self.togglePitchCorrection)
        pitchLayout.addWidget(self.pitchToggle, alignment=Qt.AlignmentFlag.AlignCenter)
        self.pitchTypeSelector = QComboBox()
        self.pitchTypeSelector.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        self.pitchTypeSelector.addItems(["Low Pitch", "Mid Pitch", "High Pitch"])
        pitchLayout.addWidget(self.pitchTypeSelector, alignment=Qt.AlignmentFlag.AlignCenter)
        eqControls.addLayout(pitchLayout)

        topLayout.addLayout(eqControls)
        self.mainLayout.addLayout(topLayout)

        eqControlsLayout = QVBoxLayout()

        bandSelectionLayout = QHBoxLayout()
        self.bandButtons = QButtonGroup(self)
        bands = ["Low", "LoMid", "HiMid", "High"]
        for index, band in enumerate(bands):
            btn = QPushButton(band)
            btn.setCheckable(True)
            btn.setFixedSize(145, 35)
            btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
            self.bandButtons.addButton(btn, index + 1)
            bandSelectionLayout.addWidget(btn)
        self.bandButtons.buttonClicked.connect(self.changeBand)
        eqControlsLayout.addLayout(bandSelectionLayout)

        dialsLayout = QHBoxLayout()

        freqLayout = QVBoxLayout()
        freqLabel = QLabel("Frequency")
        freqLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.freqDial = QDial()
        self.freqDial.setRange(int(min(map(float, eqFreq.keys()))), int(max(map(float, eqFreq.keys()))))
        self.freqDial.setValue(1000)
        self.freqDial.setFixedSize(80, 80)
        self.freqDial.valueChanged.connect(self.changeFreq)
        freqLayout.addWidget(freqLabel)
        freqLayout.addWidget(self.freqDial)
        dialsLayout.addLayout(freqLayout)

        qLayout = QVBoxLayout()
        qLabel = QLabel("Quality")
        qLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qDial = QDial()
        self.qDial.setRange(int(min(qValues.keys())), int(max(qValues.keys())))
        self.qDial.setValue(5)
        self.qDial.setFixedSize(80, 80)
        self.qDial.valueChanged.connect(self.changeQ)
        qLayout.addWidget(qLabel)
        qLayout.addWidget(self.qDial)
        dialsLayout.addLayout(qLayout)

        smallGainLayout = QVBoxLayout()
        smallGainLabel = QLabel("Gain")
        smallGainLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.smallGainDial = QDial()
        self.smallGainDial.setRange(int(min(eqGainValues.keys())), int(max(eqGainValues.keys())))
        self.smallGainDial.setValue(0)
        self.smallGainDial.setFixedSize(80, 80)
        self.smallGainDial.valueChanged.connect(self.changeEqGain)
        smallGainLayout.addWidget(smallGainLabel)
        smallGainLayout.addWidget(self.smallGainDial)
        dialsLayout.addLayout(smallGainLayout)

        eqControlsLayout.addLayout(dialsLayout)
        self.mainLayout.addLayout(eqControlsLayout)

        self.setLayout(self.mainLayout)

        # Set the default band button to be checked and update its style
        default_band_button = self.bandButtons.button(self.selectedBand)
        if default_band_button:
            default_band_button.setChecked(True)
            default_band_button.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}; color: {TEXT_COLOR}; {font_style}")

        self.setLayout(self.mainLayout)
        self.setWindowTitle('Audio Pilot')

    def changeBand(self, button):
        self.selectedBand = self.bandButtons.id(button)
        for btn in self.bandButtons.buttons():
            btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
        button.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}; color: {TEXT_COLOR}; {font_style}")

    def changeEQMode(self, index):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        
        eq_mode_id = index  # Since the index corresponds to the enum value 0..5
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/eq/{self.selectedBand}/type', [eq_mode_id])
        print(f'Sent OSC message: /ch/{channel_num_formatted}/eq/{self.selectedBand}/type {eq_mode_id}')

    def toggleFineMode(self):
        is_fine = self.fineButton.isChecked()
        self.fineButton.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}" if is_fine else f"background-color: {BUTTON_COLOR}")
        self.fader.setFineMode(is_fine)

    def togglePlotUpdates(self):
        if self.rtaToggle.isChecked() and self.plotMgr is not None:
            self.rtaToggle.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}")
            if not self.plotMgr.plottingActive:
                self.plotMgr.start()
        else:
            self.rtaToggle.setStyleSheet(f"background-color: {BUTTON_COLOR}")
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
            self.fader.channel_num = self.channelNum  # Set channel number for fader
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
            channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
            if self.toggleMuteButton.isChecked():
                self.client.send_message(f'/ch/{channel_num_formatted}/mix/on', 0)
                self.toggleMuteButton.setStyleSheet(f"background-color: #A40606")
                print(f"Channel {channel_num_formatted} is muted.")
            else:
                self.client.send_message(f'/ch/{channel_num_formatted}/mix/on', 1)
                self.toggleMuteButton.setStyleSheet(f"background-color: {BUTTON_COLOR}")
                print(f"Channel {channel_num_formatted} is unmuted.")

    def togglePitchCorrection(self):
        if self.pitchToggle.isChecked():
            self.pitchToggle.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}")
            vocalType = self.pitchTypeSelector.currentText()
            self.startBandManager(vocalType)
        else:
            self.pitchToggle.setStyleSheet(f"background-color: {BUTTON_COLOR}")
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
        closest_value = min(eqGainValues.keys(), key=lambda k: abs(k - value))
        gain_id = eqGainValues[closest_value]
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/eq/{self.selectedBand}/g', [gain_id])

    def changeLowCut(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closest_value = min(lowcutFreq.keys(), key=lambda k: abs(k - value))
        lowcut_freq_id = lowcutFreq[closest_value]
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/preamp/hpf', [lowcut_freq_id])

    def changeFreq(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        def convert_freq_to_float(freq):
            return float(freq)

        freq_keys = [convert_freq_to_float(k) for k in eqFreq.keys()]
        closest_value = min(freq_keys, key=lambda k: abs(k - value))
        # Find the closest key in its original string format
        closest_key = min(eqFreq.keys(), key=lambda k: abs(float(k) - closest_value))
        freq_id = eqFreq[closest_key]
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/eq/{self.selectedBand}/f', [freq_id])

    def changeQ(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closest_value = min(qValues.keys(), key=lambda k: abs(k - value))
        q_value_id = qValues[closest_value]
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/eq/{self.selectedBand}/q', [q_value_id])

    def changeTrim(self, value):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        closest_value = min(trimValues.keys(), key=lambda k: abs(k - value))
        trim_id = trimValues[closest_value]
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/preamp/trim', [trim_id])

    def toggleEQ(self):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        state = 1 if self.eqToggleButton.isChecked() else 0
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/eq/on/', [state])
        self.eqToggleButton.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}" if state else f"background-color: {BUTTON_COLOR}")

    def toggleLowCut(self):
        if self.channelNum is None:
            print("Channel number is not set.")
            return
        state = 1 if self.lowCutToggleButton.isChecked() else 0
        channel_num_formatted = f"{self.channelNum + 1:02}"  # Format channelNum as two-digit
        self.client.send_message(f'/ch/{channel_num_formatted}/preamp/hpon', [state])
        self.lowCutToggleButton.setStyleSheet(f"background-color: {BUTTON_SELECTED_COLOR}" if state else f"background-color: {BUTTON_COLOR}")

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
        from main import center_widget
        self.stopPlotting()
        self.applyBlurEffect()  # Apply blur effect before showing MixerDiscoveryUI
        self.mixerDiscovery = MixerDiscoveryUI(self)  # Pass self as parent to keep it modal
        center_widget(self.mixerDiscovery, self)
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
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; {font_style}")
        layout = QGridLayout()
        self.button_group = QButtonGroup(self)

        for i in range(1, 33):
            btn = QPushButton(f"CH {i:02}")
            btn.setCheckable(True)
            btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; {font_style}")
            btn.clicked.connect(self.chooseChannel)
            self.button_group.addButton(btn, i)
            layout.addWidget(btn, (i-1)//8, (i-1)%8)

        self.setLayout(layout)

    def chooseChannel(self):
        selectedButton = self.button_group.checkedButton()
        if selectedButton:
            self.selectedChannel = selectedButton.text()
            self.accept()
