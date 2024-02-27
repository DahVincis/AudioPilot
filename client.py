from pythonosc import udp_client
import time

X32_IP_ADDRESS = '192.168.56.1'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("/dca/7/on", [0])  # Turn on DCA 7
client.send_message("/ch/01/mix/fader", [0.5])  # Set channel 1 fader to 0.5
client.send_message("/meters/15", [])
client.send_message("/subscribe", ["/meters/15", 1])  # Subscribe to RTA data
client.send_message("/-action/", ["get", "/meters/15"])
client.send_message("/meters", ["/meters/6", 18])
client.send_message("/meters/6", [18])