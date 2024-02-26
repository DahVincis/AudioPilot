from pythonosc import udp_client
import time

X32_IP_ADDRESS = '192.168.56.1'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("xremote", ["on"])  # Turn on XRemote mode
time.sleep(0.1)  # Wait a bit to ensure the command is processed
client.send_message("/dca/7/on", [0])  # Turn on DCA 7
client.send_message("/ch/01/mix/fader", [0.5])  # Set channel 1 fader to 0.5