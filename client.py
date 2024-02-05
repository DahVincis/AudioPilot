from pythonosc import udp_client

X32_IP_ADDRESS = '192.168.1.100'  # Replace with the actual IP address of your X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

# Sending metering request for channel 18 (remember channels start at index 0, so channel 18 is index 17)
client.send_message("/meters/6", [17])  # arguments should be in a list

# Repeat for other channels
client.send_message("/meters/6", [18])  # Channel 19
client.send_message("/meters/6", [21])  # Channel 22