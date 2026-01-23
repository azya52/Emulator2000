import time
    
from PyQt6.QtCore import QIODeviceBase, QByteArray, QIODevice
from PyQt6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

SAMPLE_RATE = 44100
BUFFER_SIZE = 2048
SAMPLES_PART_SIZE = 2048
TONE_S = 1024 / 32768

class ToneGenerator(QIODevice):

    def __init__(self, format):
        super().__init__()

        channelCount = format.channelCount()

        try:
            with open("assets/tone.raw", "rb") as file:
                raw = QByteArray(file.read())
                out = QByteArray()
                out.reserve(len(raw) * channelCount)
                for i in range(0, len(raw) - 1, 2):
                    out.append(raw.mid(i, 2) * channelCount)
                self._toneRaw = out
                self.open(QIODeviceBase.OpenModeFlag.ReadOnly | QIODeviceBase.OpenModeFlag.Unbuffered)
        except FileNotFoundError as e:
            print(e.strerror, e.filename)

        self._pos = 0
        self._toneStarts = []
        self._bytesPerSample = format.bytesPerSample() * channelCount
        self._sampleRate = format.sampleRate()
        self._toneLength = round(self._sampleRate * TONE_S) * self._bytesPerSample
        
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

    def beep(self, goalTime):
        if (len(self._toneStarts) == 0):
            self._pos = int(self._sampleRate * goalTime) * self._bytesPerSample
        self._toneStarts.append(SAMPLES_PART_SIZE + int(self._sampleRate * goalTime) * self._bytesPerSample)

    def bytesAvailable(self):
        return SAMPLES_PART_SIZE * self._bytesPerSample

class TremoloGenerator(QIODevice):

    def __init__(self, format):
        super().__init__()
        
        channelCount = format.channelCount()

        try:
            with open("assets/tremolo.raw", "rb") as file:
                raw = QByteArray(file.read())
                out = QByteArray()
                out.reserve(len(raw) * channelCount)
                for i in range(0, len(raw) - 1, 2):
                    out.append(raw.mid(i, 2) * channelCount)
                self._toneRaw = out
                self.open(QIODeviceBase.OpenModeFlag.ReadOnly | QIODeviceBase.OpenModeFlag.Unbuffered)
        except FileNotFoundError as e:
            print(e.strerror, e.filename)
            
        self._pos = 0
        self._toneStarts = []
        self._toneEnds = []
        self._bytesPerSample = format.bytesPerSample() * channelCount
        self._sampleRate = format.sampleRate()
        self._toneLength = self._toneRaw.size()
        self._initTime = time.perf_counter()

    def readData(self, maxlen):
        data = QByteArray()

        while maxlen:
            if (len(self._toneStarts) > 0):
                if (self._pos < self._toneStarts[0]):
                    chunk = min(maxlen, self._toneStarts[0] - self._pos)
                    data.append(chunk, b'\0')
                elif (len(self._toneEnds) == 0):
                    toneRawPos = self._pos % self._toneLength
                    chunk = min(maxlen, self._toneLength - toneRawPos)
                    data.append(self._toneRaw.mid(toneRawPos, chunk))
                elif (self._pos < self._toneEnds[0]):
                    toneRawPos = self._pos % self._toneLength
                    chunk = min(maxlen, self._toneEnds[0] - self._pos, self._toneLength - toneRawPos)
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

    def start(self, goalTime):
        goalSample = (SAMPLES_PART_SIZE + round(self._sampleRate * goalTime)) * self._bytesPerSample
        if (len(self._toneStarts) > len(self._toneEnds)):
            self._toneEnds.append(goalSample)
        if (len(self._toneStarts) == 0):
            self._pos = round(self._sampleRate * goalTime) * self._bytesPerSample
        self._toneStarts.append(goalSample)
        
    def stop(self, goalTime):
        if (len(self._toneStarts) > len(self._toneEnds)):
            self._toneEnds.append(SAMPLES_PART_SIZE + round(self._sampleRate * goalTime) * self._bytesPerSample)
            self._initTime = time.perf_counter()
            
    
    def bytesAvailable(self):
        return SAMPLES_PART_SIZE * self._bytesPerSample

class Beeper():
    def __init__(self):
        device = QMediaDevices.defaultAudioOutput()

        audioFormat = device.preferredFormat()
        audioFormat.setSampleRate(SAMPLE_RATE)
        audioFormat.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        self._tremolo = QAudioSink(audioFormat)
        self._tremolo.setBufferSize(BUFFER_SIZE)
        self._tremoloGenerator = TremoloGenerator(audioFormat)
        self._tremolo.start(self._tremoloGenerator)
        
        self._tone = QAudioSink(audioFormat)
        self._tone.setBufferSize(BUFFER_SIZE)
        self._toneGenerator = ToneGenerator(audioFormat)
        self._tone.start(self._toneGenerator)   

    def stop(self):
        self._tone.stop()
        self._tremolo.stop()
        self._toneGenerator.close()
        self._tremoloGenerator.close()
        
    def beep(self, goalTime):
        self._toneGenerator.beep(goalTime)

    def startTremolo(self, goalTime):
        self._tremoloGenerator.start(goalTime)
        
    def stopTremolo(self, goalTime):
        self._tremoloGenerator.stop(goalTime)
