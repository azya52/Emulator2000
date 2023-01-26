GR_STR = [
    'RA0', 'RA1', 'RA2', 'RA3', 'RA4', 'RA5', 'RA6', 'RA7',
    'RB0', 'RB1', 'RB2', 'RB3', 'RB4', 'RB5', 'RB6', 'RB7',
    'RC0', 'RC1', 'RC2', 'RC3', 'RC4', 'RC5', 'RC6', 'RC7',
    'RD0', 'RD1', 'RD2', 'RD3', 'RD4', 'RD5', 'RD6', 'RD7',
]

SR_STR = [
    'RS0', 'SR1', 'SR2', 'SR3', 'SR4', 'SR5', 'SR6', 'SR7',
    'SR8', 'SR9', 'SR10', 'SR11', 'SR12', 'SR13', 'SR14', 'SR15',
]

class Disassembler():

    def __init__(self):
        self._base = '0x%X'
        self._lblbase = '0x%0.3X'

        self._instructions = (
			Disassembler._add,
			Disassembler._adb,
			Disassembler._sub,
			Disassembler._sbb,
			Disassembler._adi,
			Disassembler._adbi,
			Disassembler._sbi,
			Disassembler._sbbi,
			Disassembler._adm,
			Disassembler._adbm,
			Disassembler._sbm,
			Disassembler._sbbm,
			Disassembler._cmp,
			Disassembler._cpm,
			Disassembler._cpi,
			Disassembler._op0x3C, #LCRB, LARB
			Disassembler._andi,
			Disassembler._ori,
			Disassembler._xori,
			Disassembler._op0x4C, #INC, INCB, DEC, DECB
			Disassembler._op0x50, #RSHM, LSHM
			Disassembler._in,
			Disassembler._out,
			Disassembler._outi,
			Disassembler._op0x60, #PSAM, PLAM
			Disassembler._op0x64, #LDSM, STSM
			Disassembler._stlm,
			Disassembler._stl,
			Disassembler._psai,
			Disassembler._psai,
			Disassembler._plai,
			Disassembler._op0x7C, #STLS, #STLSA, #STLI, #STLIA,
			Disassembler._mov,
			Disassembler._movm,
			Disassembler._ldi,
			Disassembler._clrm,
			Disassembler._mvac,
			Disassembler._mvacm,
			Disassembler._mvca,
			Disassembler._mvcam,
			Disassembler._call,
			Disassembler._call,
			Disassembler._call,
			Disassembler._call,
			Disassembler._ret,
			Disassembler._cpfjr,
			Disassembler._ijmr,
			Disassembler._wfe,
			Disassembler._jmp,
			Disassembler._jmp,
			Disassembler._jmp,
			Disassembler._jmp,
			Disassembler._jz,
			Disassembler._jnz,
			Disassembler._jc,
			Disassembler._jnc,
			Disassembler._btjr,
			Disassembler._btjr,
			Disassembler._btjr,
			Disassembler._btjr,
			Disassembler._cpjr,
			Disassembler._cpjr,
			Disassembler._cpjr,
			Disassembler._cpjr,
        )

        self._0x3C = (Disassembler._lcrb, Disassembler._larb)
        self._0x7C = (Disassembler._stls, Disassembler._stlsa, Disassembler._stli, Disassembler._stlia)
        self._0x4C = (Disassembler._inc, Disassembler._incb, Disassembler._dec, Disassembler._decb)
        self._0x50 = (Disassembler._rshm, Disassembler._lshm)
        self._0x60 = (Disassembler._psam, Disassembler._plam)
        self._0x64 = (Disassembler._stsm, Disassembler._ldsm)

    def disassemble(self, memory):
        pcList = memory.getUpdated()
        if (len(pcList) > 0):
            instructions = {"LISTING": {}}
            for pc in pcList:
                opcode = memory.getOpcode(pc)
                instructions["LISTING"][pc] = [opcode, self._instructions[opcode >> 10](self, opcode, pc)]

            return instructions
        else:
            return {}

    def _op0x3C(self, opcode, pc):
        adOp = (opcode >> 9) & 0x01
        return self._0x3C[adOp](self, opcode, pc)
    
    def _op0x7C(self, opcode, pc):
        adOp = (opcode >> 3) & 0x03
        return self._0x7C[adOp](self, opcode, pc)

    def _op0x4C(self, opcode, pc):
        adOp = (opcode >> 3) & 0x03
        return self._0x4C[adOp](self, opcode, pc)

    def _op0x50(self, opcode, pc):
        adOp = (opcode >> 3) & 0x01
        return self._0x50[adOp](self, opcode, pc)

    def _op0x60(self, opcode, pc):
        adOp = (opcode >> 4) & 0x01
        return self._0x60[adOp](self, opcode, pc)

    def _op0x64(self, opcode, pc):
        adOp = (opcode >> 3) & 0x01
        return self._0x64[adOp](self, opcode, pc)

    def _add(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'add ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _adb(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'adb ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _sub(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'sub ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _sbb(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'sbb ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _adi(self, opcode, pc):
        imd = (opcode >> 1) & 0xF
        grD = (opcode >> 5) & 0x1F
        return 'adi ' + GR_STR[grD] + ', ' + self._base % imd

    def _adbi(self, opcode, pc):
        imd = (opcode >> 1) & 0xF
        grD = (opcode >> 5) & 0x1F
        return 'adbi ' + GR_STR[grD] + ', ' + self._base % imd

    def _sbi(self, opcode, pc):
        imd = (opcode >> 1) & 0xF
        grD = (opcode >> 5) & 0x1F
        return 'sbi ' + GR_STR[grD] + ', ' + self._base % imd

    def _sbbi(self, opcode, pc):
        imd = (opcode >> 1) & 0xF
        grD = (opcode >> 5) & 0x1F
        return 'sbbi ' + GR_STR[grD] + ', ' + self._base % imd

    def _adm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'adm ' + GR_STR[grF] + ', %s' % grL

    def _adbm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'adbm ' + GR_STR[grF] + ', %s' % grL

    def _sbm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'sbm ' + GR_STR[grF] + ', %s' % grL

    def _sbbm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'sbbm ' + GR_STR[grF] + ', %s' % grL

    def _cmp(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'cmp ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _cpm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'cpm ' + GR_STR[grF] + ', %s' % grL

    def _cpi(self, opcode, pc):
        imd = (opcode >> 1) & 0x0F
        grD = (opcode >> 5) & 0x1F
        return 'cpi ' + GR_STR[grD] + ', ' + self._base % imd

    def _lcrb(self, opcode, pc):
        cb = (opcode >> 3) & 0x03
        return 'lcrb %s' % cb

    def _larb(self, opcode, pc):
        ab = (opcode >> 3) & 0x03
        return 'larb %s' % ab

    def _andi(self, opcode, pc):
        imd = (opcode >> 1) & 0x0F
        grD = (opcode >> 5) & 0x1F
        return 'andi ' + GR_STR[grD] + ', ' + self._base % imd

    def _ori(self, opcode, pc):
        imd = (opcode >> 1) & 0x0F
        grD = (opcode >> 5) & 0x1F
        return 'ori ' + GR_STR[grD] + ', ' + self._base % imd

    def _xori(self, opcode, pc):
        imd = (opcode >> 1) & 0x0F
        grD = (opcode >> 5) & 0x1F
        return 'xori ' + GR_STR[grD] + ', ' + self._base % imd

    def _inc(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'inc ' + GR_STR[grF] + ', %s' % grL

    def _incb(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'incb ' + GR_STR[grF] + ', %s' % grL

    def _dec(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'dec ' + GR_STR[grF] + ', %s' % grL

    def _decb(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'decb ' + GR_STR[grF] + ', %s' % grL

    def _rshm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'rshm ' + GR_STR[grF] + ', %s' % grL

    def _lshm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'lshm ' + GR_STR[grF] + ', %s' % grL

    def _in(self, opcode, pc):
        srS = opcode & 0x0F
        grD = (opcode >> 5) & 0x1F
        return 'in ' + GR_STR[grD] + ', ' + SR_STR[srS]

    def _out(self, opcode, pc):
        srD = opcode & 0x0F
        grS = (opcode >> 5) & 0x1F
        return 'out ' + SR_STR[srD] + ', ' + GR_STR[grS]

    def _outi(self, opcode, pc):
        srD = opcode & 0x0F
        imd = (opcode >> 6) & 0x0F
        return 'outi ' + SR_STR[srD] + ', ' + self._base % imd

    def _psam(self, opcode, pc):
        grLo = (opcode >> 5) & 0x1F
        grHi = opcode & 0x07
        return 'psam ' + GR_STR[grLo] + ', %s' % grHi

    def _plam(self, opcode, pc):
        grLo = (opcode >> 5) & 0x1F
        grHi = opcode & 0x07
        return 'plam ' + GR_STR[grLo] + ', %s' % grHi

    def _ldsm(self, opcode, pc):    
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'ldsm ' + GR_STR[grF] + ', %s' % grL

    def _stsm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'stsm ' + GR_STR[grF] + ', %s' % grL

    def _stlm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'stlm ' + GR_STR[grF] + ', %s' % grL       

    def _stl(self, opcode, pc):
        grS = (opcode >> 5) & 0x1F
        return 'stl ' + GR_STR[grS]

    def _psai(self, opcode, pc):
        imd = opcode & 0x07FF
        return 'psai ' + self._base % imd

    def _plai(self, opcode, pc):
        imd = (((opcode >> 2) & 0xF8) | (opcode & 0x07))
        return 'plai ' + self._base % imd

    def _stls(self, opcode, pc):
        return 'stls'

    def _stlsa(self, opcode, pc):
        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)
        return 'stlsa ' + self._base % imd

    def _stli(self, opcode, pc):
        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)
        return 'stli ' + self._base % imd

    def _stlia(self, opcode, pc):
        imd = ((opcode >> 2) & 0xF8) | (opcode & 0x07)
        return 'stlia ' + self._base % imd

    def _mov(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'mov ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _movm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'movm ' + GR_STR[grF] + ', ' + GR_STR[grL]

    def _ldi(self, opcode, pc):
        grD = (opcode >> 5) & 0x1F
        imd = (opcode >> 1) & 0x0F
        return 'ldi ' +  GR_STR[grD] + ', ' + self._base % imd

    def _clrm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = opcode & 0x07
        return 'clrm ' + GR_STR[grF] + ', %s' % grL

    def _mvac(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'mvac ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _mvacm(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'mvacm ' + GR_STR[grF] + ', ' + GR_STR[grL]

    def _mvca(self, opcode, pc):
        grS = opcode & 0x1F
        grD = (opcode >> 5) & 0x1F
        return 'mvca ' + GR_STR[grD] + ', ' + GR_STR[grS]

    def _mvcam(self, opcode, pc):
        grF = (opcode >> 5) & 0x1F
        grL = (opcode & 0x1F)
        return 'mvcam ' + GR_STR[grF] + ', %s' % grL

    def _call(self, opcode, pc):
        imd = (opcode) & 0x1FFF
        return 'call ' + self._lblbase % imd

    def _ret(self, opcode, pc):
        return 'ret'

    def _cpfjr(self, opcode, pc):
        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        return 'cpfjr ' + GR_STR[gr] + ', ' + self._lblbase % (imd + pc + 1)

    def _ijmr(self, opcode, pc):
        gr = (opcode >> 5) & 0x1F
        return 'ijmr ' + GR_STR[gr]

    def _wfe(self, opcode, pc):
        return 'wfe'

    def _jmp(self, opcode, pc):
        imd = (opcode) & 0x1FFF
        return 'jmp ' + self._lblbase % imd

    def _jz(self, opcode, pc):
        imd = ((opcode & 0x03FF) | (0xC00 & pc))
        return 'jz ' + self._lblbase % imd

    def _jnz(self, opcode, pc):
        imd = ((opcode & 0x03FF) | (0xC00 & pc))
        return 'jnz ' + self._lblbase % imd

    def _jc(self, opcode, pc):
        imd = ((opcode & 0x03FF) | (0xC00 & pc))
        return 'jc ' + self._lblbase % imd

    def _jnc(self, opcode, pc):
        imd = ((opcode & 0x03FF) | (0xC00 & pc))
        return 'jnc ' + self._lblbase % imd

    def _btjr(self, opcode, pc):
        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        cmp = (opcode >> 10) & 0x03
        return 'btjr ' + GR_STR[gr] + ', %s' % cmp + ', ' + self._lblbase % (imd + pc + 1)

    def _cpjr(self, opcode, pc):
        imd = opcode & 0x1F
        gr = (opcode >> 5) & 0x1F
        cmp = (opcode >> 10) & 0x03
        return 'cpjr ' + GR_STR[gr] + ', %s' % cmp + ', ' + self._lblbase % (imd + pc + 1)
