import sys
import os
import argparse
from PyQt6.QtWidgets import QApplication, QDialog
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
myappid = 'AudioPilot.AudioPilot.App.2_5'
windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def alignWidgetCenter(widget, parent):
    rect = parent.geometry()
    widgetCenter = widget.geometry()
    widgetCenter.moveCenter(rect.center())
    widget.setGeometry(widgetCenter)

def rPath(relativePath):
    """ Get the absolute path to a resource, works for dev and PyInstaller """
    basePath = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basePath, relativePath)

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

    # Load QSS stylesheet
    qssFilePath = rPath("styles.qss")
    with open(qssFilePath, "r") as f:
        app.setStyleSheet(f.read())

    # Path to your logo image
    logoPath = rPath("AudioPilot_Logo2.png")

    # Create a QIcon with multiple sizes
    applicationIcon = QIcon()
    for size in [16, 24, 32, 48, 256]:
        pixmap = QPixmap(logoPath)
        scaled = pixmap.scaled(size, size)
        applicationIcon.addPixmap(scaled)

    app.setWindowIcon(applicationIcon)  # Set the application icon globally

    # Initialize AudioPilotUI but don't show it yet
    audioPilotUI = AudioPilotUI("", None)
    audioPilotUI.applyBlurEffect()
    audioPilotUI.show()

    mixerDiscoveryDialog = MixerDiscoveryUI()
    mixerDiscoveryDialog.setParent(audioPilotUI, Qt.WindowType.Dialog)
    mixerDiscoveryDialog.setModal(True)
    alignWidgetCenter(mixerDiscoveryDialog, audioPilotUI)

    # Show mixer discovery dialog first
    if mixerDiscoveryDialog.exec() == QDialog.DialogCode.Accepted:
        audioPilotUI.close()
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
        apUI = audioPilotUI
        apUI.mixerName = chosenName
        apUI.client = client
        apUI.updateUI()  # Update the UI with the new mixer settings

        oscServerThread = OSCServerThread(server)
        oscServerThread.start()

        appManager = ApplicationManager(client, server, chosenName)
        appManager.run()
    else:
        audioPilotUI.close()
        sys.exit(app.exec())