from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient('192.168.10.104', 10023)  # Example IP and port

#client.send_message('/xinfo', None)
client.send_message('/ch/31/eq/4/g', 0.03)