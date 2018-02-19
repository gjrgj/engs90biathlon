import gui
import sys
import datetime
from graph import simple_graph
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QTimer


if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)

    def time_show():
        now = datetime.datetime.now()
        master.Time.setText(now.strftime("%H" + ":" + "%M" + ":" + "%S"))

        if ((now.strftime("%S")) == ("05")):
            master.update_buffer_minute()

    gui_master = gui.QtGui.QTabWidget()
    master = gui.Ui_Izbira()
    master.setupUi(gui_master)

    # Buttons
    master.pushButton_Graph.clicked.connect(simple_graph)

    # Timer - Trigers updating of time label every second
    timer = QTimer()
    timer.timeout.connect(time_show)
    timer.start(1000)

    gui_master.show()
    sys.exit(app.exec_())