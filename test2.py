import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QComboBox, QDial, QGridLayout, QDialog, QFormLayout, QDialogButtonBox, QButtonGroup, QGraphicsRectItem
)
from PyQt6.QtCore import Qt, QTimer, QRectF
import pyqtgraph as pg
import numpy as np

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
            btn.clicked.connect(self.select_channel)
            self.button_group.addButton(btn, i)
            layout.addWidget(btn, (i-1)//8, (i-1)%8)

        self.setLayout(layout)

    def select_channel(self):
        selected_button = self.button_group.checkedButton()
        if selected_button:
            self.selected_channel = selected_button.text()
            self.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.pitch_type_selector = QComboBox()
        self.pitch_type_selector.addItems(["Low Pitch", "Mid Pitch", "High Pitch"])
        layout.addRow("Pitch Type:", self.pitch_type_selector)

        self.lowcut_dial = QDial()
        self.lowcut_dial.setRange(20, 400)  # Frequency range in Hz
        self.lowcut_dial.setValue(100)
        layout.addRow("Lowcut Frequency:", self.lowcut_dial)

        self.setLayout(layout)

class AudioMixerUI(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Top layout
        top_layout = QHBoxLayout()

        # Left panel: Fader and channel controls
        left_panel = QVBoxLayout()

        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.clicked.connect(self.toggle_mute)
        left_panel.addWidget(self.mute_button)

        self.fader = QSlider(Qt.Orientation.Vertical)
        self.fader.setRange(-90, 10)  # dB range
        self.fader.setValue(0)
        left_panel.addWidget(self.fader)

        self.channel_selector_button = QPushButton("Select Channel")
        self.channel_selector_button.clicked.connect(self.open_channel_selector)
        left_panel.addWidget(self.channel_selector_button)

        top_layout.addLayout(left_panel)

        # Middle panel: RTA plot
        self.plot_widget = pg.GraphicsLayoutWidget(show=True)
        self.plot = self.plot_widget.addPlot(title="RTA")
        self.plot.setLogMode(x=True, y=False)
        self.plot.setYRange(-90, 0)
        self.plot.setLabel('bottom', 'Frequency', units='Hz')
        self.plot.setLabel('left', 'dB')
        self.plot.showGrid(x=True, y=True)
        top_layout.addWidget(self.plot_widget)

        # Add a semi-transparent rectangle for dimming effect
        self.dim_rect = QGraphicsRectItem(QRectF(self.plot.vb.viewRect()))
        self.dim_rect.setBrush(pg.mkBrush((0, 0, 0, 100)))  # Semi-transparent black
        self.dim_rect.setZValue(10)  # Ensure it is on top
        self.plot.addItem(self.dim_rect)
        self.dim_rect.hide()

        # Right panel: EQ controls and settings
        right_panel = QVBoxLayout()

        self.eq_on_button = QPushButton("EQ On/Off")
        self.eq_on_button.setCheckable(True)
        self.eq_on_button.clicked.connect(self.toggle_eq)
        right_panel.addWidget(self.eq_on_button)

        gain_layout = QVBoxLayout()
        gain_label = QLabel("Gain Level")
        gain_layout.addWidget(gain_label)
        self.gain_dial = QDial()
        self.gain_dial.setRange(-15, 15)  # Gain range in dB
        self.gain_dial.setValue(0)
        gain_layout.addWidget(self.gain_dial)
        right_panel.addLayout(gain_layout)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        right_panel.addWidget(self.settings_button)

        self.band_selector = QComboBox()
        self.band_selector.addItems(["Low", "Low Mid", "High Mid", "High"])
        right_panel.addWidget(self.band_selector)

        top_layout.addLayout(right_panel)

        main_layout.addLayout(top_layout)

        # Bottom layout for EQ dials
        eq_controls = QHBoxLayout()
        
        freq_layout = QVBoxLayout()
        freq_label = QLabel("Freq")
        self.freq_dial = QDial()
        self.freq_dial.setRange(20, 20000)  # Frequency range in Hz
        self.freq_dial.setValue(1000)
        self.freq_dial.setFixedSize(50, 50)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_dial)
        eq_controls.addLayout(freq_layout)

        q_layout = QVBoxLayout()
        q_label = QLabel("Q")
        self.q_dial = QDial()
        self.q_dial.setRange(1, 10)  # Q range
        self.q_dial.setValue(5)
        self.q_dial.setFixedSize(50, 50)
        q_layout.addWidget(q_label)
        q_layout.addWidget(self.q_dial)
        eq_controls.addLayout(q_layout)

        gain_layout_small = QVBoxLayout()
        gain_label_small = QLabel("Gain")
        self.gain_dial_small = QDial()
        self.gain_dial_small.setRange(-12, 12)  # Gain range in dB
        self.gain_dial_small.setValue(0)
        self.gain_dial_small.setFixedSize(50, 50)
        gain_layout_small.addWidget(gain_label_small)
        gain_layout_small.addWidget(self.gain_dial_small)
        eq_controls.addLayout(gain_layout_small)

        main_layout.addLayout(eq_controls)

        self.setLayout(main_layout)

        # Timer to update plot periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        self.setWindowTitle('Audio Mixer')
        self.show()

    def update_plot(self):
        # Dummy data for the plot, replace with actual data
        freqs = np.logspace(np.log10(20), np.log10(20000), num=102)
        db_values = np.random.uniform(-90, 0, size=102)
        self.plot.clear()
        self.plot.plot(freqs, db_values, pen='g')

    def open_channel_selector(self):
        self.channel_selector_dialog = ChannelSelectorDialog(self)
        if self.channel_selector_dialog.exec() == QDialog.DialogCode.Accepted:
            self.channel_selector_button.setText(self.channel_selector_dialog.selected_channel)

    def open_settings_dialog(self):
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.exec()

    def toggle_mute(self):
        if self.mute_button.isChecked():
            self.mute_button.setStyleSheet("background-color: red")
            print("Channel is muted.")
        else:
            self.mute_button.setStyleSheet("background-color: gray")
            print("Channel is unmuted.")

    def toggle_eq(self):
        if self.eq_on_button.isChecked():
            self.dim_rect.hide()
            print("EQ is on.")
        else:
            self.dim_rect.show()
            print("EQ is off.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = AudioMixerUI()
    sys.exit(app.exec())