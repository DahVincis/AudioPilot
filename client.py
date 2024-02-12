from pythonosc import udp_client
import time

X32_IP_ADDRESS = '192.168.56.1'  # IP address of X32 mixer
X32_OSC_PORT = 10023

client = udp_client.SimpleUDPClient(X32_IP_ADDRESS, X32_OSC_PORT)

client.send_message("/ch/1/mix/on", 0) 
client.send_message("/ch/2/mix/on", 1) 
client.send_message("/ch/3/mix/on", 0) 

client.send_message("/ch/1/mix/fader", [0.5])

client.send_message("/dca/1/on", 1)
client.send_message("/dca/2/on", 1)
client.send_message("/dca/3/on", 1)
client.send_message("/dca/4/on", 1)
client.send_message("/dca/5/on", 1)
client.send_message("/dca/6/on", 1)

while True:
    client.send_message("/xremote", [])
    time.sleep(7)