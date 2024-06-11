import struct

from Data import frequencies, dataRTA, gainOffset, queueRTA

receivedFirstRTA = False

# Class definitions
class RTASubscriber:
    def __init__(self, client):
        self.client = client

    def subRenewRTA(self):
        import time
        while True:
            self.client.send_message("/batchsubscribe", ["/meters", "/meters/15", 0, 0, 99])
            time.sleep(0.1)

    def handlerRTA(self, address, *args):
        global receivedFirstRTA
        if not args:
            print(f"No RTA data received on {address}")
            return

        blobRTA = args[0]
        dataPoints = len(blobRTA) // 4

        try:
            ints = struct.unpack(f'<{dataPoints}I', blobRTA)
            dbValues = []
            for intValue in ints:
                shortINT1 = intValue & 0xFFFF
                shortINT2 = (intValue >> 16) & 0xFFFF
                if shortINT1 >= 0x8000: shortINT1 -= 0x10000
                if shortINT2 >= 0x8000: shortINT2 -= 0x10000
                dbValue1 = (shortINT1 / 256.0) + gainOffset
                dbValue2 = (shortINT2 / 256.0) + gainOffset
                dbValues.append(dbValue1)
                dbValues.append(dbValue2)

            for i, dbValue in enumerate(dbValues[2:len(frequencies) + 2]):
                freqLabel = frequencies[i] if i < len(frequencies) else "Unknown"
                if freqLabel in dataRTA:
                    dataRTA[freqLabel].append(dbValue)
                    if len(dataRTA[freqLabel]) > 10:
                        dataRTA[freqLabel].pop(0)
                else:
                    dataRTA[freqLabel] = [dbValue]

            if not receivedFirstRTA:
                receivedFirstRTA = True

            queueRTA.put(dataRTA)
        except Exception as e:
            print(f"Error processing RTA data: {e}")

class FaderHandler:
    def handlerFader(self, address, *args):
        if args and isinstance(args[0], float):
            f = args[0]
            if f > 0.75:
                d = f * 40.0 - 30.0
            elif f > 0.5:
                d = f * 80.0 - 50.0
            elif f > 0.25:
                d = f * 160.0 - 70.0
            elif f >= 0.0:
                d = f * 480.0 - 90.0
            else:
                print(f"Invalid fader value: {f}")
                return
            print(f"[{address}] ~ Fader value: {d:.2f} dB")
        else:
            print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

    def floatToDB(self, trimFloat):
        floatMin = 0.0
        floatMax = 0.25
        dbMin = -18.0
        dbMax = 18.0
        if 0 <= trimFloat <= 0.25:
            dbValue = (trimFloat - floatMin) * (dbMax - dbMin) / (floatMax - floatMin) + dbMin
        else:
            dbValue = "Out of range"
        return dbValue

    def handlerPreampTrim(self, address, *args):
        if args and isinstance(args[0], float):
            trimFloat = args[0]
            dbValue = self.floatToDB(trimFloat)
            if isinstance(dbValue, str):
                print(f"[{address}] ~ Preamp trim value: {dbValue}")
            else:
                print(f"[{address}] ~ Preamp trim value: {dbValue:.2f} dB")
        else:
            print(f"[{address}] ~ Incorrect argument format or length. ARGS: {args}")

    def handlerXInfo(self, data):
        try:
            addressEnd = data.find(b'\x00')
            data = data[(addressEnd + 4) & ~3:]
            startTypeTag = data.find(b',') + 1
            endTypeTag = data.find(b'\x00', startTypeTag)
            typeTag = data[startTypeTag:endTypeTag].decode()
            data = data[(endTypeTag + 4) & ~3:]
            arguments = []
            for tag in typeTag:
                if tag == 's':
                    endString = data.find(b'\x00')
                    argument = data[:endString].decode()
                    arguments.append(argument)
                    data = data[(endString + 4) & ~3:]
            return " | ".join(arguments)
        except Exception as e:
            print(f"Error parsing data: {e}")
            return "Error parsing data"

    def handlerDefault(self, address, *args):
        print(f"Received fader message on {address}. Args: {args}")
