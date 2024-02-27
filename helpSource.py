import argparse

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server

from pythonosc import osc_packet
from typing import overload, List, Union, Any, Generator, Tuple
from types import FunctionType
from pythonosc.osc_message import OscMessage
import time
import socket
import threading

last_recv_addr = None
behringer_addr = '198.168.56.1'
client = udp_client.SimpleUDPClient(behringer_addr, 10023)

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
    time.sleep(5)

class MyDispatcher(dispatcher.Dispatcher):
  def call_handlers_for_packet(self, data: bytes, client_address: Tuple[str, int]) -> None:
    # ugly. Needs refactoring
    global last_recv_addr
    global behringer_addr
    # Get OSC messages from all bundles or standalone message.
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

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="0.0.0.0", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=10023, help="The port to listen on")
  args = parser.parse_args()

  dispatcher = MyDispatcher()

  server = osc_server.ThreadingOSCUDPServer(
      (args.ip, args.port), dispatcher)
  print("Serving on {}".format(server.server_address))
  client._sock = server.socket
  x = threading.Thread(target=keep_behringer_awake)
  x.start()
  server.serve_forever()