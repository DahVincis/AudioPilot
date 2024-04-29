## Overview

AudioPilot is a Python-based software designed to interact with digital audio mixers on a network using the Open Sound Control (OSC) protocol. It provides a range of functionalities from discovering mixers on the network to processing real-time audio data (RTA), controlling mixer parameters, and visualizing frequency responses.

## Features

- **Mixer Discovery**: Automatically detects mixers within specified subnets.
- **Keep-Alive**: Sends periodic messages to keep the mixer awake.
- **Real-Time Audio Data Subscription and Renewal**: Manages RTA data subscriptions.
- **dB Value Processing**: Converts mixer data points to decibel values.
- **Dynamic EQ Control**: Adjusts EQ parameters based on RTA data and pre-set profiles for different vocal types.
- **Visualization**: Plots real-time frequency response histograms using PyQtGraph.

## Usage

1. Run `AudioPilot.py` to begin the mixer discovery process.
2. Select a discovered mixer to interact with.
3. Choose the vocal type that corresponds to your scenario.
4. Observe the real-time frequency response in the visualization window.

For advanced usage, refer to the detailed comments within the code.

## Requirements

- Python 3.x
- `python-osc`
- `pyqtgraph`
- `PyQt5`
- Networked digital audio mixer compatible with OSC protocol (X32 or M32 Consoles)

## Installation

To install AudioPilot, simply clone the repository and install the required Python packages.

```bash
git clone https://github.com/DahVincis/AudioPilot.git
cd audiopilot
pip install -r requirements.txt
```

## Authors

- Pedro H. Fernandes