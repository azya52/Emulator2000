INTERNAL_SIZE = 1024 * 6
EXTERNAL_OFFSET = 1024 * 6
EXTERNAL_SIZE = 1024 * 2
MEM_SIZE = 1024 * 8

class Memory():
    def __init__(self, internalPath, externalPath):
        self._memory = bytearray()
        self._SA = 0
        self._updated = []
        self.setInternal(internalPath)
        self.setExternal(externalPath)

    def getOpcode(self, PC):
        PC = (PC & 0xFFF) << 1
        return (self._memory[PC] << 8) | self._memory[PC + 1]

    def readExternal(self):
        value = self._memory[EXTERNAL_OFFSET + self._SA]
        self._SA = (self._SA + 1) & 0x7FF
        return value

    def readNibbleExternal(self):
        return self._memory[EXTERNAL_OFFSET + self._SA] & 0x0F

    def writeExternal(self, value):
        self.writeByte(EXTERNAL_OFFSET + self._SA, value)
        self._SA = (self._SA + 1) & 0x7FF

    def writeByte(self, addr, value):
        self._memory[addr] = value
        self._updated.append(addr >> 1)
    
    def writeWord(self, addr, value):
        self._memory[addr] = (value >> 8) & 0xFF
        self._memory[addr + 1] = value & 0xFF
        self._updated.append(addr >> 1)

    def setSA(self, value):
        self._SA = value & 0x7FF

    def SA(self):
        return self._SA

    def length(self):
        return len(self._memory) // 2
   
    def getUpdated(self):
        updated = self._updated
        self._updated = []
        return updated

    def setInternal(self, path):
        rom = bytearray()
        if (path != None):
            try:
                with open(path, "rb") as bin_f:
                    rom = bytearray(bin_f.read())
            except FileNotFoundError as e:
                print(e.strerror, e.filename)
        rom += bytearray([0] * (INTERNAL_SIZE - len(rom)))
        self._memory = rom[:INTERNAL_SIZE] + self._memory[EXTERNAL_OFFSET:]
        self._updated.extend(range(len(rom) // 2)) 

    def setExternal(self, path):
        mem = bytearray()
        if (path != None):
            try:
                with open(path, "rb") as bin_f:
                    mem = bytearray(bin_f.read())
            except FileNotFoundError as e:
                print(e.strerror, e.filename)
        mem += bytearray([0] * (EXTERNAL_SIZE - len(mem)))
        self._memory = self._memory[:EXTERNAL_OFFSET] + mem[:EXTERNAL_SIZE]
        self._updated.extend(range((EXTERNAL_OFFSET + len(mem)) // 2))

    def examine(self):
        return {
            "SA": self._SA,
        }