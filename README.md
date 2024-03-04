
# Behringer Mixer OSC Interface

This project provides a Python interface to interact with Behringer digital mixers over OSC (Open Sound Control) protocol. It includes functionality to keep the mixer awake via periodic "keep-alive" messages, subscribe to and renew real-time analyzer (RTA) data, and convert fader positions to decibel (dB) values. This tool is designed for sound engineers, developers, and hobbyists looking to extend control and receive data from Behringer mixers programmatically.

## Features

- **Keep Mixer Awake:** Sends periodic keep-alive messages to prevent the mixer from going into a sleep state.
- **Subscribe to RTA Data:** Automatically subscribes to RTA (Real-Time Analyzer) data from the mixer and renews the subscription as needed.
- **Fader Position to dB Conversion:** Converts fader positions to decibel (dB) values using a polynomial fitting based on predefined data points.
- **Custom OSC Message Handling:** Includes a framework for processing and handling custom OSC messages from the mixer.

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
X32_IP = '192.168.56.1'  # Change this to the IP address of your Behringer mixer
```

### Running the Script

To start the interface, run the script from the command line with optional arguments for IP and port if you want to listen to incoming OSC messages from other devices or applications:

```bash
python your_script_name.py --ip 0.0.0.0 --port 10024
```

- `--ip` specifies the IP address to listen on. Default is `0.0.0.0`.
- `--port` specifies the port to listen on. Default is `10024`.

### Understanding the Code

- **Keep Behringer Awake:** The `keep_behringer_awake` function sends periodic messages to the mixer to keep it awake.
- **Subscribe and Renew RTA:** The `subscribe_and_renew_rta` function handles the subscription to RTA data and its renewal.
- **Process RTA Data:** RTA data received from the mixer is processed by the `process_rta_data` function, which unpacks the data and converts it to dB values.
- **Fader Handler:** The `print_fader_handler` function demonstrates how to handle fader position messages and convert them to dB values using a polynomial derived from predefined data points.
- **Default Handler:** All other OSC messages are handled by the `default_handler`, which logs the messages for debugging purposes.

## Contributing

Contributions to improve the project are welcome. Please feel free to fork the repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

This project is not affiliated with Behringer or Music Tribe. Behringer is a trademark of MUSIC Group IP Ltd.
