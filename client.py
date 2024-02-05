from pythonosc import udp_client

X32_IP_ADDRESS = 'X32_IP_ADDRESS'  # Actual IP address of the X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

# Example OSC messages to configure the X32 for streaming
client.send_message("/ch/01/mix/on", 1)