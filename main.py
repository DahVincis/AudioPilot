import sys
import argparse
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QIcon, QPixmap
from ctypes import windll
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from ui import MixerDiscoveryUI
from osc_handlers import RTASubscriber, OscHandlers
from utils import ApplicationManager

# Explicit App User Model ID for Windows taskbar icon
myappid = 'mycompany.myproduct.subproduct.version'
windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

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
    while True:
        mixerDiscoveryDialog = MixerDiscoveryUI()
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

            appManager = ApplicationManager(client, server, chosenName)
            appManager.run()
        else:
            sys.exit()
