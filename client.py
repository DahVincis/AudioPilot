from pythonosc import udp_client

X32_IP_ADDRESS = '192.168.0.101'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)


