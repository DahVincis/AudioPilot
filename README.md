## Overview

AudioPilot offers a sophisticated interface for managing Behringer digital audio mixers via network communications, harnessing the capabilities of the Open Sound Control (OSC) protocol. This Python application stands out for its automated discovery of mixers within a network, providing seamless integration and accessibility for sound engineers. A cornerstone of AudioPilot is its dynamic equalization system, which intelligently processes real-time audio data to automatically adjust equalizer settings, achieving optimal sound quality across different environments and performances. This is achieved through advanced analysis of the audio spectrum, with real-time adjustments to frequency bands based on predefined parameters and live audio input. Additionally, AudioPilot presents an intuitive visual representation of frequency responses, granting users immediate insight into the sonic characteristics of their audio, facilitating informed decision-making for live mixing scenarios. With these tools, AudioPilot empowers users to fine-tune their audio outputs, ensuring clarity and balance, and provides a high level of control over mixer parameters, streamlining the audio management process for both live and studio settings.

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