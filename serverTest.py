from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import numpy as np
from pythonosc import osc_packet
import argparse
import time
import socket
import threading
from typing import overload, List, Union, Any, Generator, Tuple
from types import FunctionType

last_recv_addr = None
behringer_addr = '198.168.0.100'
client = SimpleUDPClient(behringer_addr, 10023)

def keep_behringer_awake():
  while True:
    print("send xremote and mtx fader poll")
    client.send_message('/xremote', None)
    client.send_message('/mtx/02/mix/fader', None)
    client.send_message('/mtx/01/mix/fader', None)
    client.send_message('/mtx/01/mix/on', None)
    client.send_message('/ch/01/mix/on', None)
    client.send_message('/mtx/02/mix/on', None)
    client.send_message('/main/st/mix/on', None)
    client.send_message('/main/st/mix/fader', None)
    client.send_message("/meters/15", [])
    client.send_message("-action/setrtasrc", [116])  # Set RTA meter to channel 19
    client.send_message("/subscribe", ["/meters/15", 1])  # Subscribe to RTA data
    client.send_message("-action", ["get", "/meters/15"]) # Request RTA data
    time.sleep(5)

class MyDispatcher(Dispatcher):
    def call_handlers_for_packet(self, data: bytes, client_address: Tuple[str, int]) -> None:
        print("Handler working...", data, client_address)
        pass

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="0.0.0.0", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=10023, help="The port to listen on")
  args = parser.parse_args()

  dispatcher = MyDispatcher()

  server = ThreadingOSCUDPServer(
      (args.ip, args.port), dispatcher)
  print("Serving on {}".format(server.server_address))
  client._sock = server.socket
  x = threading.Thread(target=keep_behringer_awake)
  x.start()
  server.serve_forever()