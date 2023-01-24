from charset import CHARSET

CHAR_COUNT_X = 10
CHAR_COUNT_Y = 4
CHAR_COUNT = CHAR_COUNT_Y * CHAR_COUNT_X

DOT_COUNT_X = 5
DOT_COUNT_Y = 7

SCR_WIDTH = CHAR_COUNT_X * DOT_COUNT_X
SCR_HEIGHT = CHAR_COUNT_Y * DOT_COUNT_Y

DDRAM_OFFSET = 0
DARAM_OFFSET = 64
DCTRL_OFFSET = 112

DCTRL_COUNT = 16

class Display():
    def __init__(self):
        self._DDRAM = [0] * CHAR_COUNT
        self._DARAM = [0] * CHAR_COUNT
        self._DCTRL = [0] * DCTRL_COUNT
        self._pixels = [0] * (SCR_WIDTH * SCR_HEIGHT)
        self._blinkChar = 0
        self._LA = 0
        self._contrast = 16
        self._pixelOpacity = [0, 0]
        self._counter = 0
        self._scancharCounter = 0
        self._reflects = [[0, 0], [0, 0]]
        self._resetScenchar = False
        self._setPixelOpacity()
        self._storeCR = (
            Display._setCtrlRegTopHalf,
            Display._setCtrlRegBottomHalf,
            Display._setCtrlRegUndefined0x71,
            Display._setCtrlRegUndefined0x72,
            Display._setCtrlRegScanStop,
            Display._setCtrlRegBlinkMode,
            Display._setCtrlRegTestFill,
            Display._setCtrlRegDirectDrawMode,
            Display._setCtrlRegAutoRedraw,
            Display._setCtrlRegAddContrast,
            Display._setCtrlRegDownContrast,
            Display._setCtrlRegClearCtrlRegs,
            Display._setCtrlRegForceRedraw,
            Display._setCtrlRegClearCharRegs,
            Display._setCtrlRegBlinkRegs,
            Display._setCtrlRegResetScanline
        )

    def _updateBlinkChar(self):
        if (self._blinkChar):
            self._blinkChar = 0
        else:
            self._blinkChar = 255 if (self._DCTRL[0x5]) else 32
                        
    def _directDraw(self, counter, value):    
        dotY = (counter >> 4) & 0x07
        charX = counter & 0x0F
        if ((charX < CHAR_COUNT_X) and (dotY < DOT_COUNT_Y)):
            charY = (counter >> 7) & 0x03
            reflect = 0
            if (charY > 1):
                charY ^= 1
                dotY = DOT_COUNT_Y - 1 - dotY
                charX = CHAR_COUNT_X - 1 - charX
                reflect = DOT_COUNT_X - 1
            offsetY = (charY * DOT_COUNT_Y + dotY) * SCR_WIDTH
            for dotX in range(DOT_COUNT_X):
                self._pixels[offsetY + charX * DOT_COUNT_X + abs(reflect - dotX)] = value & 0x01
                value >>= 1

    def _drawScenline(self, counter):
        dotY = (counter >> 4) & 0x07
        startCharX = max((counter & 0x0F) - 1, 0)
        if ((startCharX < CHAR_COUNT_X) and (dotY < DOT_COUNT_Y)):
            stopCharX = min((counter & 0x0F) + 3, CHAR_COUNT_X)
            charY = (counter >> 7) & 0x03
            if (charY > 1):
                charY ^= 1
                dotY = 6 - dotY
                startCharX, stopCharX = CHAR_COUNT_X - stopCharX, CHAR_COUNT_X - startCharX
            reflect = self._reflects[charY >> 1]
            offsetY = (charY * DOT_COUNT_Y + dotY) * SCR_WIDTH
            pixels = self._pixels
            for charX in range(startCharX, stopCharX):
                charPos = charY * CHAR_COUNT_X + charX
                if (self._DARAM[charPos] and self._blinkChar):
                    char = CHARSET[self._blinkChar][abs(reflect[1] - dotY)]
                else:
                    char = CHARSET[self._DDRAM[charPos]][abs(reflect[1] - dotY)]
                for dotX in range(DOT_COUNT_X):
                    pixels[offsetY + charX * DOT_COUNT_X + dotX] = char[abs(reflect[0] - dotX)]  

    def _setPixelOpacity(self):       
        self._pixelOpacity[0] = max((self._contrast - 15) * 6, 0) / 255
        self._pixelOpacity[1] = min(15 * self._contrast, 255) / 255

    def _setCtrlRegTopHalf(self, value):
        self._DCTRL[0x0] = value & 0x03
        if ((value & 0x03) == 0):
            self._reflects[0] = [0, 0]
        elif ((value & 0x03) == 1):
            self._reflects[0] = [4, 0]
        else:
            self._reflects[0] = [4, 6]

    def _setCtrlRegBottomHalf(self, value):
        self._DCTRL[0x1] = value & 0x03
        if ((value & 0x03) == 0):
            self._reflects[1] = [4, 6]
        elif ((value & 0x03) == 1):
            self._reflects[1] = [0, 6]
        else:
            self._reflects[1] = [0, 0]

    def _setCtrlRegUndefined0x71(self, value):
        self._DCTRL[0x2] = value
    
    def _setCtrlRegUndefined0x72(self, value):
        self._DCTRL[0x3] = value

    def _setCtrlRegScanStop(self, value):
        self._DCTRL[0x4] = value & 0x01

    def _setCtrlRegBlinkMode(self, value):
        self._DCTRL[0x5] = value & 0x01

    def _setCtrlRegTestFill(self, value):
        self._DCTRL[0x6] = value & 0x01
        if (value & 0x01):
            self._pixels = [1] * (SCR_WIDTH * SCR_HEIGHT)
            self._pixelOpacity[1] = 1
        else:
            self._setPixelOpacity()

    def _setCtrlRegDirectDrawMode(self, value):
        self._DCTRL[0x7] = value & 0x01

    def _setCtrlRegAutoRedraw(self, value):
        self._DCTRL[0x8] = value & 0x01
         
    def _setCtrlRegAddContrast(self, value):
        if (self._contrast < 32):
            self._contrast += 1
            self._setPixelOpacity()

    def _setCtrlRegDownContrast(self, value):
        if (self._contrast > 0):
            self._contrast -= 1
            self._setPixelOpacity()

    def _setCtrlRegClearCharRegs(self, value):
        #to-do clearing is stop after switching to direct mode?
        self._DDRAM = [0] * CHAR_COUNT

    def _setCtrlRegForceRedraw(self, value):
        self._DCTRL[0xC] = 1
    
    def _setCtrlRegBlinkRegs(self, value):
        self._DARAM = [0] * CHAR_COUNT

    def _setCtrlRegClearCtrlRegs(self, value):
        self._DCTRL = [0] * DCTRL_COUNT

    def _setCtrlRegResetScanline(self, value):
        self._scancharCounter = 0

    def writeDDRAM(self, value):
        self.writeDDRAMaddr(self._LA, value)
        self._LA = (self._LA + 1) & 0xFF

    def writeDDRAMaddr(self, addr, value):
        if (self._DCTRL[0x7] or ((addr == DCTRL_OFFSET + 0x7) and (value & 0x1))):
            if (not self._DCTRL[0x6] and (self._scancharCounter < (32 * 16))):
                self._directDraw(self._scancharCounter, value)
            self._scancharCounter += 1
            
        if (addr in range(DDRAM_OFFSET, DDRAM_OFFSET + CHAR_COUNT)):
            self._DDRAM[addr] = value
        elif (addr in range(DARAM_OFFSET, DARAM_OFFSET + CHAR_COUNT)):
            self._DARAM[addr - DARAM_OFFSET] = value & 0x1
        elif (addr in range(DCTRL_OFFSET, DCTRL_OFFSET + 0xF + 1)):
            self._storeCR[addr - DCTRL_OFFSET](self, value)


    def setLA(self, value):
        self._LA = value

    def clock(self):
        DCTRL = self._DCTRL

        if (not (self._counter & 0x3FF)):
            if (DCTRL[0x8]):
                self._scancharCounter = 0
            self._updateBlinkChar()

        if (not DCTRL[0x7]):       
            if ((not DCTRL[0x4]) and (not DCTRL[0x6]) and (self._scancharCounter < (32 * 16))):
                self._drawScenline(self._scancharCounter)
            self._scancharCounter += 4

        if (DCTRL[0xC] and (self._scancharCounter >= (32 * 16))):
            self._scancharCounter = 0
            self._DCTRL[0xC] = 0

        self._counter += 1

    def setDDRAM(self, addr, value):
        self.writeDDRAMaddr(addr + DDRAM_OFFSET, value)

    def setDARAM(self, addr, value):
        self.writeDDRAMaddr(addr + DARAM_OFFSET, value)

    def setDCTRL(self, addr, value):
        self.writeDDRAMaddr(addr + DCTRL_OFFSET, value)

    def getPixels(self):
        opacity = self._pixelOpacity
        return [opacity[pixel] for pixel in self._pixels]
        
    def examine(self):
        return {
            "DDRAM": {i : value for i, value in enumerate(self._DDRAM)},
            "DARAM": {i : value for i, value in enumerate(self._DARAM)},
            "DCTRL": {i : value for i, value in enumerate(self._DCTRL)},
            "LA": self._LA
        }