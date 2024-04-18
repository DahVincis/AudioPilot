from server_v3 import dataRTA, frequencies

# Define band ranges
band_ranges = {
    'LowCut': [(0.2600, 120.5)],
    'Low': [(0.2650, 124.7),
            (0.2700, 129.1),
            (0.2750, 133.7),
            (0.2800, 138.4),
            (0.2850, 143.2),
            (0.2900, 148.3),
            (0.2950, 153.5),
            (0.3000, 158.9),
            (0.3050, 164.4),
            (0.3100, 170.2),
            (0.3150, 176.2),
            (0.3200, 182.4),
            (0.3250, 188.8),
            (0.3300, 195.4),
            (0.3350, 202.3),
            (0.3400, 209.4),
            (0.3450, 216.8),
            (0.3500, 224.4),
            (0.3550, 232.3),
            (0.3600, 240.5),
            (0.3650, 248.9),
            (0.3700, 257.6),
            (0.3750, 266.7),
            (0.3800, 276.1),
            (0.3850, 285.8),
            (0.3900, 295.8),
            (0.3950, 306.2)],
    'Low Mid': [(0.4000, 317.0),
                (0.4050, 328.1),
                (0.4100, 339.6),
                (0.4150, 351.6),
                (0.4200, 363.9),
                (0.4250, 376.7),
                (0.4300, 390.0),
                (0.4350, 403.7),
                (0.4400, 417.9),
                (0.4450, 432.5),
                (0.4500, 447.7),
                (0.4550, 463.5),
                (0.4600, 479.8),
                (0.4650, 496.6),
                (0.4700, 514.1),
                (0.4750, 532.1),
                (0.4800, 550.8),
                (0.4850, 570.2),
                (0.4900, 590.2),
                (0.4950, 611.0),
                (0.5000, 632.5),
                (0.5050, 654.7),
                (0.5100, 677.7),
                (0.5150, 701.5),
                (0.5200, 726.2),
                (0.5250, 751.7),
                (0.5300, 778.1),
                (0.5350, 805.4),
                (0.5400, 833.7),
                (0.5450, 863.0),
                (0.5500, 893.4),
                (0.5550, 924.8),
                (0.5600, 957.3),
                (0.5650, 990.9),
                (0.5700, 1002.0),
                (0.5750, 1006.0),
                (0.5800, 1009.0),
                (0.5850, 1013.0),
                (0.5900, 1017.0),
                (0.5950, 1021.0),
                (0.6000, 1026.0),
                (0.6050, 1030.0),
                (0.6100, 1035.0),
                (0.6150, 1039.0),
                (0.6200, 1044.0),
                (0.6250, 1049.0),
                (0.6300, 1055.0)],
    'High Mid': [(0.6350, 1600),
                 (0.6400, 1660),
                 (0.6450, 1720),
                 (0.6500, 1780),
                 (0.6550, 1840),
                 (0.6600, 1910),
                 (0.6650, 1970),
                 (0.6700, 2040),
                 (0.6750, 2110),
                 (0.6800, 2190),
                 (0.6850, 2270),
                 (0.6900, 2340),
                 (0.6950, 2430),
                 (0.7000, 2510),
                 (0.7050, 2600),
                 (0.7100, 2690),
                 (0.7150, 2790),
                 (0.7200, 2890),
                 (0.7250, 2990),
                 (0.7300, 3090),
                 (0.7350, 3200),
                 (0.7400, 3310),
                 (0.7450, 3430),
                 (0.7500, 3550),
                 (0.7550, 3680),
                 (0.7600, 3810),
                 (0.7650, 3940),
                 (0.7700, 4080),
                 (0.7750, 4220),
                 (0.7800, 4370),
                 (0.7850, 4520),
                 (0.7900, 4680),
                 (0.7950, 4850),
                 (0.8000, 5020)],
    'High': [(0.8050, 5200),
             (0.8100, 5380),
             (0.8150, 5570),
             (0.8200, 5760),
             (0.8250, 5970),
             (0.8300, 6180),
             (0.8350, 6390),
             (0.8400, 6620),
             (0.8450, 6850),
             (0.8500, 7090),
             (0.8550, 7340),
             (0.8600, 7600),
             (0.8650, 7870),
             (0.8700, 8140),
             (0.8750, 8430),
             (0.8800, 8730),
             (0.8850, 9030),
             (0.8900, 9350),
             (0.8950, 9680),
             (0.9000, 10020),
             (0.9050, 10370),
             (0.9100, 10740),
             (0.9150, 11110),
             (0.9200, 11500),
             (0.9250, 11890),
             (0.9300, 12330),
             (0.9350, 12760),
             (0.9400, 13210),
             (0.9450, 13670),
             (0.9500, 14150),
             (0.9550, 14650),
             (0.9600, 15170),
             (0.9650, 15700),
             (0.9700, 16250),
             (0.9750, 16820),
             (0.9800, 17410),
             (0.9850, 18030),
             (0.9900, 18660),
             (0.9950, 19320),
             (1.0000, 20000)]
}

def find_closest_frequency(target_frequency):
    """ Find the closest frequency in the hardcoded list to the target frequency. """
    return min(frequencies, key=lambda x: abs(x - target_frequency))

# Mapping each frequency in the band_ranges to the closest in the hardcoded frequencies
closest_frequencies = {}
for band, freq_list in band_ranges.items():
    closest_frequencies[band] = [(osc, find_closest_frequency(freq)) for osc, freq in freq_list]

# Function to find the highest dB frequency in a band
def find_highest_db_frequency(band):
    band_freqs = [freq for _, freq in closest_frequencies[band]]
    highest_db = -90
    highest_freq = None
    for freq in band_freqs:
        latest_db = dataRTA[freq][-1] if dataRTA[freq] else -90
        if latest_db > highest_db:
            highest_db = latest_db
            highest_freq = freq
    return highest_freq, highest_db

# Function to calculate gain
def calculate_gain(db_value):
    freq_flat = -45  # dB level to achieve flat response
    distance = db_value - freq_flat
    return distance / 10  # Simplified gain calculation

# Example of processing the 'Low' band
low_freq, low_db = find_highest_db_frequency('Low')
low_gain = calculate_gain(low_db)
print(f"Low Band Frequency: {low_freq} Hz, Gain: {low_gain} dB")

# You can replicate the above example for other bands as needed