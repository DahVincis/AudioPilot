import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import numpy as np
import time

# Initialize the dispatcher
dispatcher = Dispatcher()

# Function to handle RTA data for channel 19
def handleRTAData(_, *args):
    osc_blob = args[0]
    # The data is in little-endian 16-bit integers
    new_data = np.frombuffer(osc_blob, dtype='<i2').reshape(-1)
    new_data_float = new_data.astype(np.float32) / 256.0  # Convert to float and scale
    print(new_data_float)  # Print the received and processed RTA data

# Map the RTA data handler to the /meters/15 OSC address pattern
dispatcher.map("/meters/15", handleRTAData)

# Function to set RTA source to channel 19 and then request RTA data
async def setRTASourceAndRequestData(client):
    # Set the RTA source to channel 19 (value is 20)
    client.send_message("/prefs/rta/source", [20])
    await asyncio.sleep(0.5)  # Wait a bit to ensure the command is processed
    client.send_message("ch/19/meters/15", 1)  # Request RTA data

async def requestRTAData(x32_ip, port):
    client = SimpleUDPClient(x32_ip, port)  # Use the X32's IP address here
    await setRTASourceAndRequestData(client)

async def initServer(local_ip, port):
    server = AsyncIOOSCUDPServer((local_ip, port), dispatcher, asyncio.get_event_loop())
    return await server.create_serve_endpoint()

async def main(local_ip, x32_ip, port):
    transport = await initServer(local_ip, port)
    
    # Schedule the RTA source setting and data request as an asyncio task
    asyncio.create_task(requestRTAData(x32_ip, port))

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        transport.close()

if __name__ == "__main__":
    local_ip = "127.0.0.1"
    x32_ip = "192.168.56.1"
    port = 10023
    asyncio.run(main(local_ip, x32_ip, port))
