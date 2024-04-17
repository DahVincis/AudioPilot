# EQ Automation Algorithm

This document outlines the details for an automation algorithm designed to manage EQ settings based on dynamic analysis of frequency and dB levels.

## Minimum and Maximum Q Values
- Minimum Q value: 3.0
- Maximum Q value: 1.0
- Usage: `/ch/[01...32]/eq/[1...4]/q  logf  [10.000, 0.3, 72]`

## Band Type
- Type: Bell/PEQ (PEQ represented as `2`)
- Usage: `/ch/[01...32]/eq/[1...4]/type  enum  int [2]`

## Frequency Management
Each EQ band will select frequencies based on the highest dB value within the band to determine the frequency position.

### Lowcut Frequency Parameters
- Range: 20hz - 120.5hz
- Usage: `/ch/[01...32]/eq/[1...4]/f  logf  [20.000, 20000, 201]` (120.5hz = 0.2600)
- Type: Lowcut `/ch/[01...32]/eq/[1...4]/type  enum  int [0]`

### Frequency Bands
- Low Band: 124.7 - 306.2 Hz
- Low Mid Band: 317.0 - 1k55 Hz
- High Mid Band: 1k60 - 5k02 Hz
- High Band: 5k20 - 20k00 Hz

## Gain Level Management
The gain for each band is set based on the distance from the frequency's dB level to a "frequency flat" level (-45 dB). This is adjusted based on the voice pitch type (Low, High, Mid).

### Final Formula for Gain
- `((dbFreqValue - freqFlat) / 10) * bandMultiplier`

### Voice Pitch Settings
- **Low Pitch (Men)**:
  - Low Band: decrease -4dB to -12dB
  - LowMid Band: decrease -2dB to -10dB
  - MidHigh Band: increase 0dB to 6.5dB
  - High Band: increase 0dB to 6dB

- **High Pitch (Women)**:
  - Low Band: decrease 0dB to -6.5dB
  - LowMid Band: decrease -1dB to -7dB
  - MidHigh Band: decrease -2dB to -8dB
  - High Band: decrease -3dB to -6.5dB 

- **Mid Pitch (Flat)**:
  - Low Band: decrease 0dB to -7dB
  - LowMid Band: decrease 0dB to -6dB
  - MidHigh Band: increase 0dB to 4dB
  - High Band: decrease 0dB to -4dB

## Q Value Calculation
The Q value is adjusted based on the number of frequencies close to the selected frequency within each band.

### Final Formula for Q Value
- `len(freqSize) * ((qMax - qMin) // len(bandSize))`

This formula adjusts the Q value based on the concentration of similar dB values around the selected frequency, influencing the precision of the EQ curve.
