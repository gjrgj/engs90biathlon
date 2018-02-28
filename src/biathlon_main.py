#!/usr/bin/env python

# This file is inteded for the usage of the Thayer School of Engineering and the US Biathlon Team.
# Within is outlined a data collection interface that utilizes the Raspberry Pi and a couple of Python open-source libraries.
# Special thanks to the creators of paramiko and pyqtgraph, without them this project wouldn't have been possible.
#
# All code written by George Hito.
# Currently only functional on OSX.

import signal
import time
import base64
import getpass
import os
import socket
import sys
import traceback
import errno
from datetime import datetime
from timeout import timeout
from paramiko.py3compat import input
from paramiko.py3compat import u

# paramiko for ssh
import paramiko
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False

# plotting and GUI
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg
global curve1, curve2, app

# opencv for laser tracking
import cv2
from processframe import ProcessFrame
global video_out

# rounds time to seconds
def round_seconds(dt):
    result = []
    date = dt.split()[0]
    h, m, s = [dt.split()[1].split(':')[0],
               dt.split()[1].split(':')[1],
               str(round(float(dt.split()[1].split(':')[-1])))]
    result = (date + ' ' + h + '.' + m + '.' + s)
    return result

# csv file writing, store latest run and init with column headers
# for the filename, use the current datetime 
import csv
print("Using openCV version " + str(cv2.__version__))
global fileName, filePointer, fileWriter, folderName, csv_out
# check to see if 'stored_data' directory exists
if not os.path.exists("stored_data"):
    os.makedirs("stored_data")
	# set foldername for the run
folderName = round_seconds(str(datetime.now()))

# set adc values as globals
# these are lists that have each new value appended to them
global adc_value1, adc_value2, ptr
adc_value1 = [0]
adc_value2 = [0]
ptr = 0

# other globals for usage to start/stop actions in other threads
global run_started
run_started = False


# worker class for multithreading
class Worker(QRunnable):
	def __init__(self, fn, *args, **kwargs):
		super(Worker, self).__init__()
		self.fn = fn
		self.args = args
		self.kwargs = kwargs

	@pyqtSlot()
	def run(self):
		'''
		Initialise the runner function with passed self.args, self.kwargs.
		'''
		self.fn(*self.args, **self.kwargs)

# wrapper for threadpool
class WorkerPool():
	def __init__(self, *args, **kwargs):
		self.threadpool = QThreadPool()

# connect to pi
def connectPi():
	global adc_value1, adc_value2, ptr, run_started, client, wifi, fileWriter, filePointer, folderName

	# # first check if biathlon_rifle is current network
	# if "biathlon_rifle" in subprocess.check_output("iwgetid -r"):
	# 	print("Connected to rifle!")
	# else:
	# 	print("Please connect to the rifle.")
	# 	sys.exit(1)


	# setup logging
	paramiko.util.log_to_file('demo_simple.log')

	# check if the biathlon rifle is within range
	import objc

	objc.loadBundle('CoreWLAN',
				bundle_path = '/System/Library/Frameworks/CoreWLAN.framework',
				module_globals = globals())

	iface = CWInterface.interface()

	networks, error = iface.scanForNetworksWithName_error_('biathlon_rifle', None)
	
	# if no error, biathlon rifle is nearby
	# if str(error) == 'None':
	# 	print('Biathlon rifle is nearby.')
	# else:
	# 	print('Biathlon rifle is not nearby, please try and get closer to connect.')
	# 	sys.exit(2)

	# returns list of nearby networks
	network_list = os.popen("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport --scan | awk '{print $1}'")

	# is rifle nearby? initialize to false.
	rifle_nearby = False

	while 1:
		line = network_list.readline()
		if line == 'biathlon_rifle\n':
			rifle_nearby = True
		if not line: 
			break

	# if rifle is nearby, proceed
	if rifle_nearby == True:
		print('Biathlon rifle is nearby.')
	else:
		print('Biathlon rifle is not nearby, please try and get closer to connect.')
		sys.exit(2)


	network = networks.anyObject()

	# if not currently connected to rifle, try to connect to it
	# returns currently connected wifi network
	current_network = os.popen("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print substr($0, index($0, $2))}'")
	
	# check if we are currently connected to rifle, if not then try to connect to it
	connected_to_rifle = False
	while 1:
		line = current_network.readline()
		if line == 'biathlon_rifle\n':
			connected_to_rifle = True
		if not line: 
			break

	if connected_to_rifle == False:
		# if no error, successfully connected to rifle
		success, error = iface.associateToNetwork_password_error_(network, 'biathlon', None)
		if str(error) == 'None':
			print('Successfully connected to rifle!')
		else:
			print('Unable to connnect to rifle')
			sys.exit(2)
	else:
		print('Already connected to rifle!')
	


	# Paramiko client configuration
	UseGSSAPI = paramiko.GSS_AUTH_AVAILABLE             # enable "gssapi-with-mic" authentication, if supported by your python installation
	DoGSSAPIKeyExchange = paramiko.GSS_AUTH_AVAILABLE   # enable "gssapi-kex" key exchange, if supported by your python installation
	# UseGSSAPI = False
	# DoGSSAPIKeyExchange = False

	# adc_value initialized for two channels
	adc_value1_temp = 0
	adc_value2_temp = 0
	time = 0

	# now, connect and use paramiko Client to negotiate SSH2 across the connection
	try:
		# get hostname
		username = 'pi'
		password = 'biathlon'
		hostname = '192.168.4.1'
		port = 22
		
		client = paramiko.SSHClient()
		client.load_system_host_keys()
		client.set_missing_host_key_policy(paramiko.WarningPolicy())
		print('*** Starting ssh...')
		if not UseGSSAPI and not DoGSSAPIKeyExchange:
			client.connect(hostname, port, username, password)
		else:
			try:

				client.connect(hostname, port, username, gss_auth=UseGSSAPI,
					gss_kex=DoGSSAPIKeyExchange)
			except Exception:
				# traceback.print_exc()
				password = getpass.getpass('Password for %s@%s: ' % (username, hostname))
				client.connect(hostname, port, username, password)

		chan = client.invoke_shell()
		# print(repr(client.get_transport()))
		print('*** Successfully started ssh!')
		run_started = True

		# send relevant messages to start adc reading and print to terminal
		# in the future this will be synchronized with animated graph
		import select

		oldtty = termios.tcgetattr(sys.stdin)
		try:
			tty.setraw(sys.stdin.fileno())
			tty.setcbreak(sys.stdin.fileno())
			chan.settimeout(0.0)
			# send command to Pi to trigger data collection and gather the results through ssh
			chan.send('python ~/biathlon/demo_readvoltage.py\n')

			# generate folder for writing to from current time
			if not os.path.exists("stored_data/" + folderName):
				os.makedirs("stored_data/" + folderName)
			filePointer = open("stored_data/" + folderName + "/sensor_data.csv", "w+")
			fileWriter = csv.writer(filePointer, delimiter=',')
			fileWriter.writerow(['Hall Effect Sensor (V)', 'Force Sensor (V)'])
			while True:
				r, w, e = select.select([chan, sys.stdin], [], [])
				if chan in r:
					try:
						x = u(chan.recv(1024))
						if len(x) == 0:
							sys.stdout.write('\r\n*** EOF\r\n')
							break

						# save numbers once they start coming in, we assume both sensors are always connected
						# first check to see if both sensors are attached
						# only one attached
						if len(x.split(' ')) == 3:
							# check which one is attached
							if x[:3] == 'Ch1':
								adc_value1_temp = float(x.split(' ')[1])
								adc_value2_temp = 0
							elif x[:3] == 'Ch2':
								adc_value1_temp = 0
								adc_value2_temp = float(x.split(' ')[1])				
							adc_value1.append(adc_value1_temp)
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')
							fileWriter.writerow([adc_value1_temp, adc_value2_temp])

						# both attached
						elif len(x.split(' ')) == 4:
							adc_value1_temp = float(x.split(' ')[1])
							adc_value2_temp = float(x.split(' ')[3])
							adc_value1.append(adc_value1_temp)
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')
							fileWriter.writerow([adc_value1_temp, adc_value2_temp])

					except socket.timeout:
						pass
				if sys.stdin in r:
					x = sys.stdin.read(1)
					if len(x) == 0:
						break
					chan.send(x)
					chan.close()
					client.close()

		finally:
			termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
	except Exception as e:
		print('*** Caught exception: %s: %s' % (e.__class__, e))
		traceback.print_exc()
		try:
			client.close()
		except:
			pass
		sys.exit(1)

# main graphics window
class MainWindow(QMainWindow):
	global window
	keyPressed = QtCore.pyqtSignal()
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.initUI()

	def setFrame(self,frame):
		pixmap = QPixmap.fromImage(frame)
		self.label.setPixmap(pixmap)
	
	def initUI(self):
		global app, adc1, adc2, curve1, curve2, ptr, window, video

		# define a top-level widget to hold everything
		window = pg.GraphicsLayoutWidget()
		window.setWindowTitle('Biathlon Team Data Processing')

		# init graphs in widget
		adc1 = window.addPlot(row=0,col=0,title="Hall Effect Sensor Voltage vs Time", 
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'}, xRange=[-100, 10], yRange=[-1,2])
		adc2 = window.addPlot(row=0,col=1,title="Force Sensor Voltage vs Time",
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})

		# antialiasing for better plots
		pg.setConfigOptions(antialias=True)

		# set downsampling and clipping to reduce drawing load
		adc1.setDownsampling(mode='peak')
		adc2.setDownsampling(mode='peak')
		adc1.setClipToView(True)
		adc2.setClipToView(True)

		adc1.setRange(xRange=[-100, 10], yRange=[-1,5])
		adc1.setLimits(xMax=10, yMax=5, yMin=-1)
		adc2.setRange(xRange=[-100, 10], yRange=[-1,5])
		adc2.setLimits(xMax=10, yMax=5, yMin=-1)

		curve1 = adc1.plot(pen='y')
		curve2 = adc2.plot(pen='y')

	def beginGraphics(self):
		global app, adc1, adc2, curve1, curve2, ptr, window

		# updates plots in real-time and keeps the most recent values the focus
		def update():
			global curve1, curve2, adc_value1, adc_value2, ptr
			curve1.setData(adc_value1[:ptr])
			curve1.setPos(-ptr, 0)
			curve2.setData(adc_value2[:ptr])
			curve2.setPos(-ptr, 0)

		timer = QtCore.QTimer()
		timer.timeout.connect(update)
		timer.start(50)

		# Display the widget as a new window
		window.show()

		# start the QT event loop
		app.exec_()

	def keyPressEvent(self, event):
		self.keyPressed.emit()
		if event.key() == Qt.Key_Escape:
			self.close()

# handle ctrl+c elegantly
def sigint_handler(*args):
	"""Handler for the SIGINT signal."""
	sys.stderr.write('\r')

	QtGui.QApplication.quit()
	# os._exit(1)

# use openCV to track a laser in a video stream
class Capture():
	def __init__(self):
		self.capturing = False
		# CHANGE THIS TO SWITCH BETWEEN WEBCAM AND USB CAMERA
		self.cam = cv2.VideoCapture(1)
		if self.cam.isOpened() == False:
			print("No USB camera detected on computer. Defaulting to front-facing camera.")
			self.cam = cv2.VideoCapture(0)
		self.camw = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)
		self.camh = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
		
	def startCapture(self):
		global folderName
		print("pressed start")

		self.capturing = True
		# captures video and processes for laser point
		pf = ProcessFrame()
		cap = self.cam

		# set up file logging too
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter("stored_data/" + folderName + "/laser_data.mp4", fourcc, 20.0, (int(self.camw),int(self.camh)))	

		while(self.capturing):
			ret, frame = cap.read()

			if ret == True:
				# Find the laser
				center = pf.find_laser(frame)

				# Find the targets
				circles = pf.find_targets(frame)

				# check if found, if not then just display the regular frame, if so then overlay tracking
				if circles is not None and center is not None:
					# Draw circles
					circles = np.uint16(np.around(circles))
					for i in circles[0,:]:
						cv2.circle(frame,(i[0],i[1]),i[2],(0,255,0),2) # Draw the outer circle
						cv2.circle(frame,(i[0],i[1]),2,(0,0,255),3) # Draw the center

					# Draw laser
					cv2.circle(frame, center, 6, (0, 255, 0), -1)

				# display to user
				cv2.namedWindow('Frame',cv2.WINDOW_AUTOSIZE)
				frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5) 

				# write to file
				out.write(frame)

				cv2.imshow('Frame', frame)

				if cv2.waitKey(25) & 0xFF == ord('q'): # Exit by pressing Q
					break
		cv2.destroyAllWindows()

	def endCapture(self):
		print ("pressed End")
		self.capturing = False
		# cv2.destroyAllWindows()

	def quitCapture(self):
		print ("pressed Quit")
		cap = self.cam
		cv2.destroyAllWindows()
		cap.release()
		QtCore.QCoreApplication.quit()

class VideoWindow(QtWidgets.QWidget):
	def __init__(self):
		QtWidgets.QWidget.__init__(self)
		self.setWindowTitle('Control Panel')

		self.capture = Capture()
		self.start_button = QtGui.QPushButton('Start',self)
		self.start_button.clicked.connect(self.capture.startCapture)

		self.end_button = QtGui.QPushButton('End',self)
		self.end_button.clicked.connect(self.capture.endCapture)

		self.quit_button = QtGui.QPushButton('Quit',self)
		self.quit_button.clicked.connect(self.capture.quitCapture)

		vbox = QtGui.QVBoxLayout(self)
		vbox.addWidget(self.start_button)
		vbox.addWidget(self.end_button)
		vbox.addWidget(self.quit_button)

		self.setLayout(vbox)
		self.setGeometry(100,100,200,200)
		self.show()


def main():
	global adc_value1, adc_value2, app

	# set up QT
	app = QtGui.QApplication(sys.argv)

	# get current time to the microsecond, this will be used for syncing with pi
	startTime = datetime.now()

	# multithread graphics, video, and pi connections
	wp = WorkerPool()

	dataWorker = Worker(connectPi)
	wp.threadpool.start(dataWorker)

	mainwindow = MainWindow()
	video = VideoWindow()

	# handle ctrl+c
	signal.signal(signal.SIGINT, sigint_handler)
	timer = QTimer()
	timer.start(50)  # You may change this if you wish.
	timer.timeout.connect(lambda: None)  # Let the interpreter run each 50 ms.

	sys.exit(mainwindow.beginGraphics())


if __name__ == '__main__':
	import sys
	main()

