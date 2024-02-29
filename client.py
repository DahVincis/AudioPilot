from pythonosc import udp_client
import time

X32_IP_ADDRESS = '192.168.0.100'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("/dca/7/on", [0])  # Turn on DCA 7
