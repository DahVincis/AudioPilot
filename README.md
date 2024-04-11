# Behringer Mixer OSC Interface

This project provides a Python interface to interact with Behringer digital mixers over OSC (Open Sound Control) protocol. It includes functionality to keep the mixer awake via periodic "keep-alive" messages, subscribe to and renew real-time analyzer (RTA) data, convert fader positions to decibel (dB) values, and process RTA data into dB values for frequency bands. This tool is designed for sound engineers, developers, and hobbyists looking to extend control and receive data from Behringer mixers programmatically.

## Features

- **Keep Mixer Awake:** Sends periodic keep-alive messages (`/xremote` and `/xinfo`) to prevent the mixer from going into a sleep state.
- **Subscribe to RTA Data:** Automatically subscribes to RTA (Real-Time Analyzer) data from the mixer (`/meters/15`) and renews the subscription as needed to avoid timeouts.
- **Fader Position to dB Conversion:** Converts fader positions to decibel (dB) values using a polynomial fitting based on predefined data points, allowing for accurate volume level representation.
- **RTA Data Processing:** Processes RTA data received in blobs, converting the raw data into readable dB values for each frequency band, providing valuable insights into the audio spectrum being analyzed.
- **Custom OSC Message Handling:** Includes a framework for processing and handling custom OSC messages from the mixer, with default and specific handlers for various data types.

## Requirements

- Python 3.6 or later
- [python-osc](https://pypi.org/project/python-osc/)
- [NumPy](https://numpy.org/)

You can install the necessary Python packages using pip:

```bash
pip install python-osc numpy
```

## Usage

### Configuration

Before running the script, ensure the IP address of your Behringer mixer is correctly set in the script:

```python
X32IP = '192.168.10.104'  # Change this to the IP address of your Behringer mixer
```

### Running the Script

To start the interface, run the script from the command line with optional arguments for IP and port if you want to listen to incoming OSC messages from other devices or applications:

```bash
python your_script_name.py --ip 0.0.0.0 --port 10024
```

- `--ip` specifies the IP address to listen on. Default is `0.0.0.0`.
- `--port` specifies the port to listen on. Default is `10024`.

### Understanding the Code

- **Keep Behringer Awake:** The `keepMixerAwake` function sends periodic messages to the mixer to keep it awake, using separate threads to avoid blocking the main execution.
- **Subscribe and Renew RTA:** The `subRenewRTA` function manages the subscription to RTA data and its renewal, ensuring continuous data flow.
- **Process RTA Data:** RTA data received from the mixer is processed by the `handlerRTA` function, which unpacks the data and converts it into dB values for each frequency band. This is particularly useful for sound analysis and optimization.
- **Fader Handler:** The `handlerFader` function demonstrates how to handle fader position messages and convert them to dB values using a polynomial derived from predefined data points, allowing for precise volume adjustments.
- **Default Handler:** All other OSC messages are handled by the `handlerDefault`, which logs the messages for debugging purposes.

## Advanced Configuration

You can customize the frequency list or gain value in the script to tailor the functionality to specific mixers or use cases. Adjusting these values can enhance the accuracy of dB conversions for RTA data and fader positions.

## Contributing

Contributions to improve the project are welcome. Please feel free to fork the repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.
