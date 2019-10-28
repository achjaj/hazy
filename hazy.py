#!/usr/bin/python

import libhazy as hazy
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from pathlib import Path
import traceback
from multiprocessing import Pool, cpu_count
from sympy import simplify as simplifyExpr

def simJob(expr):
    return simplifyExpr(expr)


class ExprView(QStackedWidget):
    def __init__(self, parent):
        super(ExprView, self).__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load("exprview.ui", self)
        self.ui.saveButton.clicked.connect(self.save)
        self.ui.simplifyButton.clicked.connect(self.simplify)
        self.ui.cancelButton.clicked.connect(self.cancel)

        self.imageScene = QGraphicsScene()
        self.ui.imageView.setScene(self.imageScene)
        self.dialog = QErrorMessage()

    def showExpression(self, expr):
        tempFile = QTemporaryFile("hazy-")
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
        fileName = QFileDialog.getSaveFileName(self, "Save expression", str(Path.home()),
                                               "LaTex (*.tex);;PNG image (*.png)")
        try:
            if fileName[0] != "":
                if fileName[1] == "LaTex (*.tex)":
                    hazy.saveToLaTex(fileName[0] + ".tex", self.current)
                else:
                    hazy.saveToImg(fileName[0] + ".png", self.current)
        except:
            e = sys.exc_info()[0]
            print(traceback.format_exc())
            self.dialog.showMessage("Cannot export expression!\n" + traceback.format_exc())

    def poolCallback(self, result):
        self.setCurrentIndex(0)
        #self.compute.setEnabled(True)
        self.showExpression(result)

    def simplify(self):
        msgBox = QMessageBox()
        msgBox.setText("WARNING! This operation can be very slow!")
        msgBox.setInformativeText("Continue?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec()

        if ret == QMessageBox.Yes:
            self.setCurrentIndex(1)
            #self.compute.setEnabled(False)
            self.pool = Pool(processes=cpu_count() - 1)
            self.pool.apply_async(simJob, (self.current,), callback=self.poolCallback)

    def cancel(self):
        self.pool.terminate()
        self.pool.join()
        self.setCurrentIndex(0)
        self.compute.setEnabled(True)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())
