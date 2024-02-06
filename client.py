from pythonosc import udp_client

X32_IP_ADDRESS = '192.168.56.1'  # Actual IP address of your X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("/ch/1/mix/on", 0) 
client.send_message("/ch/2/mix/on", 1) 
client.send_message("/ch/3/mix/on", 0) 

client.send_message("/ch/1/mix/fader", [0.5])