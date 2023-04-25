from PyQt6 import QtCore
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time

from cpu import CPU
from display import Display
from memory import Memory
from disasembler import Disassembler
from beeper import Beeper

FPS = 60
EXAMINE_RATE = 30

MAIN_FREQ = 32768
CICLE_TIME_NS = 1000000000 / MAIN_FREQ
MCICLE_TIME_NS = CICLE_TIME_NS * 8

DISPLAY_UPDTE_NS = 1000000000 / FPS
EXAMINE_UPDTE_NS = 1000000000 / EXAMINE_RATE

class Watch(QObject):
    btnPressSignal = pyqtSignal(int)
    btnReleaseSignal = pyqtSignal(int)
    stepSignal = pyqtSignal()
    pauseSignal = pyqtSignal()
    runSignal = pyqtSignal()
    stopSignal = pyqtSignal()
    setSpeedSignal = pyqtSignal(float)
    receiveSignal = pyqtSignal(int)
    setBreakpointSignal = pyqtSignal(int, bool)
    examineSignal = pyqtSignal(dict, bool)
    uiDisplayUpdateSignal = pyqtSignal(list)
    setInternalMemSignal = pyqtSignal(str)
    setExternalMemSignal = pyqtSignal(str)
    setPortNameSignal = pyqtSignal(str)

    def __init__(self, internalMem, externalMem, portName):
        super().__init__()
        self._internalMem = internalMem
        self._externalMem = externalMem
        self._portName = portName

    @pyqtSlot()
    def run(self):
        self._beeper = Beeper()
        self._memory = Memory(self._internalMem, self._externalMem)
        self._display = Display()
        self._disassembler = Disassembler()
        self._CPU = CPU(self._memory, self._display, self._beeper, self._transmit)

        self._serial = QSerialPort(baudRate=2048)
        self._serial.readyRead.connect(self._serialReadyRead)
        if (self._portName != None and self._portName != ""):
            self._serial.setPortName(self._portName)
            if (not self._serial.open(QtCore.QIODeviceBase.OpenModeFlag.ReadWrite)):
                print(self._serial.errorString())

        self._breakpoints = {}
        self._debug = False

        self._mcycleTimeNs = MCICLE_TIME_NS

        self._mcyclesOnStop = 0

        self.btnPressSignal.connect(self._btnPressed)
        self.btnReleaseSignal.connect(self._btnReleased)
        self.setBreakpointSignal.connect(self._setBreakpoint)
        self.runSignal.connect(self._run)
        self.pauseSignal.connect(self._pause)
        self.stepSignal.connect(self._step)
        self.stopSignal.connect(self._stop)
        self.setInternalMemSignal.connect(self._setInternalMem)
        self.setExternalMemSignal.connect(self._setExternalMem)
        self.setPortNameSignal.connect(self._setPortName)
        self.stopSignal.connect(self._stop)
        self.setSpeedSignal.connect(self._setSpeed)
        self.receiveSignal.connect(self._receive)

        self._uiDisplayUpdate()
        self._uiExamineUpdate(force = True)

        self._clock()

    @pyqtSlot()
    def finish(self):
        self.btnPressSignal.disconnect()
        self.btnReleaseSignal.disconnect()
        self.setBreakpointSignal.disconnect()
        self.runSignal.disconnect()
        self.pauseSignal.disconnect()
        self.stepSignal.disconnect()
        self.stopSignal.disconnect()
        self.setInternalMemSignal.disconnect()
        self.setExternalMemSignal.disconnect()
        self.setPortNameSignal.disconnect()
        self.setSpeedSignal.disconnect()
        self.receiveSignal.disconnect()
        self._serial.close()
        self._beeper.stop()

    @pyqtSlot(dict)
    def editState(self, state):
        if ("PC" in state):
            self._CPU.setPC(state["PC"])
        if ("LA" in state):
            self._display.setLA(state["LA"])
        if ("SA" in state):
            self._memory.setSA(state["SA"])
        if ("CB" in state):
            self._CPU.setCB(state["CB"])
        if ("AB" in state):
            self._CPU.setAB(state["AB"])
        if ("CF" in state):
            self._CPU.setCF(state["CF"])
        if ("ZF" in state):
            self._CPU.setZF(state["ZF"])
        if ("SR" in state):
            for i, value in state["SR"].items():
                self._CPU.setSR(i, value)
        if ("GR" in state):
            for i, bank in state["GR"].items():
                for j, value in bank.items():
                    self._CPU.setGR(i, j, value)
        if ("DDRAM" in state):
            for i, value in state["DDRAM"].items():
                self._display.setDDRAM(i, value)
        if ("DARAM" in state):
            for i, value in state["DARAM"].items():
                self._display.setDARAM(i, value)
        if ("DCTRL" in state):
            for i, value in state["DCTRL"].items():
                self._display.setDCTRL(i, value)
        if ("MEMORY" in state):
            self._memory.writeWord(state["MEMORY"][0], state["MEMORY"][1])
        
        self._uiDisplayUpdate()
        self._uiExamineUpdate(force = True)

    def _clock(self):
        thread = self.thread().currentThread()
        lastTick = time.perf_counter_ns()
        lastExamine = lastTick
        lastDisplayUpdate = lastTick
        while not(thread.isInterruptionRequested() or self._debug):
            ns = time.perf_counter_ns()
            if (ns > lastTick):                
                lastTick += self._mcycleTimeNs
                self._CPU.clock()
                self._display.clock()

                if (self._CPU.PC() in self._breakpoints):
                    self.examineSignal.emit({"DEBUG": True}, False)
                    self._pause()

            if (ns > lastDisplayUpdate):
                lastDisplayUpdate += DISPLAY_UPDTE_NS
                self._uiDisplayUpdate()
            elif (ns > lastExamine):
                lastExamine += EXAMINE_UPDTE_NS
                self._uiExamineUpdate()
            
            QtCore.QCoreApplication.processEvents()
            
    @pyqtSlot()
    def _run(self):
        self._debug = False
        self._clock()

    @pyqtSlot()
    def _pause(self):
        self._debug = True
        self._uiDisplayUpdate()
        self._uiExamineUpdate(force = True)
        self._mcyclesOnStop = self._CPU.mcycles()

    @pyqtSlot()
    def _step(self):
        while (self._CPU.clock() > 1):
            self._display.clock()
        self._display.clock()
        self._uiDisplayUpdate()
        self._uiExamineUpdate(force = True)

    @pyqtSlot()
    def _stop(self):
        self._debug = True
        self._display = Display()
        self._CPU = CPU(self._memory, self._display, self._beeper, self._transmit)
        self._uiDisplayUpdate()
        self._uiExamineUpdate(force = True)

    def _transmit(self, data):
        if (self._serial.isOpen()):
            self._serial.write(data.to_bytes())
        self.examineSignal.emit({"ISPOUT": data}, False)

    @pyqtSlot()
    def _serialReadyRead(self):
        while self.sender().bytesAvailable():
            self._receive(self.sender().read(1)[0])

    @pyqtSlot(int)
    def _receive(self, data):
        self._CPU.ispReceive(data)
        self.examineSignal.emit({"ISPIN": (data & 0xFF)}, False)
            
    @pyqtSlot(int, bool)
    def _setBreakpoint(self, pc, add):
        if (add):
            self._breakpoints[pc] = True
        else:
            if (pc in self._breakpoints):
                del self._breakpoints[pc]

    @pyqtSlot(str)
    def _setInternalMem(self, path):
        self._memory.setInternal(path)

    @pyqtSlot(str)
    def _setExternalMem(self, path):
        self._memory.setExternal(path)
        self._CPU = CPU(self._memory, self._display, self._beeper, self._transmit)

    @pyqtSlot(str)
    def _setPortName(self, name):
        self._serial.close()
        self._portName = name
        if (self._portName != None and self._portName != ""):
            self._serial.setPortName(self._portName)
            if (not self._serial.open(QtCore.QIODeviceBase.OpenModeFlag.ReadWrite)):
                print(self._serial.errorString())

    def _uiDisplayUpdate(self):
        self.uiDisplayUpdateSignal.emit(self._display.getPixels()) 

    def _uiExamineUpdate(self, force = False):
        self.examineSignal.emit({
            **self._disassembler.disassemble(self._memory),
            **self._memory.examine(),
            **self._CPU.examine(),
            **self._display.examine(),
            **{"MC": self._CPU.mcycles() - self._mcyclesOnStop}
        }, force)

    @pyqtSlot(int)
    def _btnPressed(self, keyCode):
        self._CPU.btnPressed(keyCode)

    @pyqtSlot(int)
    def _btnReleased(self, keyCode):
        self._CPU.btnReleased(keyCode)

    @pyqtSlot(float)
    def _setSpeed(self, speed):
        self._mcycleTimeNs = MCICLE_TIME_NS * speed

    def debugRun(self):
        self.runSignal.emit()

    def debugStep(self):
        self.stepSignal.emit()

    def debugPause(self):
        self.pauseSignal.emit()

    def debugStop(self):
        self.stopSignal.emit()

    def debugSetBreakpoint(self, pc, checked):
        self.setBreakpointSignal.emit(pc, checked)

    def btnPressed(self, keyCode):
        self.btnPressSignal.emit(keyCode)

    def btnReleased(self, keyCode):
        self.btnReleaseSignal.emit(keyCode)

    def setInternalMem(self, path):
        self.setInternalMemSignal.emit(path)

    def setExternalMem(self, path):
        self.setExternalMemSignal.emit(path)

    def setSpeed(self, speed):
        self.setSpeedSignal.emit(speed)

    def receive(self, data):
        self.receiveSignal.emit(data)

    def setPortName(self, name):
        self.setPortNameSignal.emit(name)
