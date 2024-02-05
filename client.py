from pythonosc import udp_client

X32_IP_ADDRESS = '192.168.1.100'  # Actual IP address of your X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

# Sending metering request for specific channels
client.send_message("/meters/6", [17])  # Channel 18
client.send_message("/meters/6", [18])  # Channel 19
client.send_message("/meters/6", [21])  # Channel 22
