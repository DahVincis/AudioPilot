import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
import numpy as np
import matplotlib.pyplot as plt
from threading import Thread, Lock
import time

# Initialize the dispatcher
dispatcher = Dispatcher()

# Prepare data storage
frequencies = np.logspace(np.log10(20), np.log10(20000), num=100)
rta_data = np.zeros_like(frequencies)
data_lock = Lock()  # Lock for thread-safe operations on rta_data

# Plotting function to be run in a separate thread
def plot_rta():
    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.semilogx(frequencies, rta_data, 'b-', label='Channel 19 RTA')
    ax.set_ylim(-15, 15)
    ax.set_xlim(20, 20000)
    ax.set_yticks(np.arange(-15, 20, step=5))
    frequency_ticks = [20, 40, 60, 80, 100, 200, 300, 400, 600, 800, 1e3, 2e3, 3e3, 4e3, 5e3, 6e3, 8e3, 10e3, 20e3]
    ax.set_xticks(frequency_ticks)
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x/1000)}k' if x >= 1000 else int(x)))
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Gain (dB)')
    ax.set_title('RTA Visualization for Channel 19')
    ax.grid(True, which="both", ls="--")
    ax.legend()

    while True:
        with data_lock:  # Ensure thread-safe access to rta_data
            line.set_ydata(rta_data)
        ax.relim()
        ax.autoscale_view(True, True, True)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.1)  # Adjust this for the desired refresh rate

# Function to handle RTA data for channel 19
def handle_rta_data(address: str, *args):
    global rta_data
    osc_blob = args[0]
    new_data = np.frombuffer(osc_blob, dtype='<f4')
    with data_lock:  # Ensure thread-safe update of rta_data
        np.copyto(rta_data, new_data)  # Safe update

# Map the RTA data handler to the /meters/15 OSC address pattern
dispatcher.map("/meters/15", handle_rta_data)

ip = "127.0.0.1"
port = 10023

async def init_server():
    server = AsyncIOOSCUDPServer((ip, port), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()
    return transport, server

async def main():
    plotting_thread = Thread(target=plot_rta, daemon=True)
    plotting_thread.start()

    transport, server = await init_server()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        transport.close()

asyncio.run(main())
