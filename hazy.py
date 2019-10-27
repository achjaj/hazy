#!/usr/bin/python

import libhazy as hazy
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from pathlib import Path
import traceback
from multiprocessing import Pool, cpu_count
from sympy import simplify as simplifyExpr


def simJob(expr):
    return simplifyExpr(expr)


class ExprView(QFrame):
    def __init__(self, parent, prompt, compute):
        super(ExprView, self).__init__(parent)
        self.stacked = QStackedWidget()
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.stacked)
        self.setLayout(mainLayout)

        self.compute = compute

        first = QWidget()
        self.stacked.addWidget(first)
        layout = QVBoxLayout()
        first.setLayout(layout)

        self.button = QPushButton("Save")
        self.button.clicked.connect(self.save)
        self.button.setEnabled(False)

        self.simButton = QPushButton("Simplify")
        self.simButton.clicked.connect(self.simplify)
        self.simButton.setEnabled(False)

        self.label = QLabel(prompt)
        area = QScrollArea()
        area.setBackgroundRole(QPalette.Dark)
        area.setWidget(self.label)
        area.setWidgetResizable(True)

        layout.addWidget(area)
        layout.addWidget(self.button)
        layout.addWidget(self.simButton)

        self.setFrameStyle(6)
        self.dialog = QErrorMessage()

        indicator = QProgressBar()
        indicator.setRange(0, 0)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancel)
        waitLayout = QVBoxLayout()
        waitLayout.addWidget(indicator)
        waitLayout.addWidget(cancel)

        second = QWidget()
        second.setLayout(waitLayout)
        self.stacked.addWidget(second)

    def showExpression(self, expr):
        tempFile = QTemporaryFile("hazy-")
        if tempFile.open():
            try:
                tempFile.close()
                self.current = expr
                hazy.saveToImg(tempFile.fileName(), expr)
                picture = QPixmap(tempFile.fileName())
                self.label.setPixmap(picture)
                self.button.setEnabled(True)
                self.simButton.setEnabled(True)
            except:
                e = sys.exc_info()[0]
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
        self.stacked.setCurrentIndex(0)
        self.compute.setEnabled(True)
        self.showExpression(result)

    def simplify(self):
        msgBox = QMessageBox()
        msgBox.setText("WARNING! This operation can be very slow!")
        msgBox.setInformativeText("Continue?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec()

        if ret == QMessageBox.Yes:
            self.stacked.setCurrentIndex(1)
            self.compute.setEnabled(False)
            self.pool = Pool(processes=cpu_count() - 1)
            self.pool.apply_async(simJob, (self.current,), callback=self.poolCallback)

    def cancel(self):
        self.pool.terminate()
        self.pool.join()
        self.stacked.setCurrentIndex(0)
        self.compute.setEnabled(True)


class Window(QMainWindow):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle("Hazy")
        main = QSplitter(self)
        self.setCentralWidget(main)

        self.model = QStandardItemModel(1, 3)
        self.model.setHorizontalHeaderLabels(["Symbol", "Value", "Error"])

        self.values = QTableView()
        self.values.setModel(self.model)
        self.values.setContextMenuPolicy(Qt.CustomContextMenu)
        self.values.customContextMenuRequested.connect(self.menu)

        upholder, downholder = self.construct_left()
        leftholder = QSplitter()
        leftholder.setOrientation(Qt.Vertical)
        leftholder.addWidget(upholder)
        leftholder.addWidget(downholder)

        main.addWidget(leftholder)
        main.addWidget(self.values)
        self.setMinimumSize(800, 600)
        self.dialog = QErrorMessage()

    def addRow(self):
        self.model.appendRow([])

    def removeRow(self):
        index = QInputDialog.getInt(self, "Set row index", "Row index:", 1, 1, self.model.rowCount())
        if index[1]:
            self.model.takeRow(index[0] - 1)

    def menu(self, pos):
        menu = QMenu()

        addAction = menu.addAction("Add row")
        removeAction = menu.addAction("Remove row")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == addAction:
            self.addRow()
        elif action == removeAction:
            self.removeRow()

    def construct_left(self):
        vlayout = QVBoxLayout()

        self.typeBox = QComboBox()
        self.typeBox.addItems(["text", "LaTex"])

        self.input = QTextEdit()
        self.input.setPlaceholderText("Input expression")

        inlayout = QHBoxLayout()
        inlayout.addWidget(self.typeBox)
        inlayout.addWidget(self.input)
        inholder = QWidget()
        inholder.setLayout(inlayout)

        self.symInput = QLineEdit()
        self.symInput.setPlaceholderText("Comma separated vyriables")
        vlayout.addWidget(self.symInput)

        self.cmpButton = QPushButton("Compute")
        self.cmpButton.clicked.connect(self.compute)

        self.evalButton = QPushButton("Eval")
        self.evalButton.clicked.connect(self.eval)

        blayout = QHBoxLayout()
        blayout.addWidget(self.cmpButton)
        blayout.addWidget(self.evalButton)
        vlayout.addLayout(blayout)

        self.resLabel = QLabel("Numerical result: <no data>")
        vlayout.addWidget(self.resLabel)

        self.preview = ExprView(self, "Input preview", self.cmpButton)

        self.final = ExprView(self, "Final expression", self.cmpButton)

        exprlayout = QHBoxLayout()
        exprlayout.addWidget(self.preview)
        exprlayout.addWidget(self.final)
        vlayout.addLayout(exprlayout)

        downholder = QWidget()
        downholder.setLayout(vlayout)

        return inholder, downholder

    def cmpTest(self):
        if self.input.toPlainText() == "":
            self.dialog.showMessage("Input expression is empty!")
            return False
        if self.symInput.text() == "":
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
            self.preview.showExpression(self.expr)
            self.final.showExpression(self.finalExpr)
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
            self.resLabel.setText("Numerical result: " + str(value) + "+-" + str(error))
        except:
            e = sys.exc_info()[0]
            print(traceback.format_exc())
            self.dialog.showMessage("Cannot eval!\n" + traceback.format_exc())

    def getData(self):
        data = {}

        expr = {"format": self.typeBox.currentText().lower(), "value": self.input.toPlainText()}
        data["expr"] = expr
        data["symbols"] = self.symInput.text().split(",")

        return data

    def getValues(self):
        values = {}

        for i in range(self.model.rowCount()):
            symbol = self.model.item(i, 0)
            value = self.model.item(i, 1)
            error = self.model.item(i, 2)

            if symbol is not None and value is not None:
                values[symbol.text()] = float(value.text())
            if symbol is not None and error is not None:
                values["u_" + symbol.text()] = float(error.text())

        return values


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
