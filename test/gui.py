# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'test.ui'
#
# Created: Sun Apr  9 08:44:41 2017
#      by: PyQt4 UI code generator 4.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui
from Buffer_script import Buffer_Time_minute, Buffer_Zg
from graph import OUT_Buffer_Time_minute, OUT_Buffer_Zg


time_190 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]   # year, month, day, hour, minuttes, seconds, week_day, up_6_7, up, down
temp_160 = [0, 0, 0, 0, 0, 0, 0, 0, 0]      # zg, sp, bo, so, pe, zu, szg, ssp, out

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Izbira(object):
    def setupUi(self, Izbira):
        Izbira.setObjectName(_fromUtf8("Izbira"))
        Izbira.resize(530, 363)
        Izbira.setWindowTitle(_fromUtf8(""))
        self.Mainpage = QtGui.QWidget()
        self.Mainpage.setObjectName(_fromUtf8("Mainpage"))
        self.Time = QtGui.QLineEdit(self.Mainpage)
        self.Time.setGeometry(QtCore.QRect(130, 70, 261, 71))
        font = QtGui.QFont()
        font.setPointSize(47)
        font.setBold(False)
        font.setItalic(True)
        font.setWeight(50)
        self.Time.setFont(font)
        self.Time.setObjectName(_fromUtf8("Time"))
        self.pushButton_Graph = QtGui.QPushButton(self.Mainpage)
        self.pushButton_Graph.setGeometry(QtCore.QRect(130, 200, 261, 31))
        self.pushButton_Graph.setObjectName(_fromUtf8("pushButton_Graph"))
        Izbira.addTab(self.Mainpage, _fromUtf8(""))

        self.retranslateUi(Izbira)
        Izbira.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Izbira)

    def retranslateUi(self, Izbira):
        self.pushButton_Graph.setText(_translate("Izbira", "Graph", None))
        Izbira.setTabText(Izbira.indexOf(self.Mainpage), _translate("Izbira", "Main page", None))

    def update_buffer_minute(self):
        global time_190
        a = time_190[4]
        Buffer_Time_minute(a, OUT_Buffer_Time_minute)
        b = 11
        Buffer_Zg(b, OUT_Buffer_Zg)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Izbira = QtGui.QTabWidget()
    ui = Ui_Izbira()
    ui.setupUi(Izbira)
    Izbira.show()
    sys.exit(app.exec_())