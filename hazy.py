#!/usr/bin/python
from threading import Thread

import libhazy as hazy
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from pathlib import Path
import traceback
from multiprocessing import Pool, cpu_count, Pipe
from sympy import simplify as simplifyExpr


def simJob(expr):
    print("simplify start")
    simplified = simplifyExpr(expr)
    print("simplify stop")
    return simplified


class ExprView(QStackedWidget):
    def __init__(self, parent):
        super(ExprView, self).__init__(parent)

        self.loader = QUiLoader()
        self.ui = self.loader.load("exprview.ui")

        self.addWidget(self.ui.page)
        self.addWidget(self.ui.page_2)

        self.ui.saveButton.clicked.connect(self.save)
        self.ui.simplifyButton.clicked.connect(self.simplify)
        self.ui.cancelButton.clicked.connect(self.cancel)

        self.imageScene = QGraphicsScene()
        self.ui.imageView.setScene(self.imageScene)
        self.dialog = QErrorMessage()

        self.emitter = QObject()
        self.connect(self.emitter, SIGNAL("data(PyObject)"), self.simplifyResult)

    def showExpression(self, expr):
        tempFile = QTemporaryFile("hazy-")
        self.imageScene.clear()
        if tempFile.open():
            try:
                tempFile.close()
                self.current = expr
                hazy.saveToImg(tempFile.fileName(), expr)
                picture = QPixmap(tempFile.fileName())
                self.imageScene.addPixmap(picture)
                self.ui.saveButton.setEnabled(True)
                self.ui.simplifyButton.setEnabled(True)
            except:
                print(traceback.format_exc())
                self.dialog.showMessage("Cannot show expression!\n" + traceback.format_exc())

    def save(self):
        extensions = "LaTex (*.tex);;PNG image (*.png);;MathML (*.mathml *.xml);;DVI (*.dvi);;PDF (*.pdf);;PostScript (*.ps);;DOT (*.gv);;ASCII (*.txt);;Unicode (*.txt);;Text (*.txt)"
        extensionsList = extensions.split(";;")
        fileName = QFileDialog.getSaveFileName(self, "Save expression", str(Path.home()), extensions)
        try:
            if fileName[0] != "":
                if fileName[1] == extensionsList[0]:
                    hazy.saveToLaTex(fileName[0] + ".tex", self.current)
                elif fileName[1] == extensionsList[1]:
                    hazy.saveToImg(fileName[0] + ".png", self.current)
                elif fileName[1] == extensionsList[2]:
                    hazy.saveToMathML(fileName[0] + ".mathml", self.current)
                elif fileName[1] == extensionsList[3]:
                    hazy.saveToDVI(fileName[0] + ".dvi", self.current)
                elif fileName[1] == extensionsList[4]:
                    hazy.saveToPDF(fileName[0] + ".pdf", self.current)
                elif fileName[1] == extensionsList[5]:
                    hazy.saveToPS(fileName[0] + ".ps", self.current)
                elif fileName[1] == extensionsList[6]:
                    hazy.saveToDot(fileName[0] + ".gv", self.current)
                elif fileName[1] == extensionsList[7]:
                    hazy.saveToASCII(fileName[0] + ".txt", self.current)
                elif fileName[1] == extensionsList[8]:
                    hazy.saveToUnicode(fileName[0] + ".txt", self.current)
                elif fileName[1] == extensionsList[9]:
                    hazy.saveToText(fileName[0] + ".txt", self.current)
        except:
            e = sys.exc_info()[0]
            print(traceback.format_exc())
            self.dialog.showMessage("Cannot export expression!\n" + traceback.format_exc())

    def poolCallback(self, result):
        self.emitter.emit(SIGNAL("data(PyObject)"), result)

    def simplifyResult(self, result):
        self.setCurrentIndex(0)
        self.showExpression(result)

    def simplify(self):
        msgBox = QMessageBox()
        msgBox.setText("WARNING! This operation can be very slow!")
        msgBox.setInformativeText("Continue?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec()

        if ret == QMessageBox.Yes:
            self.setCurrentIndex(1)
            self.pool = Pool(processes=cpu_count() - 1)
            self.pool.apply_async(simJob, (self.current,), callback=self.poolCallback)

    def cancel(self):
        self.pool.terminate()
        self.pool.join()
        self.setCurrentIndex(0)

    def wheelEvent(self, event):
        if hasattr(self, "current"):
            zoomIn = 1.2
            zoomOut = 1 / zoomIn

            oldPos = self.ui.imageView.mapToScene(event.pos())

            if event.angleDelta().y() > 0:
                factor = zoomIn
            else:
                factor = zoomOut

            self.ui.imageView.scale(factor, factor)

            newPos = self.ui.imageView.mapToScene(event.pos())
            delta = newPos - oldPos
            self.ui.imageView.translate(delta.x(), delta.y())


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        loader = QUiLoader()
        loader.registerCustomWidget(ExprView)
        self.ui = loader.load("mainwindow.ui", self)

        self.model = QStandardItemModel(1, 3)
        self.model.setHorizontalHeaderLabels(["Symbol", "Value", "Error"])
        self.ui.values.setModel(self.model)

        self.ui.typeBox.addItems(["text", "LaTex"])

        self.connectSignals()

        self.dialog = QErrorMessage()
        self.ui.splitter.setSizes([517, 332])

        self.setWindowTitle("Hazy")

    def connectSignals(self):
        self.ui.addRowButton.clicked.connect(self.addRow)
        self.ui.removeRowButton.clicked.connect(self.removeRow)
        self.ui.clearButton.clicked.connect(self.clearValues)

        self.ui.calcButton.clicked.connect(self.compute)
        self.ui.evalButton.clicked.connect(self.eval)

    def addRow(self):
        self.model.appendRow([])

    def removeRow(self):
        index = QInputDialog.getInt(self, "Set row index", "Row index:", 1, 1, self.model.rowCount())
        if index[1]:
            self.model.removeRow(index[0] - 1)

    def clearValues(self):
        self.model.removeRows(0, self.model.rowCount())

    def cmpTest(self):
        if self.ui.input.toPlainText() == "":
            self.dialog.showMessage("Input expression is empty!")
            return False
        if self.ui.symInput.text() == "":
            self.dialog.showMessage("No symbols to differentiate by!")
            return False

        return True

    def evalTest(self):
        if not hasattr(self, "finalExpr") or self.finalExpr is None:
            self.dialog.showMessage("No expression!")
            return False

        values = self.getValues()
        if not values:
            self.dialog.showMessage("No values!")

        return values

    def compute(self):
        if not self.cmpTest():
            return

        self.data = self.getData()
        try:
            self.expr, self.finalExpr = hazy.compute(self.data)
            self.ui.preview.showExpression(self.expr)
            self.ui.final.showExpression(self.finalExpr)
        except:
            e = sys.exc_info()[0]
            print(traceback.format_exc())
            self.dialog.showMessage("Cannot compute!\n" + traceback.format_exc())

    def eval(self):
        values = self.evalTest()
        if not values:
            return

        try:
            value = hazy.eval(self.expr, values)
            error = hazy.eval(self.finalExpr, values)
            self.ui.result.setText(str(value) + "+-" + str(error))
        except:
            e = sys.exc_info()[0]
            print(traceback.format_exc())
            self.dialog.showMessage("Cannot eval!\n" + traceback.format_exc())

    def getData(self):
        data = {}

        expr = {"format": self.ui.typeBox.currentText().lower(), "value": self.ui.input.toPlainText()}
        data["expr"] = expr
        data["symbols"] = self.ui.symInput.text().split(",")

        return data

    def getValues(self):
        values = {}

        for i in range(self.model.rowCount()):
            symbol = self.model.item(i, 0)
            value = self.model.item(i, 1)
            error = self.model.item(i, 2)

            if symbol is not None and value is not None:
                values[symbol.text()] = value.text()
            if symbol is not None and error is not None:
                values["u_" + symbol.text()] = error.text()

        return values


def start():
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    start()
