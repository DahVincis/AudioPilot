from pythonosc import udp_client
import time

X32_IP_ADDRESS = '26.11.225.132'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("/xremote", None)  # Send XRemote to keep connection alive
client.send_message("/renew", ["/meters/15"]) # Renew RTA data
client.send_message("/meters", ["/meters/6", [16]])  # Turn on DCA 7
