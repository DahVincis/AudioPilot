import csv
import matplotlib.pyplot as plt
import numpy as np

# Dictionary to store frequency band as key and list of dB values as value
frequency_dict = {}

# Open the CSV file and read its contents
with open('rta_db_values1.csv', mode='r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        frequency_band = row['Frequency Band']
        db_value = float(row['dB Value'])
        if frequency_band in frequency_dict:
            frequency_dict[frequency_band].append(db_value)
        else:
            frequency_dict[frequency_band] = [db_value]

# Extract the numeric part from the keys and convert to int
frequencies = [int(key.split()[1]) for key in frequency_dict.keys()]

# Find the maximum number of dB values for a frequency band
max_db_values_count = max(len(db_values) for db_values in frequency_dict.values())

# Plot the data
for update_number in range(1, max_db_values_count + 1):
    plt.figure(figsize=(15, 6))
    for frequency_band, db_values in frequency_dict.items():
        if len(db_values) >= update_number:
            plt.plot(frequencies, db_values[:update_number], marker='o', linestyle='-', label=frequency_band)
    plt.xscale('log')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('dB Value')
    plt.title(f'Frequency Response Update {update_number}')
    plt.grid(True, which='both', ls='--', lw=0.5)
    xticks = [int(x) for x in np.logspace(np.log10(min(frequencies)), np.log10(max(frequencies)), num=15)]
    plt.xticks(xticks, [str(x) for x in xticks])
    plt.ylim(-128, 0)
    plt.legend()
    plt.tight_layout()
    plt.show()
