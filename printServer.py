import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import numpy as np

# IP and port configuration
MIXER_IP = '192.168.56.1'  # Replace with the IP address of your X32 mixer
MIXER_PORT = 10023          # Port on which the X32 OSC server is running
LOCAL_IP = '0.0.0.0'        # Listen on all local IPs
LOCAL_PORT = 10024          # Port on which this script's OSC server will listen

# OSC message dispatcher setup
dispatcher = Dispatcher()

# Function to handle RTA data for channel 19
def handle_rta_data(address, *args):
    osc_blob = args[0]
    # Assuming the blob data is little-endian 16-bit integers
    new_data = np.frombuffer(osc_blob, dtype='<i2').reshape(-1)
    new_data_float = new_data.astype(np.float32) / 256.0  # Convert to float and scale
    print(f"Received RTA data: {new_data_float[:5]}...")  # Print the first 5 values

# Default handler for unhandled messages
def default_handler(address, *args):
    print(f"DEFAULT {address}: {args}")

# Register the handlers with the dispatcher
dispatcher.map("/meters/15", handle_rta_data)
dispatcher.set_default_handler(default_handler)

# Function to maintain the X32 in remote mode
async def keep_xremote_active(client):
    while True:
        client.send_message("/xremote", ["on"])
        await asyncio.sleep(9)  # Send every 9 seconds

# Function to create and start the OSC server
async def init_osc_server():
    server = AsyncIOOSCUDPServer((LOCAL_IP, LOCAL_PORT), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Start the server
    return transport, server

# Main coroutine
async def main():
    client = SimpleUDPClient(MIXER_IP, MIXER_PORT)  # OSC client for sending messages to the X32
    transport, server = await init_osc_server()     # OSC server for receiving messages

    # Start the background task to keep the X32 mixer in remote mode
    asyncio.create_task(keep_xremote_active(client))

    print("OSC server is running. Waiting for messages...")
    try:
        while True:
            await asyncio.sleep(3600)  # Keep the script running indefinitely
    except KeyboardInterrupt:
        print("Stopping OSC server.")
        transport.close()

# Run the main coroutine
if __name__ == '__main__':
    asyncio.run(main())