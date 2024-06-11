import sys
import argparse
from PyQt6.QtWidgets import QApplication, QDialog
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from ui import MixerDiscoveryUI
from osc_handlers import RTASubscriber, FaderHandler
from utils import ApplicationManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mixerDiscoveryDialog = MixerDiscoveryUI()
    if mixerDiscoveryDialog.exec() == QDialog.DialogCode.Accepted:
        chosenIP = mixerDiscoveryDialog.selectedMixerIp
        client = SimpleUDPClient(chosenIP, 10023)

        parser = argparse.ArgumentParser()
        parser.add_argument("--ip", default="0.0.0.0", help="The IP to listen on")
        parser.add_argument("--port", type=int, default=10024, help="The port to listen on")
        args = parser.parse_args()

        dispatcher = Dispatcher()
        subRTA = RTASubscriber(client)
        faderHandler = FaderHandler()
        dispatcher.map("/meters", subRTA.handlerRTA)

        server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
        print(f"Serving on {server.server_address}")
        client._sock = server.socket

        appManager = ApplicationManager(client, server)
        appManager.run(chosenIP)
    else:
        sys.exit()