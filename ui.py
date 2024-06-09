# Imports
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QHBoxLayout, QSlider, QComboBox, QDial, QFormLayout, QButtonGroup,
    QGraphicsRectItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QRectF
import pyqtgraph as pg
import threading
import time

# Local imports
from utils import MixerDiscovery, PlotManager, BandManager

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