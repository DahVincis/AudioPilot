import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

csvPath = 'rta_db_values2.csv'  
updateData = pd.read_csv(csvPath)


updateData['Frequency'] = pd.to_numeric(updateData['Frequency Band'], errors='coerce')

resets = updateData['Frequency'] == 20
updateData['Update Index'] = resets.cumsum()

totalUpdates = updateData['Update Index'].max()

for updateNumber in range(1, totalUpdates + 1):
    currentUpdateData = updateData[updateData['Update Index'] == updateNumber]
    
    plt.figure(figsize=(20, 6))
    plt.plot(currentUpdateData['Frequency'], currentUpdateData['dB Value'], marker='o', linestyle='-')
    plt.xscale('log')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('dB Value')
    plt.title(f'Frequency Response Update {updateNumber}')
    plt.grid(True, which='both', ls='--', lw=0.5)
    
    if not currentUpdateData['Frequency'].empty:
        xticks = [int(x) for x in np.logspace(np.log10(min(currentUpdateData['Frequency'])), np.log10(max(currentUpdateData['Frequency'])), num=15)]
        plt.xticks(xticks, [str(x) for x in xticks])
    
    plt.ylim(-90, 0)
    plt.tight_layout()
    plt.show()
