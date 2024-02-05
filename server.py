from pythonosc import dispatcher, osc_server
import threading
import matplotlib.pyplot as plt

# Assuming these are global variables to store the levels
chLVL = {18: [], 19: [], 22: []}

def handle_audio_level(address, *args):
    print(f"Received {address}: {args}")
    # Assuming args[0] contains the channel ID and args[1] contains the level
    chID = int(args[0])
    if chID in chLVL:
        chLVL[chID].append(args[1])  # Append level to the respective channel list

disp = dispatcher.Dispatcher()
# Map the OSC path for receiving meter values. Adjust as per actual usage.
disp.map("/meters/6", handle_audio_level)

server = osc_server.ThreadingOSCUDPServer(('0.0.0.0', 10123), disp)
print(f"Serving on {server.server_address}")

# Consider plotting in a separate thread or process to not block the OSC server
def plot_levels():
    plt.ion()  # Interactive mode on
    while True:
        plt.clf()  # Clear current figure
        for ch_id, levels in chLVL.items():
            if levels:  # If there are levels to plot
                plt.plot(levels, label=f"Channel {ch_id}")
        plt.legend()
        plt.pause(1)  # Pause for a bit before the next update

threadPlot = threading.Thread(target=plot_levels)
threadPlot.start()

server.serve_forever()