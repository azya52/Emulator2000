b3 = 0x8
b2 = 0x4
b1 = 0x2
b0 = 0x1

STACK_SIZE = 3

SM_DISABLE = 0
SM_ENABLE = 1
SM_STOP = 2
SM_RUN = 3

IM_REGISTERS = 0
IM_DMA = 1

from memory import Memory
from display import Display
from beeper import Beeper

class CPU():
    def __init__(self, memory: Memory, display: Display, beeper: Beeper, transmit):
        self._display = display
        self._memory = memory
        self._beeper = beeper
        self._transmit = transmit
        
        self._GR = [[0] * 32 for i in range(4)]
        self._SR = [0] * 16

        self._STACK = []

        self._PC = 0
        self._CB = 0
        self._AB = 0
        self._CF = 0
        self._ZF = 0
        self._bSA = 0

        self._counter0 = 0
        self._counter1 = 0

        self._stopwatchMode = SM_DISABLE

        self._ispCpunter = 0
        self._ispMode = IM_REGISTERS
        self._ispTransmitEnable = False
        self._ispReceiveEnable = False
        self._ispTransmit = False
        self._ispTransmitBuffer = 0

        self._executionCounter = 0
        self._mcyclesCounter = 0

        self._execute = (
			CPU._add,
			CPU._adb,
			CPU._sub,
			CPU._sbb,
			CPU._adi,
			CPU._adbi,
			CPU._sbi,
			CPU._sbbi,
			CPU._adm,
			CPU._adbm,
			CPU._sbm,
			CPU._sbbm,
			CPU._cmp,
			CPU._cpm,
			CPU._cpi,
			CPU._op0x3C, #LCRB, LARB
			CPU._andi,
			CPU._ori,
			CPU._xori,
			CPU._op0x4C, #INC, INCB, DEC, DECB
			CPU._op0x50, #RSHM, LSHM
			CPU._in,
			CPU._out,
			CPU._outi,
			CPU._op0x60, #PSAM, PLAM
			CPU._op0x64, #LDSM, STSM
			CPU._stlm,
			CPU._stl,
			CPU._psai,
			CPU._psai,
			CPU._plai,
			CPU._op0x7C, #STLS, #STLSA, #STLI, #STLIA,
			CPU._mov,
			CPU._movm,
			CPU._ldi,
			CPU._clrm,
			CPU._mvac,
			CPU._mvacm,
			CPU._mvca,
			CPU._mvcam,
			CPU._call,
			CPU._call,
			CPU._call,
			CPU._call,
			CPU._ret,
			CPU._cpfjr,
			CPU._ijmr,
			CPU._wfe,
			CPU._jmp,
			CPU._jmp,
			CPU._jmp,
			CPU._jmp,
			CPU._jz,
			CPU._jnz,
			CPU._jc,
			CPU._jnc,
			CPU._btjr,
			CPU._btjr,
			CPU._btjr,
			CPU._btjr,
			CPU._cpjr,
			CPU._cpjr,
			CPU._cpjr,
			CPU._cpjr,
        )

        self._execute0x3C = (CPU._lcrb, CPU._larb)
        self._execute0x7C = (CPU._stls, CPU._stlsa, CPU._stli, CPU._stlia)
        self._execute0x4C = (CPU._inc, CPU._incb, CPU._dec, CPU._decb)
        self._execute0x50 = (CPU._rshm, CPU._lshm)
        self._execute0x60 = (CPU._psam, CPU._plam)
        self._execute0x64 = (CPU._stsm, CPU._ldsm)

        self._srWrite = (
            CPU._sr0Write,
            CPU._sr1Write,
            CPU._sr2Write,
            CPU._sr3Write,
            CPU._sr4Write,
            CPU._sr5Write,
            CPU._sr6Write,
            CPU._sr7Write,
            CPU._sr8Write,
            CPU._sr9Write,
            CPU._sr10Write,
            CPU._sr11Write,
            CPU._sr12Write,
            CPU._sr13Write,
            CPU._sr14Write,
            CPU._sr15Write,
        )

    def examine(self):
        return {
            "PC": self._PC,
            "CB": self._CB,
            "AB": self._AB,
            "CF": self._CF,
            "ZF": self._ZF,
            "SR": {i : value for i, value in enumerate(self._SR)},
            "GR": {i : {j : value for j, value in enumerate(self._GR[i])} for i in range(4)},
        }

    def setSR(self, index, value):
        self._srWrite[index](self, value & 0xF)

    def setGR(self, bank, index, value):
        self._GR[bank][index] = value & 0xF

    def setPC(self, value):
        self._PC = value & 0xFFF

    def setCB(self, value):
        self._CB = value & 0x3

    def setAB(self, value):
        self._AB = value & 0x3

    def setCF(self, value):
        self._CF = value & 0x1

    def setZF(self, value):
        self._ZF = value & 0x1

    def btnPressed(self, keyCode):
        self._SR[7] |= 0x1 << keyCode
        self._SR[8] |= 0x1 << keyCode
        self._SR[0] |= b2
        if (self._stopwatchMode): self._timer1StopwatchProcess(keyCode)

    def btnReleased(self, keyCode):
        self._SR[8] &= ~(0x1 << keyCode)

    def ispReceive(self, data):
            if(self._ispReceiveEnable):
                self._SR[5] = (data >> 4) & 0x0F
                self._SR[6] = data & 0x0F
                if (self._ispMode == IM_DMA):
                    if (not self._ispTransmitEnable):
                        self._memory.writeExternal(data)
                        if (self._memory.SA() & 0xFF == 0):
                            self._SR[1] |= b1
                            self._SR[0] |= b3
                else:
                    self._SR[1] |= b0
                    self._SR[1] |= b2 if (self._ispTransmitEnable) else b0
                    self._SR[0] |= b3

    def _isp(self):
        self._ispCpunter += 1
        if (self._ispCpunter % 24 == 0):
            if (self._ispTransmit and self._ispTransmitEnable):
                if (self._ispMode == IM_DMA):
                    self._ispTransmitBuffer = self._memory.readExternal()
                    if (self._memory.SA() & 0xFF == 0):
                        self._SR[1] |= b3
                        self._SR[0] |= b3
                        self._ispTransmit = False
                else:
                    self._SR[1] |= b2
                    self._SR[0] |= b3
                    self._ispTransmit = False
                if (self._transmit != None):
                    self._transmit(self._ispTransmitBuffer)
                if (self._ispReceiveEnable):
                    self._SR[5] = (self._ispTransmitBuffer >> 4) & 0x0F
                    self._SR[6] = self._ispTransmitBuffer & 0x0F

    def PC(self):
        return self._PC
    
    def mcycles(self):
        return self._mcyclesCounter

    def _timer0(self):
        self._counter0 += 1
        if (self._counter0 % 128 == 0):
            if (self._SR[13] & b3 == 0):
                self._SR[12] |= b3
        if (self._counter0 % 256 == 0):
            if (self._SR[13] & b2 == 0):
                self._SR[12] |= b2
            self._SR[14] += 1
            if self._SR[14] > 15:
                self._SR[14] = 0
                if (self._SR[13] & b0 == 0):
                    self._SR[12] |= b0
                    self._SR[4] = (self._SR[4] + 1) & 0x3
        if (self._counter0 % 1024 == 0):
            if (self._SR[13] & b1 == 0):
                self._SR[12] |= b1
        if (self._SR[12]):
            self._SR[0] |= b0

    def _timer1(self):
        if (self._SR[9] & b3):
            self._counter1 += self._counter1
            if (self._counter1 % 38 == 0):
                self._SR[10] += 1
                if self._SR[10] > 9:
                    self._SR[10] = 0
                    self._SR[9] |= b2
                    self._SR[3] = (self._SR[3] + 1) & 0x3
    
    def _timer1StopwatchProcess(self, keyCode):
        if (keyCode == 0):
            if (self._stopwatchMode == SM_RUN):
                self._SR[9] |= b1    #set stopwatch split flag
                self._SR[11] = self._SR[10]   #store split value
            elif (self._stopwatchMode == SM_STOP):
                self._SR[9] |= b0    #set stopwatch clear flag
                self._SR[10] = 0     #clear stopwatch
                self._counter1 = 0
        if (keyCode == 1):
            if (self._stopwatchMode == SM_RUN):
                self._stopwatchMode = SM_STOP
                self._SR[9] &= ~b3
            else:
                self._stopwatchMode = SM_RUN
                self._SR[9] |= b3
            
    def clock(self):
        self._timer0()
        self._timer1()
        self._isp()
        
        self._executionCounter -= 1
        if (self._executionCounter <= 0):
            opcode = self._memory.getOpcode(self._PC)
            self._executionCounter = self._execute[opcode >> 10](self, opcode)
            self._mcyclesCounter += self._executionCounter
            self._PC = self._PC & 0xFFF
    
        return self._executionCounter
    
    def _op0x3C(self, opcode):
        adOp = (opcode >> 9) & 0x01
        return self._execute0x3C[adOp](self, opcode)

    def _op0x7C(self, opcode):
        adOp = (opcode >> 3) & 0x03
        return self._execute0x7C[adOp](self, opcode)

    def _op0x4C(self, opcode):
        adOp = (opcode >> 3) & 0x03
        return self._execute0x4C[adOp](self, opcode)

    def _op0x50(self, opcode):
        adOp = (opcode >> 3) & 0x01
        return self._execute0x50[adOp](self, opcode)

    def _op0x60(self, opcode):
        adOp = (opcode >> 4) & 0x01
        return self._execute0x60[adOp](self, opcode)

    def _op0x64(self, opcode):
        adOp = (opcode >> 3) & 0x01
        return self._execute0x64[adOp](self, opcode)
        
    def _add(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] += self._GR[self._CB][grS]

        self._CF = 1 if self._GR[self._CB][grD] > 15 else 0
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _adb(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] += self._GR[self._CB][grS]

        self._CF = 1 if self._GR[self._CB][grD] > 9 else 0
        if (self._CF): self._GR[self._CB][grD] -= 10
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _sub(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] -= self._GR[self._CB][grS]

        self._ZF = 0 if (self._GR[self._CB][grD]) else 1
        self._CF = 1 if (self._GR[self._CB][grD] < 0) else 0
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _sbb(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] -= self._GR[self._CB][grS]

        self._ZF = 0 if (self._GR[self._CB][grD]) else 1
        self._CF = self._GR[self._CB][grD] < 0
        self._GR[self._CB][grD] -= 6 * self._CF
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _adi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0xF

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
        
        self._GR[self._CB][grD] += imd

        self._CF = self._GR[self._CB][grD] > 15
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _adbi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0xF

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
        
        self._GR[self._CB][grD] += imd

        self._CF = self._GR[self._CB][grD] > 9
        self._GR[self._CB][grD] -= 10 * self._CF
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _sbi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0xF

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
        
        self._GR[self._CB][grD] -= imd

        self._ZF = self._GR[self._CB][grD] == 0
        self._CF = self._GR[self._CB][grD] < 0
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _sbbi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0xF

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
        
        self._GR[self._CB][grD] -= imd

        self._ZF = self._GR[self._CB][grD] == 0
        self._CF = self._GR[self._CB][grD] < 0
        self._GR[self._CB][grD] -= 6 * self._CF
        self._GR[self._CB][grD] &= 0xF
        self._PC += 1

        return 1

    def _adm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        self._CF = 0

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
            
            self._GR[self._CB][grD] += self._GR[self._CB][grS] + self._CF
            self._CF = self._GR[self._CB][grD] > 15
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _adbm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        self._CF = 0

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] += self._GR[self._CB][grS] + self._CF
            self._CF = self._GR[self._CB][grD] > 9
            self._GR[self._CB][grD] -= 10 * self._CF
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _sbm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        self._CF = 0
        self._ZF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
            
            self._GR[self._CB][grD] -= self._GR[self._CB][grS] + self._CF
            self._ZF &= 1 if (self._GR[self._CB][grD] == 0) else 0
            self._CF = 1 if (self._GR[self._CB][grD] < 0) else 0
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _sbbm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        self._CF = 0
        self._ZF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
            
            self._GR[self._CB][grD] -= self._GR[self._CB][grS] + self._CF
            self._ZF &= self._GR[self._CB][grD] == 0
            self._CF = self._GR[self._CB][grD] < 0
            self._GR[self._CB][grD] -= 6 * self._CF
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _cmp(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._ZF = self._GR[self._CB][grD] == self._GR[self._CB][grS]
        self._CF = self._GR[self._CB][grD] < self._GR[self._CB][grS]

        self._PC += 1

        return 1

    def _cpm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        self._CF = 0
        self._ZF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._ZF &= self._GR[self._CB][grD] == (self._GR[self._CB][grS] + self._CF)
            self._CF = self._GR[self._CB][grD] < (self._GR[self._CB][grS] + self._CF)

        self._PC += 1

        return 1 * len

    def _cpi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._ZF = self._GR[self._CB][grD] == imd
        self._CF = self._GR[self._CB][grD] < imd
        self._PC += 1
        
        return 1

    def _lcrb(self, opcode):
        grD = (opcode >> 5) & 0x1F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._CB = (opcode >> 3) & 0x03
        self._PC += 1

        return 1

    def _larb(self, opcode):
        grD = (opcode >> 5) & 0x1F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._AB = (opcode >> 3) & 0x03
        self._PC += 1

        return 1

    def _andi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] &= imd
        self._ZF = self._GR[self._CB][grD] == 0
        self._PC += 1

        return 1

    def _ori(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] |= imd
        self._PC += 1

        return 1

    def _xori(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
        
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] ^= imd
        self._PC += 1

        return 1

    def _inc(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = opcode & 0x07
        page = grHi & 0xF8
        
        self._CF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] += self._CF
            self._CF = self._GR[self._CB][grD] > 15
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _incb(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = opcode & 0x07
        page = grHi & 0xF8

        self._CF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] += self._CF
            self._CF = self._GR[self._CB][grD] > 9
            self._GR[self._CB][grD] -= 10 * self._CF
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _dec(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = opcode & 0x07
        page = grHi & 0xF8

        self._CF = 1
        self._ZF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] -= self._CF
            self._ZF &= self._GR[self._CB][grD] == 0
            self._CF = self._GR[self._CB][grD] < 0
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _decb(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = opcode & 0x07
        page = grHi & 0xF8

        self._CF = 1
        self._ZF = 1

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] -= self._CF
            self._ZF &= self._GR[self._CB][grD] == 0
            self._CF = self._GR[self._CB][grD] < 0
            self._GR[self._CB][grD] -= 6 * self._CF
            self._GR[self._CB][grD] &= 0xF

        self._PC += 1

        return 1 * len

    def _rshm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = opcode & 0x07
        page = grHi & 0xF8

        len = ((grLo - grHi) & 0x07)
        for gr in range(grHi + len, grHi, -1):
            grS = page + ((gr - 1) & 0x07)
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = self._GR[self._CB][grS]
        
        self._GR[self._CB][grHi] = 0
        self._PC += 1

        return 1 * len

    def _lshm(self, opcode):
        grLo = (opcode >> 5) & 0x1F
        grHi = opcode & 0x07
        page = grLo & 0xF8

        len = ((grLo - grHi) & 0x07)
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)
            grS = page + ((gr + 1) & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = self._GR[self._CB][grS]
       
        self._GR[self._CB][grLo] = 0
        self._PC += 1
        
        return 1 * len

    def _in(self, opcode):
        grD = (opcode >> 5) & 0x1F
        srS = opcode & 0x0F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] = self.srRead(srS)
        self._PC += 1

        return 1

    def _out(self, opcode):
        srD = opcode & 0x0F
        grS = (opcode >> 5) & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)

        self._srWrite[srD](self, self._GR[self._CB][grS])
        self._PC += 1

        return 1

    def _outi(self, opcode):
        grD = (opcode >> 5) & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        srD = opcode & 0x0F
        imd = (opcode >> 6) & 0x0F

        self._srWrite[srD](self, imd)
        self._PC += 1

        return 1

    def _psam(self, opcode):
        grLo = (opcode >> 5) & 0x1F
        page = grLo & 0x18
        grHi = page | (opcode & 0x07)

        len = ((grHi - grLo) & 0x07) + 1
        for gr in range(grLo, grLo + len):
            grS = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)
 
        self._memory.setSA(self._bSA)
        self._PC += 1

        return 1 * len

    def _plam(self, opcode):
        grLo = (opcode >> 5) & 0x1F
        grHi = (grLo & 0x18) | (opcode & 0x07)
        page = grLo & 0xF8

        LA = 0
        len = ((grHi - grLo) & 0x07) + 1
        for gr in range(grLo, grLo + len):
            grS = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)

            LA = (LA >> 4) | (self._GR[self._CB][grS] << 4)

        if (len > 1):
            self._display.setLA(LA)

        self._PC += 1

        return 1 * len

    def _ldsm(self, opcode):    
        grHi = (opcode >> 5) & 0x1F
        grLo = (grHi & 0x18) | (opcode & 0x07)
        page = grHi & 0xF8

        self._GR[self._CB][grHi] = self._memory.readNibbleExternal()

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi + 1, grHi + len):
            grD = page + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = (self._memory.readExternal() >> 4) & 0x0F

        self._PC += 1

        return 1 * len

    def _stsm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (grHi & 0x18) | (opcode & 0x07)
        page = grHi & 0xF8
        
        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi + 1, grHi + len):
            grS = page + (gr & 0x07)
            grP = page + ((gr - 1) & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)
            
            self._memory.writeExternal((self._GR[self._CB][grS] << 4) | (self._GR[self._CB][grP] & 0x0F))

        self._PC += 1

        return 1 * len

    def _stlm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (grHi & 0x18) | (opcode & 0x07)
        page = grHi & 0xF8
        
        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi + 1, grHi + len):
            grS = page + (gr & 0x07)
            grP = page + ((gr - 1) & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)
            
            self._display.writeDDRAM((self._GR[self._CB][grS] << 4) | (self._GR[self._CB][grP] & 0x0F))

        self._PC += 1

        return 1 * len

    def _stl(self, opcode):
        grS = (opcode >> 5) & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grS] << 8)

        self._display.writeDDRAM(self._GR[self._CB][grS] | 0x30)
        self._PC += 1

        return 1

    def _psai(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._memory.setSA(opcode)
        self._PC += 1

        return 1

    def _plai(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._display.setLA(((opcode >> 2) & 0xF8) | (opcode & 0x07))
        self._PC += 1

        return 1

    def _stls(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._display.writeDDRAM(self._memory.readExternal())
        self._PC += 1

        return 1

    def _stlsa(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)

        self._display.writeDDRAMaddr(imd, self._memory.readExternal())
        self._PC += 1

        return 1

    def _stli(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)
        self._display.writeDDRAM(imd)
        self._PC += 1

        return 1

    def _stlia(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)
        self._display.writeDDRAMaddr(imd, imd)
        self._PC += 1

        return 1

    def _mov(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] = self._GR[self._CB][grS]
        self._PC += 1

        return 1

    def _movm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)
    
            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = self._GR[self._CB][grS]

        self._PC += 1

        return 1 * len

    def _ldi(self, opcode):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
            
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] = imd
        self._PC += 1

        return 1

    def _clrm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        page = grHi & 0xF8

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = page + (gr & 0x07)
                
            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = 0

        self._PC += 1

        return 1 * len

    def _mvac(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._AB][grD] = self._GR[self._CB][grS]
        self._PC += 1

        return 1

    def _mvacm(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._AB][grD] = self._GR[self._CB][grS]

        self._PC += 1

        return 1 * len

    def _mvca(self, opcode):
        grD = (opcode >> 5) & 0x1F
        grS = opcode & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        self._GR[self._CB][grD] = self._GR[self._AB][grS]
        self._PC += 1

        return 1

    def _mvcam(self, opcode):
        grHi = (opcode >> 5) & 0x1F
        grLo = (opcode & 0x1F)
        pageF = grHi & 0xF8
        pageL = grLo & 0xF8

        len = ((grLo - grHi) & 0x07) + 1
        for gr in range(grHi, grHi + len):
            grD = pageF + (gr & 0x07)
            grS = pageL + (gr & 0x07)

            self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

            self._GR[self._CB][grD] = self._GR[self._AB][grS]

        self._PC += 1

        return 1 * len

    def _call(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        imd = (opcode & 0xFFF)
        self._STACK.append(self._PC)
        if (len(self._STACK) > STACK_SIZE):
            self._STACK.pop(0)
        self._PC = imd

        return 1

    def _ret(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (len(self._STACK) > 0):
            self._PC = self._STACK.pop()
        self._PC += 1

        return 1

    def _cpfjr(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        if (self._GR[self._CB][gr] == 4): self._PC += imd
        self._PC += 1

        return 1

    def _ijmr(self, opcode):
        gr = (opcode >> 5) & 0x1F

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][gr] << 8)

        self._PC += self._GR[self._CB][gr]
        self._PC += 1

        return 1

    def _wfe(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (self._SR[0] != 0):
            self._PC += 1

        return 1

    def _jmp(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)
        
        self._PC = opcode & 0xFFF

        return 1

    def _jz(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (self._ZF):
            self._PC = ((opcode & 0x03FF) | (0xC00 & self._PC))
        else: 
            self._PC += 1

        return 1

    def _jnz(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (not self._ZF):
            self._PC = ((opcode & 0x03FF) | (0xC00 & self._PC))
        else:
            self._PC += 1

        return 1

    def _jc(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (self._CF):
            self._PC = ((opcode & 0x03FF) | (0xC00 & self._PC))
        else:
            self._PC += 1

        return 1

    def _jnc(self, opcode):
        grD = (opcode >> 5) & 0x1F
        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][grD] << 8)

        if (not self._CF):
            self._PC = ((opcode & 0x03FF) | (0xC00 & self._PC))
        else:
            self._PC += 1

        return 1

    def _btjr(self, opcode):
        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        cmp = (opcode >> 10) & 0x03

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][gr] << 8)

        if (self._GR[self._CB][gr] & (1 << cmp)): self._PC += imd
        self._PC += 1

        return 1

    def _cpjr(self, opcode):
        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        cmp = (opcode >> 10) & 0x03

        self._bSA = (self._bSA >> 4) | (self._GR[self._CB][gr] << 8)

        if (self._GR[self._CB][gr] == cmp): self._PC += imd
        self._PC += 1

        return 1

    def srRead(self, sr):
        res = self._SR[sr]
        if (sr == 3 or sr == 4):
            self._SR[sr] = 0

        if (sr == 15):
            self._SR[15] &= ~b0

        return res

    def _sr0Write(self, value):
        return

    def _sr1Write(self, value):
        self._SR[1] &= 0x0
        self._SR[0] &= 0x7
    
    def _sr2Write(self, value):
        self._SR[2] &= 0x0

    def _sr3Write(self, value):
        self._ispMode = value & b0
        self._ispTransmitEnable = (value & b1) > 0
        return

    def _sr4Write(self, value):
        self._ispReceiveEnable = (value & b1) > 0
        self._ispTransmit = (value & b0) > 0
        return

    def _sr5Write(self, value):
        self._ispTransmitBuffer = (self._ispTransmitBuffer & 0x0F) | (value << 4)

    def _sr6Write(self, value):
        self._ispTransmitBuffer = (self._ispTransmitBuffer & 0xF0) | value

    def _sr7Write(self, value):
        self._SR[7] &= 0x0
        self._SR[0] &= 0xB

    def _sr8Write(self, value):
        return

    def _sr9Write(self, value):
        self._SR[9] &= ~(value & ~b3)  #clear SR9.0 - SR9.2
        if (self._SR[9] == 0):
            self._SR[0] &= 0xD

    def _sr10Write(self, value):
        if (value & b3):
            self._SR[9] |= b3
        if (value & b2):
            self._SR[9] &= ~b3
        if (value & b1):
            self._SR[10] = 0
            self._counter1 = 0
        if (value & b0):
            if (self._stopwatchMode == SM_DISABLE):
                self._stopwatchMode = SM_ENABLE
        else:
            self._stopwatchMode = SM_DISABLE

    def _sr11Write(self, value):
        return

    def _sr12Write(self, value):
        self._SR[12] &= ~value
        if (self._SR[12] == 0):
            self._SR[0] &= 0xE

    def _sr13Write(self, value):
        self._SR[13] = value

    def _sr14Write(self, value):
        self._SR[14] = 0

    def _sr15Write(self, value):
        if (value & 0b0001):
            self._beeper.beep()
        if (value & 0b0100):
            self._beeper.startTremolo()
        if (value & 0b0010):
            self._beeper.stopTremolo()
        return
