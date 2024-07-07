import sys
import argparse
from PyQt6.QtWidgets import QApplication, QDialog, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from ctypes import windll
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from ui import MixerDiscoveryUI, AudioPilotUI
from osc_handlers import RTASubscriber, OscHandlers
from utils import ApplicationManager

# Explicit App User Model ID for Windows taskbar icon
myappid = 'mycompany.myproduct.subproduct.version'
windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def center_widget(widget, parent):
    rect = parent.geometry()
    widget_rect = widget.geometry()
    widget_rect.moveCenter(rect.center())
    widget.setGeometry(widget_rect)

class OSCServerThread(QThread):
    serverStarted = pyqtSignal()
    
    def __init__(self, server):
        super().__init__()
        self.server = server
    
    def run(self):
        self.serverStarted.emit()
        self.server.serve_forever()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Path to your logo image
    LOGO_PATH = "AudioPilot_Logo2.png"

    # Create a QIcon with multiple sizes
    app_icon = QIcon()
    for size in [16, 24, 32, 48, 256]:
        pixmap = QPixmap(LOGO_PATH)
        scaled = pixmap.scaled(size, size)
        app_icon.addPixmap(scaled)

    app.setWindowIcon(app_icon)  # Set the application icon globally

    # Initialize AudioPilotUI but don't show it yet
    audio_pilot_ui = AudioPilotUI("", None)

    mixerDiscoveryDialog = MixerDiscoveryUI()
    mixerDiscoveryDialog.setParent(audio_pilot_ui, Qt.WindowType.Dialog)
    mixerDiscoveryDialog.setModal(True)
    center_widget(mixerDiscoveryDialog, audio_pilot_ui)

    # Show mixer discovery dialog first
    if mixerDiscoveryDialog.exec() == QDialog.DialogCode.Accepted:
        chosenIP = mixerDiscoveryDialog.selectedMixerIp
        chosenName = mixerDiscoveryDialog.selectedMixerName
        client = SimpleUDPClient(chosenIP, 10023)

        parser = argparse.ArgumentParser()
        parser.add_argument("--ip", default="0.0.0.0", help="The IP to listen on")
        parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
        args = parser.parse_args()

        dispatcher = Dispatcher()
        subRTA = RTASubscriber(client)
        faderHandler = OscHandlers()
        dispatcher.map("/meters", subRTA.handlerRTA)
        dispatcher.map("/fader", faderHandler.handlerFader)

        server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
        print(f"Serving on {server.server_address}")
        client._sock = server.socket

        # Update AudioPilotUI with the selected mixer details
        audio_pilot_ui.mixerName = chosenName
        audio_pilot_ui.client = client
        audio_pilot_ui.updateUI()  # Update the UI with the new mixer settings
        audio_pilot_ui.show()

        oscServerThread = OSCServerThread(server)
        oscServerThread.start()

        appManager = ApplicationManager(client, server, chosenName)
        appManager.run()
    else:
        audio_pilot_ui.close()
        sys.exit(app.exec())
