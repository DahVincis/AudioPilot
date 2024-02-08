
# AudioPilot

AudioPilot is a comprehensive solution designed for remote control and visualization of audio mixing processes. Leveraging the power of the Open Sound Control (OSC) protocol, AudioPilot facilitates real-time audio manipulation and monitoring through a network-connected digital mixing console, specifically tailored for the X32 mixer. This project is split into two main components: `client.py` and `server.py`.

## Features

- **Remote Control**: Send commands to control channel and DCA (Digitally Controlled Amplifier) levels on the X32 mixer.
- **Real-Time Audio Analysis (RTA)**: Visualize the frequency spectrum of the audio being processed by the mixer in real-time.

## Requirements

- Python 3.6 or higher
- `python-osc` library for OSC communication
- `numpy` and `matplotlib` for data manipulation and visualization

## Installation

First, ensure that Python 3 is installed on your system. Then, install the required Python packages using pip:

```bash
pip install python-osc numpy matplotlib
```

## Usage

### Client

The `client.py` script is used to send control messages to the X32 mixer. Before running the script, make sure to update the `X32_IP_ADDRESS` variable with the IP address of your X32 mixer.

```bash
python client.py
```

### Server

The `server.py` script starts an OSC server that listens for incoming RTA data from the mixer and visualizes it in real-time. Simply run the script to start the server:

```bash
python server.py
```

## Configuration

- **Client (`client.py`)**: Configure the IP address and port of your X32 mixer at the beginning of the script.
- **Server (`server.py`)**: Adjust the `ip` and `port` variables to match your network settings if the default settings do not work for your setup.

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, feel free to fork the repository and submit a pull request.
