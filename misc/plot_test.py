import pandas as pd
import matplotlib.pyplot as plt

frequencies = [
    20, 21, 22, 24, 26, 28, 30, 32, 34, 36,
    39, 42, 45, 48, 52, 55, 59, 63, 68, 73,
    78, 84, 90, 96, 103, 110, 118, 127, 136, 146,
    156, 167, 179, 192, 206, 221, 237, 254, 272, 292,
    313, 335, 359, 385, 412, 442, 474, 508, 544, 583,
    625, 670, 718, 769, 825, 884, 947, 1.02, 1.09, 1.17,
    1.25, 1.34, 1.44, 1.54, 1.65, 1.77, 1.89, 2.03, 2.18, 2.33,
    2.50, 2.68, 2.87, 3.08, 3.30, 3.54, 3.79, 4.06, 4.35, 4.67,
    5.00, 5.36, 5.74, 6.16, 6.60, 7.07, 7.58, 8.12, 8.71, 9.33,
    10.00, 10.72, 11.49, 12.31, 13.20, 14.14, 15.16, 16.25, 17.41, 18.66
]

df = pd.read_csv('rta_db1.csv')

df['dB Value'] = df['dB Value'].astype(float).clip(0.0, -130.0)

plt.figure(figsize=(20, 6))

bars = plt.bar(df['Frequency Band'], df['dB Value'])
plt.ylim(0.0, -130.0) 

plt.xlabel('Frequency Band')
plt.ylabel('dB Value')
plt.title('dB Values by Frequency Band')

plt.xticks(rotation=90)

plt.tight_layout()
plt.show()
