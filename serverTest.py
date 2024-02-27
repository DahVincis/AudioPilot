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
behringer_addr = '198.168.56.1'
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
        try:
        # Loop prevention
            if client_address[0] != behringer_addr:
                client._sock.sendto(data, (behringer_addr, 10023))
                last_recv_addr = client_address
            if last_recv_addr is not None:
                client._sock.sendto(data, last_recv_addr)
            packet = osc_packet.OscPacket(data)
            for timed_msg in packet.messages:
                now = time.time()
                handlers = self.handlers_for_address(timed_msg.message.address)
                if not handlers:
                    continue
                # If the message is to be handled later, then so be it.
                if timed_msg.time > now:
                    time.sleep(timed_msg.time - now)
                for handler in handlers:
                    handler.invoke(client_address, timed_msg.message)
        except osc_packet.ParseError:
            pass
        print("Handler working...", data, client_address)
        pass

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="0.0.0.0", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=10024, help="The port to listen on")
  args = parser.parse_args()

  dispatcher = MyDispatcher()

  server = ThreadingOSCUDPServer(
      (args.ip, args.port), dispatcher)
  print("Serving on {}".format(server.server_address))
  client._sock = server.socket
  x = threading.Thread(target=keep_behringer_awake)
  x.start()
  server.serve_forever()