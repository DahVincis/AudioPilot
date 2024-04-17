# Define band ranges
band_ranges = {
    'Low': (124.7, 306.2),
    'Low Mid': (317.0, 1550),
    'High Mid': (1600, 5020),
    'High': (5200, 20000)
}

# Function to find the highest dB frequency in a band
def find_highest_db_frequency(band_range):
    frequencies_in_range = [freq for freq in frequencies if band_range[0] <= freq <= band_range[1]]
    highest_db = -90  # start with a low dB value
    highest_freq = None
    for freq in frequencies_in_range:
        latest_db = dataRTA[freq][-1] if dataRTA[freq] else -90
        if latest_db > highest_db:
            highest_db = latest_db
            highest_freq = freq
    return highest_freq, highest_db

# Function to calculate gain
def calculate_gain(db_value):
    freq_flat = -45  # dB level to achieve flat response
    distance = db_value - freq_flat
    return (distance / 10)  # simplification of your gain calculation

# Example of processing the 'Low' band
low_freq, low_db = find_highest_db_frequency(band_ranges['Low'])
low_gain = calculate_gain(low_db)
print(f"Low Band Frequency: {low_freq}Hz, Gain: {low_gain}dB")

# This would need to be repeated for each band and then integrated into the OSC commands to adjust the mixer settings
