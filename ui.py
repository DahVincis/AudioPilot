import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QHBoxLayout, QSlider, QComboBox, QDial, QFormLayout, QButtonGroup, QGraphicsRectItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QRectF, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor
import pyqtgraph as pg
import threading
import time

from utils import MixerDiscovery, PlotManager, BandManager
from Data import faderData

class MixerDiscoveryWorker(QThread):
    mixersFound = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.mixerScanner = MixerDiscovery()

    def run(self):
        availableMixers = self.mixerScanner.discoverMixers()
        self.mixersFound.emit(availableMixers)

class MixerDiscoveryUI(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mixer Discovery")
        self.setGeometry(100, 100, 400, 200)
        self.initUI()
        self.mixerWorker = MixerDiscoveryWorker()
        self.mixerWorker.mixersFound.connect(self.updateMixerGrid)
        self.mixerWorker.start()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.infoLabel = QLabel("Searching for mixers...")
        self.layout.addWidget(self.infoLabel)
        self.mixerGridLayout = QGridLayout()
        self.layout.addLayout(self.mixerGridLayout)
        self.setLayout(self.layout)

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
            mixerButton = QPushButton("Select")
            mixerButton.clicked.connect(lambda _, ip=ip, name=details.split('|')[1].strip(): self.chooseMixer(ip, name))
            self.mixerGridLayout.addWidget(mixerLabel, row, 0)
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
        # Replace special minus character with standard minus sign
        corrected_keys = [key.replace('‐', '-') for key in faderData.keys()]
        min_value = min(map(lambda x: int(float(x) * self.scale_factor), corrected_keys))
        max_value = max(map(lambda x: int(float(x) * self.scale_factor), corrected_keys))
        self.setRange(min_value, max_value)
        self.setValue(0)
        self.valueChanged.connect(self.sendOscMessage)
        self.tick_interval = (self.maximum() - self.minimum()) / 10

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tickColor = QColor(0, 0, 0)  # Black color for ticks
        painter.setPen(tickColor)

        rect = self.rect()
        interval = (rect.height() - 20) / (self.maximum() - self.minimum())

        # Define the positions and values for the labels we want to show
        tick_positions = [10, 5, 0, -10, -20, -30, -40, -50, -70, -90]
        scaled_ticks = [int(tick * self.scale_factor) for tick in tick_positions]
        for tick in scaled_ticks:
            y = rect.height() - ((tick - self.minimum()) * interval) - 10
            painter.drawLine(30, int(y), rect.width(), int(y))  # Draw line across the fader
            painter.drawText(5, int(y) + 5, str(tick / self.scale_factor))  # Draw the label to the left of the tick

        painter.end()

    def sizeHint(self):
        return QSize(80, 200)  # Increase width to ensure labels fit

    def sendOscMessage(self):
        db_value = self.value() / self.scale_factor
        corrected_keys = {key.replace('‐', '-'): value for key, value in faderData.items()}
        float_id = corrected_keys.get(str(db_value), None)
        if float_id is not None and self.channel_num is not None:
            self.client.send_message(f'/ch/{self.channel_num + 1}/mix/fader', [float_id])
            self.valueChangedSignal.emit(float_id)

class AudioPilotUI(QWidget):
    def __init__(self, mixerName, client):
        super().__init__()
        self.mixerName = mixerName
        self.client = client
        self.plotMgr = None
        self.channelNum = None
        self.bandManagerThread = None
        self.bandThreadRunning = threading.Event()
        self.isMuted = False  # Initial state is muted
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Audio Pilot')
        self.setGeometry(100, 100, 1280, 768)  # Adjust the initial window size

        mainLayout = QVBoxLayout()

        headerLayout = QHBoxLayout()
        self.mixerLabel = QLabel(f"Connected to Mixer: {self.mixerName}")
        headerLayout.addWidget(self.mixerLabel)
        mainLayout.addLayout(headerLayout)

        topLayout = QHBoxLayout()

        leftPanelLayout = QVBoxLayout()

        self.toggleMuteButton = QPushButton("Mute")
        self.toggleMuteButton.setCheckable(True)
        self.toggleMuteButton.setStyleSheet("background-color: gray")  # Initial state
        self.toggleMuteButton.clicked.connect(self.toggleMute)
        leftPanelLayout.addWidget(self.toggleMuteButton)

        self.fader = CustomFader(self.client, self.channelNum, Qt.Orientation.Vertical)
        leftPanelLayout.addWidget(self.fader)

        self.selectChannelButton = QPushButton("Select Channel")
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

        self.dimmingRectangle = QGraphicsRectItem(QRectF(self.plot.vb.viewRect()))
        self.dimmingRectangle.setBrush(pg.mkBrush((0, 0, 0, 100)))
        self.dimmingRectangle.setZValue(10)
        self.plot.addItem(self.dimmingRectangle)
        self.dimmingRectangle.hide()

        eqControls = QVBoxLayout()

        self.rtaToggle = QPushButton("RTA")
        self.rtaToggle.setCheckable(True)
        self.rtaToggle.setStyleSheet("background-color: gray")
        self.rtaToggle.setChecked(False)
        self.rtaToggle.clicked.connect(self.togglePlotUpdates)
        eqControls.addWidget(self.rtaToggle)

        gainLayout = QVBoxLayout()
        gainLabel = QLabel("Gain Level")
        gainLayout.addWidget(gainLabel)
        self.gainDial = QDial()
        self.gainDial.setRange(-15, 15)
        self.gainDial.setValue(0)
        gainLayout.addWidget(self.gainDial)
        eqControls.addLayout(gainLayout)

        lowcutLayout = QVBoxLayout()
        lowcutLabel = QLabel("Lowcut Frequency")
        lowcutLayout.addWidget(lowcutLabel)
        self.lowcutDial = QDial()
        self.lowcutDial.setRange(20, 400)
        self.lowcutDial.setValue(100)
        lowcutLayout.addWidget(self.lowcutDial)
        eqControls.addLayout(lowcutLayout)

        pitchLayout = QVBoxLayout()
        self.pitchTypeSelector = QComboBox()
        self.pitchTypeSelector.addItems(["Low Pitch", "Mid Pitch", "High Pitch"])
        pitchLayout.addWidget(self.pitchTypeSelector)

        self.pitchToggle = QPushButton("AudioPilot")
        self.pitchToggle.setCheckable(True)
        self.pitchToggle.setStyleSheet("background-color: gray")
        self.pitchToggle.setChecked(False)
        self.pitchToggle.clicked.connect(self.togglePitchCorrection)
        pitchLayout.addWidget(self.pitchToggle)

        eqControls.addLayout(pitchLayout)

        topLayout.addLayout(eqControls)

        mainLayout.addLayout(topLayout)

        eqControlsLayout = QHBoxLayout()

        freqLayout = QVBoxLayout()
        freqLabel = QLabel("Freq")
        self.freqDial = QDial()
        self.freqDial.setRange(20, 20000)
        self.freqDial.setValue(1000)
        self.freqDial.setFixedSize(50, 50)
        freqLayout.addWidget(freqLabel)
        freqLayout.addWidget(self.freqDial)
        eqControlsLayout.addLayout(freqLayout)

        qLayout = QVBoxLayout()
        qLabel = QLabel("Q")
        self.qDial = QDial()
        self.qDial.setRange(1, 10)
        self.qDial.setValue(5)
        self.qDial.setFixedSize(50, 50)
        qLayout.addWidget(qLabel)
        qLayout.addWidget(self.qDial)
        eqControlsLayout.addLayout(qLayout)

        smallGainLayout = QVBoxLayout()
        smallGainLabel = QLabel("Gain")
        self.smallGainDial = QDial()
        self.smallGainDial.setRange(-12, 12)
        self.smallGainDial.setValue(0)
        self.smallGainDial.setFixedSize(50, 50)
        smallGainLayout.addWidget(smallGainLabel)
        smallGainLayout.addWidget(self.smallGainDial)
        eqControlsLayout.addLayout(smallGainLayout)

        mainLayout.addLayout(eqControlsLayout)

        self.setLayout(mainLayout)

        self.setWindowTitle('Audio Pilot')
        self.show()

    def togglePlotUpdates(self):
        if self.rtaToggle.isChecked():
            self.rtaToggle.setStyleSheet("background-color: green")
            if not self.plotMgr.plottingActive:
                self.plotMgr.start()
        else:
            self.rtaToggle.setStyleSheet("background-color: gray")
            if self.plotMgr.plottingActive:
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
            if self.toggleMuteButton.isChecked():
                self.client.send_message(f'/ch/{self.channelNum +1}/mix/on', 0)
                self.toggleMuteButton.setStyleSheet("background-color: red")
                print(f"Channel {self.channelNum +1} is muted.")
            else:
                self.client.send_message(f'/ch/{self.channelNum +1}/mix/on', 1)
                self.toggleMuteButton.setStyleSheet("background-color: gray")
                print(f"Channel {self.channelNum +1} is unmuted.")

    def togglePitchCorrection(self):
        if self.pitchToggle.isChecked():
            self.pitchToggle.setStyleSheet("background-color: orange")
            vocalType = self.pitchTypeSelector.currentText()
            self.startBandManager(vocalType)
        else:
            self.pitchToggle.setStyleSheet("background-color: gray")
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
        selectedButton = self.button_group.checkedButton()
        if selectedButton:
            self.selectedChannel = selectedButton.text()
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
        self.lowcutDial.setRange(20, 400)  # frequency range in Hz
        self.lowcutDial.setValue(100)
        layout.addRow("Lowcut Frequency:", self.lowcutDial)

        self.setLayout(layout)