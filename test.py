import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import numpy as np

# Initialize the dispatcher
dispatcher = Dispatcher()

# Function to print received RTA data
def handleRTAData(_, *args):
    osc_blob = args[0]  # Assuming the first argument is the blob data
    # Assuming the blob data format is known and matches the expected RTA data format
    data = np.frombuffer(osc_blob, dtype='<i2')
    db_levels = data.astype(np.float32) / 256.0
    print("Received RTA dB levels:", db_levels)

# Setup dispatcher to handle RTA data
dispatcher.map("/meters/15", handleRTAData)

async def keep_xremote_active(client):
    while True:
        client.send_message("/xremote", [])
        await asyncio.sleep(9)  # Send every 9 seconds to keep the connection alive

async def main(ip, port):
    client = SimpleUDPClient(ip, port)
    server = AsyncIOOSCUDPServer(("0.0.0.0", 10024), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Start the OSC server

    # Start the background task to keep XRemote active
    asyncio.create_task(keep_xremote_active(client))

    print("OSC Server is running. Waiting for RTA data...")

    try:
        while True:
            await asyncio.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        transport.close()
        print("Script stopped by user.")

if __name__ == "__main__":
    ip = "192.168.0.100"  # X32 mixer IP address
    port = 10023  # OSC port used by the X32 mixer
    asyncio.run(main(ip, port))
