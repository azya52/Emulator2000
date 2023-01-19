import time
    
from PyQt6.QtCore import QIODeviceBase, QByteArray, QIODevice
from PyQt6.QtMultimedia import QAudioFormat, QAudioSink

class ToneGenerator(QIODevice):
    MAIN_FREQ = 32768
    INSTRUCTION_S = 8 / MAIN_FREQ
    TONE_S = 1024 / MAIN_FREQ
    SAMPLES_PART_SIZE = 1000
    DATA_PART_SIZE = SAMPLES_PART_SIZE * 2

    def __init__(self, format):
        super().__init__()

        try:
            with open("assets/tone.raw", "rb") as file:
                self._toneRaw = QByteArray(file.read())
                self.open(QIODeviceBase.OpenModeFlag.ReadOnly | QIODeviceBase.OpenModeFlag.Unbuffered)
        except FileNotFoundError as e:
            print(e.strerror, e.filename)

        self._pos = 0
        self._toneStarts = []
        self._bytesPerSample = format.bytesPerSample()
        self._sampleRate = format.sampleRate()
        self._toneLength = (int(self._sampleRate * self.TONE_S) + 1) * self._bytesPerSample
        self._initTime = time.perf_counter()
        
    def readData(self, maxlen):
        data = QByteArray()

        while maxlen:
            if (len(self._toneStarts) > 0):
                if (self._pos < self._toneStarts[0]):
                    chunk = min(maxlen, self._toneStarts[0] - self._pos)
                    data.append(chunk, b'\0')
                elif (self._pos < self._toneStarts[0] + self._toneLength):
                    toneRawPos = self._pos % self._toneRaw.size()
                    chunk = min(maxlen, self._toneStarts[0] + self._toneLength - self._pos, self._toneRaw.size() - toneRawPos)
                    data.append(self._toneRaw.mid(toneRawPos, chunk))
                else:
                    self._toneStarts.pop(0)
                    continue
            else:
                chunk = maxlen
                data.append(chunk, b'\0')

            self._pos += chunk
            maxlen -= chunk

        return data

    def beep(self):
        goalTime = time.perf_counter() - self._initTime + self.TONE_S
        goalTime -= goalTime % self.INSTRUCTION_S
        goalTime -= goalTime % self.TONE_S
        self._toneStarts.append(self.DATA_PART_SIZE + int(self._sampleRate * goalTime) * self._bytesPerSample)

    def bytesAvailable(self):
        return self.DATA_PART_SIZE

class TremoloGenerator(QIODevice):
    MAIN_FREQ = 32768
    INSTRUCTION_S = 8 / MAIN_FREQ
    SAMPLES_PART_SIZE = 1000
    DATA_PART_SIZE = SAMPLES_PART_SIZE * 2

    def __init__(self, format):
        super().__init__()

        try:
            with open("assets/tremolo.raw", "rb") as file:
                self._toneRaw = QByteArray(file.read())
                self.open(QIODeviceBase.OpenModeFlag.ReadOnly | QIODeviceBase.OpenModeFlag.Unbuffered)
        except FileNotFoundError as e:
            print(e.strerror, e.filename)
            
        self._pos = 0
        self._toneStarts = []
        self._toneEnds = []
        self._bytesPerSample = format.bytesPerSample()
        self._sampleRate = format.sampleRate()
        self._initTime = time.perf_counter()

    def readData(self, maxlen):
        data = QByteArray()

        while maxlen:
            if (len(self._toneStarts) > 0):
                if (self._pos < self._toneStarts[0]):
                    chunk = min(maxlen, self._toneStarts[0] - self._pos)
                    data.append(chunk, b'\0')
                elif (len(self._toneEnds) == 0):
                    toneRawPos = self._pos % self._toneRaw.size()
                    chunk = min(maxlen, self._toneRaw.size() - toneRawPos)
                    data.append(self._toneRaw.mid(toneRawPos, chunk))
                elif (self._pos < self._toneEnds[0]):
                    toneRawPos = self._pos % self._toneRaw.size()
                    chunk = min(maxlen, self._toneEnds[0] - self._pos, self._toneRaw.size() - toneRawPos)
                    data.append(self._toneRaw.mid(toneRawPos, chunk))
                else:
                    self._toneStarts.pop(0)
                    self._toneEnds.pop(0)
                    continue
            else:
                chunk = maxlen
                data.append(chunk, b'\0')

            self._pos += chunk
            maxlen -= chunk

        return data

    def start(self):
        if (len(self._toneStarts) == len(self._toneEnds)):
            goalTime = time.perf_counter() - self._initTime
            goalTime -= goalTime % self.INSTRUCTION_S
            self._toneStarts.append(self.DATA_PART_SIZE + int(self._sampleRate * goalTime) * self._bytesPerSample)
        
    def stop(self):
        if (len(self._toneStarts) > len(self._toneEnds)):
            goalTime = time.perf_counter() - self._initTime
            goalTime -= goalTime % self.INSTRUCTION_S
            self._toneEnds.append(self.DATA_PART_SIZE + int(self._sampleRate * goalTime) * self._bytesPerSample)
    
    def bytesAvailable(self):
        return self.DATA_PART_SIZE

class Beeper():
    def __init__(self):
        format = QAudioFormat()
        format.setSampleRate(44100)
        format.setChannelCount(1)
        format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        self._tremolo = QAudioSink(format)
        self._tremolo.setBufferSize(2048)
        self._tremoloGenerator = TremoloGenerator(format)
        self._tremolo.start(self._tremoloGenerator)
        
        self._tone = QAudioSink(format)
        self._tone.setBufferSize(2048)
        self._toneGenerator = ToneGenerator(format)
        self._tone.start(self._toneGenerator)   

    def stop(self):
        self._tone.stop()
        self._tremolo.stop()
        self._toneGenerator.close()
        self._tremoloGenerator.close()
        
    def beep(self):
        self._toneGenerator.beep()

    def startTremolo(self):
        self._tremoloGenerator.start()
        
    def stopTremolo(self):
        self._tremoloGenerator.stop()
