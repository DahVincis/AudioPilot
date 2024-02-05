from pythonosc import dispatcher, osc_server

def handle_unprocessed_data(address, *args):
    print(f"Received {address}: {args}")
    # Implement your data processing here

disp = dispatcher.Dispatcher()
disp.map("/ch/01/eq/1/f", handle_unprocessed_data)  # Adjust the mapping as needed

server = osc_server.ThreadingOSCUDPServer(
  ('0.0.0.0', 10123), disp)  # Listen on all interfaces, port 10123
print(f"Serving on {server.server_address}")
server.serve_forever()
