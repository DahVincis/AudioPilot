from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient('192.168.1.5', 10023)  # Example IP and port

client.send_message('/xinfo', None)
client.send_message('/ch/01/eq/2/q', [0.5])