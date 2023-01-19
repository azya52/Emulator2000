import argparse

from PyQt6 import uic, QtCore, QtGui, QtWidgets, QtSvgWidgets
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QByteArray
from PyQt6.QtWidgets import QGraphicsScene, QFileDialog
from PyQt6.QtSerialPort import QSerialPortInfo

import display
from watch import Watch

class Window(QtWidgets.QMainWindow):    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        uic.loadUi('ui/main_window.ui', self)
        self._setupUI()
        
        self._settings = QtCore.QSettings('azya', 'Emulator 2000')
        self._loadSettings()
        self._parseArgs()
        
        self._watchUI = WatchUI(
            self._examine,
            self._face,
            self._internalMem,
            self._externalMem,
            self.portNameCombo.currentText()
        )

        self.deviceWidget.layout().addWidget(self._watchUI)       

    def _parseArgs(self):
        parser = argparse.ArgumentParser(
            description='Emulator 2000, Seiko UC family emulator.'
        )
        parser.add_argument('-ext', nargs='?', help='External memory file')
        parser.add_argument('-rom', nargs='?', help='Internal ROM file')
        parser.add_argument('-face', nargs='?', help='Watch face file (*.svg)')
        args = parser.parse_args()
        if args.ext:
            self._externalMem = args.ext
        if args.rom:
            self._internalMem = args.rom
        if args.face:
            self._face = args.face

    def _loadSettings(self):
        geometry = self._settings.value("window/window_geometry",  QByteArray())
        if (not geometry.isEmpty()):
            self.restoreGeometry(geometry.data())
        else:
            geometry = self.screen().availableGeometry()
            self.setGeometry(QtCore.QRect(geometry.bottomRight() / 5, 3 * geometry.size() / 5))
        state = self._settings.value("window/mainsplitter_state",  QByteArray())
        if (not state.isEmpty()):
            self.mainSplitter.restoreState(state.data())
        else:
            self.mainSplitter.setSizes(
                [int(self.geometry().width() * 0.6), int(self.geometry().width() * 0.4)]
            )
        state = self._settings.value("window/sidesplitter_state",  QByteArray())
        if (not state.isEmpty()):
            self.sideSplitter.restoreState(state.data())
        state = self._settings.value("window/cpusplitter_state",  QByteArray())
        if (not state.isEmpty()):
            self.CPUSplitter.restoreState(state.data())
        state = self._settings.value("window/displaysplitter_state",  QByteArray())
        if (not state.isEmpty()):
            self.displaySplitter.restoreState(state.data())
        index = self._settings.value("window/debugtab_index",  int)
        if (isinstance(index, int)):
            self.debugTabWidget.setCurrentIndex(index)

        self._face = self._settings.value("watch/face", "./assets/uc2000.svg")
        self._internalMem = self._settings.value("watch/internal_mem", "./assets/uc2000.rom")
        self._externalMem = self._settings.value("watch/external_mem", None)
        self.portNameCombo.blockSignals(True)
        self.portNameCombo.setCurrentText(self._settings.value("watch/port_name", None))
        self.portNameCombo.blockSignals(False)

    def _saveSettings(self):
        self._settings.setValue('window/window_geometry', self.saveGeometry())
        self._settings.setValue('window/mainsplitter_state', self.mainSplitter.saveState())
        self._settings.setValue('window/sidesplitter_state', self.sideSplitter.saveState())
        self._settings.setValue('window/cpusplitter_state', self.CPUSplitter.saveState())
        self._settings.setValue('window/displaysplitter_state', self.displaySplitter.saveState())
        self._settings.setValue('window/debugtab_index', self.debugTabWidget.currentIndex())
        self._settings.setValue('watch/port_name', self.portNameCombo.currentText())

    def _setupUI(self):
        self.genRegTree.expandAll()
        
        self.specRegTable.resizeRowsToContents()
        self.specRegTable.resizeColumnsToContents()
        
        for i in range(self.genRegTree.columnCount()):
             self.genRegTree.resizeColumnToContents(i)
        
        self.dispDataTable.resizeRowsToContents()
        self.dispDataTable.resizeColumnsToContents()

        self.dispBlinkTable.resizeRowsToContents()
        self.dispBlinkTable.resizeColumnsToContents()

        self.dispCtrlTable.resizeRowsToContents()
        self.dispCtrlTable.resizeColumnsToContents()

        groupTool = QtGui.QActionGroup(self)
        groupTool.addAction(self.actionSpeedOrig)
        groupTool.addAction(self.actionSpeedx2)
        groupTool.addAction(self.actionSpeedx5)
        groupTool.addAction(self.actionSpeedx10)
        groupTool.addAction(self.actionSpeedMax)
        groupTool.setExclusive(True)

        self.portNameCombo.blockSignals(True)
        self.portNameCombo.addItems(
            [None] + [portInfo.portName() for portInfo in QSerialPortInfo().availablePorts()]
        )
        self.portNameCombo.blockSignals(False)

    def closeEvent(self, event):
        self._saveSettings()
        self._watchUI.close()

        super().closeEvent(event)

    @pyqtSlot(QtWidgets.QTableWidgetItem)
    def specRegTblItemChanged(self, item):
        try:
            self._watchUI.editStateSignal.emit({"SR": {item.column(): int(item.text(), 0)}})
        except ValueError:
            pass

    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def genRegTreeItemChanged(self, item, column):
        if (column > 0):
            bankIndex = self.genRegTree.indexFromItem(item.parent()).row()
            pageIndex = self.genRegTree.indexFromItem(item).row()
            regIndex = pageIndex * 8 + (column - 1)
            try:
                self._watchUI.editStateSignal.emit(
                    {"GR": {bankIndex : {regIndex: int(item.text(column), 0)}}}
                )
            except ValueError:
                pass

    @pyqtSlot(QtWidgets.QTableWidgetItem)
    def asmTblItemChanged(self, item):
        if (item.column() == 1):
            try:
                self._watchUI.editStateSignal.emit(
                    {"MEMORY": [item.row() * 2, int(item.text(), 0)]}
                )
            except ValueError:
                pass
        else:
            self._watchUI.setBreakpoint(item.row(), item.checkState() == Qt.CheckState.Checked)

    @pyqtSlot(QtWidgets.QTableWidgetItem)
    def dispDataTblItemChanged(self, item):
        try:
            addr = item.row() * 10 + item.column()
            self._watchUI.editStateSignal.emit({"DDRAM": {addr: int(item.text(), 0)}})
        except ValueError:
            pass

    @pyqtSlot(QtWidgets.QTableWidgetItem)
    def dispBlinkTblItemChanged(self, item):
        try:
            addr = item.row() * 10 + item.column()
            checked = 1 if (item.checkState() == Qt.CheckState.Checked) else 0
            self._watchUI.editStateSignal.emit({"DARAM": {addr: checked}})
        except ValueError:
            pass

    @pyqtSlot(QtWidgets.QTableWidgetItem)
    def dispCtrlTblItemChanged(self, item):
        try:
            self._watchUI.editStateSignal.emit({"DCTRL": {item.column(): int(item.text(), 0)}})
        except ValueError:
            pass

    @pyqtSlot()
    def pcEditFinished(self):
        try:
            self._watchUI.editStateSignal.emit({"PC": int(self.pcEdit.text(), 0)})
        except ValueError:
            pass

    @pyqtSlot()
    def saEditFinished(self):
        try:
            self._watchUI.editStateSignal.emit({"SA": int(self.saEdit.text(), 0)})
        except ValueError:
            pass

    @pyqtSlot()
    def laEditFinished(self):
        try:
            self._watchUI.editStateSignal.emit({"LA": int(self.laEdit.text(), 0)})
        except ValueError:
            pass

    @pyqtSlot()
    def cbEditFinished(self):
        try:
            self._watchUI.editStateSignal.emit({"CB": int(self.cbEdit.text(), 0)})
        except ValueError:
            pass

    @pyqtSlot()
    def abEditFinished(self):
        try:
            self._watchUI.editStateSignal.emit({"CB": int(self.abEdit.text(), 0)})
        except ValueError:
            pass

    @pyqtSlot(int)
    def cfCheckBoxStateChanged(self, state):
        self._watchUI.editStateSignal.emit({"CF": int(state == Qt.CheckState.Checked.value)})

    @pyqtSlot(int)
    def zfCheckBoxStateChanged(self, state):
        self._watchUI.editStateSignal.emit({"ZF": int(state == Qt.CheckState.Checked.value)})

    @pyqtSlot(str)
    def serialDataEditTextEdited(self, char):
        if (self.keyCodesCheckBox.checkState() == Qt.CheckState.Checked and len(char)):
            self._watchUI.receive(ord(char[-1]))
            self.serialDataEdit.clear()

    @pyqtSlot()
    def on_actionRun_triggered(self):
        self._watchUI.run()

    @pyqtSlot()
    def on_actionPause_triggered(self):
        self._watchUI.pause()

    @pyqtSlot()
    def on_actionStep_triggered(self):
        self._watchUI.step()
    
    @pyqtSlot()
    def on_actionStop_triggered(self):
        self._watchUI.stop()

    @pyqtSlot()
    def on_actionSpeedOrig_triggered(self):
        self._watchUI.setSpeed(1)

    @pyqtSlot()
    def on_actionSpeedx2_triggered(self):
        self._watchUI.setSpeed(0.5)

    @pyqtSlot()
    def on_actionSpeedx5_triggered(self):
        self._watchUI.setSpeed(0.2)

    @pyqtSlot()
    def on_actionSpeedx10_triggered(self):
        self._watchUI.setSpeed(0.1)

    @pyqtSlot()
    def on_actionSpeedMax_triggered(self):
        self._watchUI.setSpeed(0)

    @pyqtSlot()
    def on_actionSerialConnect_triggered(self):
        self._watchUI.setPortName(self.portNameCombo.currentText())

    @pyqtSlot()
    def on_actionTransmit_triggered(self):
        try:
            self._watchUI.receive(int(self.serialDataEdit.text(), 0))
        except ValueError:
            pass

    @pyqtSlot()
    def on_actionOpenFace_triggered(self):
        path, _ = QFileDialog.getOpenFileName(self,
            caption = "Select Face File",
            filter = "SVG Files (*.svg)")
        if path:
            self._watchUI.setFace(path)
            self._settings.setValue('watch/face', path)

    @pyqtSlot()
    def on_actionOpenIntMem_triggered(self):
        path, _ = QFileDialog.getOpenFileName(self, 
            caption = "Select Internal ROM File", 
            filter = "All Files (*);;Binary (*.bin *.rom *.ram)")
        if path:
            self._watchUI.setInternalMem(path)
            self._settings.setValue('watch/internal_mem', path)

    @pyqtSlot()
    def on_actionOpenExtMem_triggered(self):
        path, _ = QFileDialog.getOpenFileName(self,
            caption = "Select External Memory File",
            filter = "All Files (*);;Binary (*.bin *.rom *.ram)")
        if path:
            self._watchUI.setExternalMem(path)
            self._settings.setValue('watch/external_mem', path)

    @pyqtSlot()
    def on_actionUC2000_triggered(self):
        #self.deviceWidget.layout().removeWidget(self.watchUI)
        self._watchUI.close()
        self._watchUI = WatchUI(self._examine, 
            "./assets/uc2000.svg", 
            "./assets/UC2000.rom", 
            None,
            self.portNameCombo.currentText())
        self.deviceWidget.layout().addWidget(self._watchUI)
        self._settings.setValue('watch/face', "./assets/uc2000.svg")
        self._settings.setValue('watch/internal_mem', "./assets/UC2000.rom")
        self._settings.setValue('watch/external_mem', None)

    @pyqtSlot()
    def on_actionDATA2000_triggered(self):
        self._watchUI.close()
        self._watchUI = WatchUI(self._examine, 
            "./assets/data2000.svg", 
            "./assets/UC2000.rom", 
            None,
            self.portNameCombo.currentText())
        self.deviceWidget.layout().addWidget(self._watchUI)
        self._settings.setValue('watch/face', "./assets/data2000.svg")
        self._settings.setValue('watch/internal_mem', "./assets/UC2000.rom")
        self._settings.setValue('watch/external_mem', None)

    @pyqtSlot()
    def on_actionSpacetronic_triggered(self):
        self._watchUI.close()
        self._watchUI = WatchUI(self._examine, 
            "./assets/spacetronic.svg", 
            "./assets/spacetronik.rom", 
            "./assets/spacetronic.ram",
            self.portNameCombo.currentText())
        self.deviceWidget.layout().addWidget(self._watchUI)
        self._settings.setValue('watch/face', "./assets/spacetronic.svg")
        self._settings.setValue('watch/internal_mem', "./assets/spacetronik.rom")
        self._settings.setValue('watch/external_mem', "./assets/spacetronic.ram")

    @pyqtSlot(dict, bool)
    def _examine(self, info, force):
        if ("DEBUG" in info):
            self.actionDebug.setChecked(True)

        if ((self.pcEdit.isVisible() or force) and ("PC" in info)):
            if (not self.pcEdit.hasFocus()):
                self.pcEdit.setText("0x%0.3X" % info["PC"])
        
        if ((self.asmTable.isVisible() or force) and ("PC" in info)):
            self.asmTable.selectRow(info["PC"])

        if ((self.saEdit.isVisible() or force) and ("SA" in info)):
            if (not self.saEdit.hasFocus()):
                self.saEdit.setText("0x%0.3X" % info["SA"])

        if ((self.laEdit.isVisible() or force) and ("LA" in info)):
            if (not self.laEdit.hasFocus()):
                self.laEdit.setText("0x%0.3X" % info["LA"])

        if ((self.cbEdit.isVisible() or force) and ("CB" in info)):
            if (not self.cbEdit.hasFocus()):
                self.cbEdit.setText("0x%0.1X" % info["CB"])

        if ((self.abEdit.isVisible() or force) and ("AB" in info)):
            if (not self.abEdit.hasFocus()):
                self.abEdit.setText("0x%0.1X" % info["AB"])

        if ((self.cfCheckBox.isVisible() or force) and ("CF" in info)):
            self.cfCheckBox.blockSignals(True)
            self.cfCheckBox.setChecked(info["CF"])
            self.cfCheckBox.blockSignals(False)

        if ((self.zfCheckBox.isVisible() or force) and ("ZF" in info)):
            self.zfCheckBox.blockSignals(True)
            self.zfCheckBox.setChecked(info["ZF"])
            self.zfCheckBox.blockSignals(False)

        if ("ISPIN" in info):
            self.terminalList.addItem("< 0x%0.2X" % info["ISPIN"])
            self.terminalList.scrollToBottom()

        if ("ISPOUT" in info):
            self.terminalList.addItem("> 0x%0.2X" % info["ISPOUT"])
            self.terminalList.scrollToBottom()

        if ((self.specRegTable.isVisible() or force) and ("SR" in info)):
            if self.specRegTable.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.specRegTable.blockSignals(True)
                for i, value in info["SR"].items():
                    self.specRegTable.item(0, i).setText("0x%0.1X" % value)
                self.specRegTable.blockSignals(False)

        if ((self.genRegTree.isVisible() or force) and ("GR" in info)):
            if self.genRegTree.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.genRegTree.blockSignals(True)
                for i, bank in info["GR"].items():
                    bankTree = self.genRegTree.topLevelItem(i)
                    for j, value in bank.items():
                        bankTree.child(j >> 3).setText((j & 0x07) + 1, "0x%0.1X" % value)
                self.genRegTree.blockSignals(False)

        if ((self.asmTable.isVisible() or force) and ("LISTING" in info)):
            if self.asmTable.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.asmTable.blockSignals(True)
                if (self.asmTable.rowCount() < len(info["LISTING"])):
                    self.asmTable.setRowCount(len(info["LISTING"]))
                
                itemAdr = QtWidgets.QTableWidgetItem()
                itemAdr.setForeground(QtGui.QBrush(QtGui.QColor(128, 128, 128)))
                itemAdr.setFlags(itemAdr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                itemAdr.setCheckState(Qt.CheckState.Unchecked)

                for i, instr in info["LISTING"].items():
                    item = itemAdr.clone()
                    item.setText('0x%0.3X:' % i)
                    self.asmTable.setItem(i, 0, item)
                    itemOpcode = QtWidgets.QTableWidgetItem(' %0.4X ' % instr[0])
                    itemOpcode.setFlags(itemOpcode.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.asmTable.setItem(i, 1, itemOpcode)
                    itemAsm = QtWidgets.QTableWidgetItem(instr[1])
                    itemAsm.setFlags(itemAsm.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.asmTable.setItem(i, 2, itemAsm)
                    if (i == 0):
                        self.asmTable.resizeRowsToContents()
                        self.asmTable.resizeColumnsToContents() 
                self.asmTable.blockSignals(False)          

        if ((self.dispDataTable.isVisible() or force) and ("DDRAM" in info)):
            if self.dispDataTable.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.dispDataTable.blockSignals(True)
                for i, data in info["DDRAM"].items():
                    self.dispDataTable.item(i // 10, i % 10).setText("0x%0.2X" % data)
                self.dispDataTable.blockSignals(False)

        if ((self.dispBlinkTable.isVisible() or force) and ("DARAM" in info)):
            if self.dispBlinkTable.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.dispBlinkTable.blockSignals(True)
                for i, checked in info["DARAM"].items():
                    checked = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                    self.dispBlinkTable.item(i // 10, i % 10).setCheckState(checked)
                self.dispBlinkTable.blockSignals(False)

        if ((self.dispCtrlTable.isVisible() or force) and ("DCTRL" in info)):
            if self.dispCtrlTable.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.dispCtrlTable.blockSignals(True)
                for i, data in info["DCTRL"].items():
                    self.dispCtrlTable.item(0, i).setText("0x%0.1X" % data)
                self.dispCtrlTable.blockSignals(False)
                
class WatchUI(QtWidgets.QGraphicsView):
    LEFT_BTN = 0
    RIGHT_BTN = 1
    TRANSM_BTN = 2
    MODE_BTN = 3

    BTN_HOT_KEYS = {
        LEFT_BTN: Qt.Key.Key_1,
        MODE_BTN: Qt.Key.Key_2,
        TRANSM_BTN: Qt.Key.Key_3,
        RIGHT_BTN: Qt.Key.Key_4
    }
    
    editStateSignal = pyqtSignal(dict)

    def __init__(self, examine, face, internalMem, externalMem, portName):
        super().__init__()

        self.setScene(QGraphicsScene())

        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setBackgroundRole(QtGui.QPalette.ColorRole.NoRole)
        self.setFrameStyle(0)

        self._examine = examine

        self._draw(face)
        
        self._watch = Watch(internalMem, externalMem, portName)
        self._watch.uiDisplayUpdateSignal.connect(self._render)
        self._watch.examineSignal.connect(self._examineSlot)
        self.editStateSignal.connect(self._watch.editState)
        
        self._watchThread = QtCore.QThread()
        self._watch.moveToThread(self._watchThread)
        self._watchThread.started.connect(self._watch.run)
        self._watchThread.finished.connect(self._watch.finish)
        self._watchThread.start(QtCore.QThread.Priority.LowestPriority)
        
    def setFace(self, path):
        self._draw(path)

    def setExternalMem(self, path):
        self._watch.setExternalMem(path)

    def setInternalMem(self, path):
        self._watch.setInternalMem(path)

    def step(self):
        self._watch.debugStep()

    def pause(self):
        self._watch.debugPause()
    
    def stop(self):
        self._watch.debugStop()
    
    def run(self):
        self._watch.debugRun()

    def setBreakpoint(self, pc, checked):
        self._watch.debugSetBreakpoint(pc, checked)

    def setSpeed(self, speed):
        self._watch.setSpeed(speed)

    def setPortName(self, name):
        self._watch.setPortName(name)

    def receive(self, data):
        self._watch.receive(data)

    def closeEvent(self, event):    
        self._watch.uiDisplayUpdateSignal.disconnect()
        self._watch.examineSignal.disconnect()

        self._watchThread.requestInterruption()
        self._watchThread.quit()
        self._watchThread.wait()

        return super().closeEvent(event)

    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        return super().resizeEvent(event)

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            for id, key in self.BTN_HOT_KEYS.items():
                if (event.key() == key):
                    self._buttonPressed(id)
        return super().keyPressEvent(event)

    def keyReleaseEvent(self, event):            
        if not event.isAutoRepeat():
            for id, key in self.BTN_HOT_KEYS.items():
                if (event.key() == key):
                    self._buttonReleased(id)
        return super().keyReleaseEvent(event)

    @pyqtSlot(dict, bool)
    def _examineSlot(self, info, force):
        if (self._examine != None):
            self._examine(info, force)
    
    @pyqtSlot(int)
    def _buttonPressed(self, id):
        self._watch.btnPressed(id)

    @pyqtSlot(int)
    def _buttonReleased(self, id):
        self._watch.btnReleased(id)

    def _draw(self, faceSVG):
        self.scene().clear()
        self.scene().setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        face = QtSvgWidgets.QGraphicsSvgItem(faceSVG)
        self.scene().setSceneRect(face.boundingRect())
        self.scene().addItem(face)
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.btnGroup = QtWidgets.QButtonGroup()
        self.btnGroup.idPressed.connect(self._buttonPressed)
        self.btnGroup.idReleased.connect(self._buttonReleased)           
        
        id = 0
        while (face.renderer().elementExists("button%d" % id)):
            btn = QtWidgets.QPushButton(objectName="watchButton")
            btn.setGeometry(face.renderer().boundsOnElement("button%d" % id).toRect())
            btn.setToolTip("Shortcut: " + QtGui.QKeySequence(self.BTN_HOT_KEYS[id]).toString()) 
            self.scene().addWidget(btn)
            self.btnGroup.addButton(btn, id)
            id += 1
                
        self._pixels = [0] * (display.SCR_WIDTH * display.SCR_HEIGHT)

        dot = face.renderer().boundsOnElement("dotBounds")
        dotIndent = face.renderer().boundsOnElement("dotIndentBounds")
        charIndent = face.renderer().boundsOnElement("charIndentBounds")
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        pen = QtGui.QPen(Qt.PenStyle.NoPen)
        for i in range(display.SCR_HEIGHT * display.SCR_WIDTH):
            pY = i // display.SCR_WIDTH
            pX = i % display.SCR_WIDTH
            y = (dot.y() + pY * (dot.height() + dotIndent.height()) + 
                (pY // display.DOT_COUNT_Y) * (charIndent.height() - dotIndent.height()))
            x = (dot.x() + pX * (dot.width() + dotIndent.height()) + 
                (pX // display.DOT_COUNT_X) * (charIndent.width() - dotIndent.width()))
            self._pixels[i] = self.scene().addRect(x, y, dot.width(), dot.height(), pen, brush)
            self._pixels[i].setOpacity(0)
        
    @pyqtSlot(list)
    def _render(self, pixels):
        for i, pixel in enumerate(self._pixels):
            pixel.setOpacity(0.35 * pixels[i] + 0.65 * pixel.opacity())
