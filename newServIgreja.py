from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import argparse
import threading
import time

# Configuration for the Behringer device
behringer_addr = '198.168.0.100'

# Function to send OSC messages to query the Behringer device
def query_behringer_state(client):
    while True:
        print("Querying Behringer device state...")
        # Sending queries about various faders and on/off states
        client.send_message('/mtx/02/mix/fader', None)
        client.send_message('/mtx/01/mix/fader', None)
        client.send_message('/mtx/01/mix/on', None)
        client.send_message('/ch/01/mix/on', None)
        client.send_message('/mtx/02/mix/on', None)
        client.send_message('/main/st/mix/on', None)
        client.send_message('/main/st/mix/fader', None)
        time.sleep(10)  # Adjust this interval as needed

# Callback function for printing received OSC messages
def print_osc_data(address, *args):
    print(f"Received OSC message: Address: {address}, Args: {args}")

if __name__ == "__main__":
    # Parse command line arguments for IP and port
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The IP to listen on")
    parser.add_argument("--port", type=int, default=10023, help="The port to listen on")
    args = parser.parse_args()

    # Initialize the OSC client and server
    client = SimpleUDPClient(behringer_addr, args.port)
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(print_osc_data)

    # Create the OSC server
    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    print(f"Serving on {server.server_address}")

    # Start a thread for querying the Behringer device state
    query_thread = threading.Thread(target=query_behringer_state, args=(client,))
    query_thread.start()

    # Start the OSC server to listen for and print incoming OSC messages
    server.serve_forever()
