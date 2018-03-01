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
import math
from datetime import datetime, timedelta
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
global client

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
global saved_frame, file_out, video_ready
video_ready = False

# cs file writing
import csv

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

# foldername will be updated with each press of the Capture button
global folderName, fileName, filePointer, fileWriter, isLogging, startTime
isLogging = False

# multithreading
global wp


# set adc values as globals
# these are lists that have each new value appended to them
global adc_value1, adc_value2, adc_value1_temp, adc_value2_temp, ptr, dataReceivedFromPi
adc_value1 = [0]
adc_value2 = [0]
adc_value1_temp = 0
adc_value2_temp = 0
dataReceivedFromPi = False
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

# helper class to parse data coming from Pi, deal with disjoint network data transfer
def RepresentsFloat(s):
    try: 
        float(s)
        return True
    except ValueError:
        return False

# connect to pi
def connectPi():
	global adc_value1, adc_value2, adc_value1_temp, adc_value2_temp, ptr, run_started, client, wifi, fileWriter, filePointer, folderName, client, dataReceivedFromPi

	# setup logging
	paramiko.util.log_to_file('demo_simple.log')

	# check if the biathlon rifle is within range
	import objc

	objc.loadBundle('CoreWLAN',
				bundle_path = '/System/Library/Frameworks/CoreWLAN.framework',
				module_globals = globals())

	iface = CWInterface.interface()

	networks, error = iface.scanForNetworksWithName_error_('biathlon_rifle', None)

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
			while True:
				r, w, e = select.select([chan, sys.stdin], [], [])
				if chan in r:
					try:
						x = u(chan.recv(1024))
						if len(x) == 0:
							sys.stdout.write('\r\n*** EOF\r\n')
							break
						dataReceivedFromPi = True
						# save numbers once they start coming in, we assume both sensors are always connected
						# first check to see if both sensors are attached, then tdo a test to see if any of the arrived values
						# contain unexpected characters, if they do then ignore that line of input and process the next line input		
						
						# only one attached
						if len(x.split(' ')) == 3 and RepresentsFloat(x.split(' ')[1]):
							# check which one is attached
							if x[:3] == 'Ch1':    																		
								adc_value1_temp = math.sqrt(float(x.split(' ')[1]))
								adc_value2_temp = 0
							elif x[:3] == 'Ch2':
								adc_value1_temp = 0
								adc_value2_temp = float(x.split(' ')[1])				
							adc_value1.append(adc_value1_temp)
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')

						# both attached
						elif len(x.split(' ')) == 4 and RepresentsFloat(x.split(' ')[1]) and RepresentsFloat(x.split(' ')[3]):
							adc_value1_temp = math.sqrt(float(x.split(' ')[1]))
							adc_value2_temp = float(x.split(' ')[3])
							adc_value1.append(adc_value1_temp)
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')

						# parsing error in incoming data, skip it
						else:
							continue

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

# opens and writes to a CSV file
def writeToCSV():
	global fileWriter, folderName, isLogging, adc_value1_temp, adc_value2_temp, dataReceivedFromPi
	with open("stored_data/" + folderName + "/sensor_data.csv", "w+") as filePointer:
		fileWriter = csv.writer(filePointer, delimiter=',')
		# write column headers
		fileWriter.writerow(['Square Root of Hall Effect Sensor Voltage (V)', 'Force Sensor Voltage (V)', 'Time (seconds)'])
		# update startTime for csv logging
		startTime = datetime.now()
		# while capturing, write to file
		while isLogging:
    		# write data as soon as it arrives then wait for next data to arrive
			if dataReceivedFromPi:
				# get current time passed since start in seconds
				toSeconds = float((datetime.now() - startTime).total_seconds())
				fileWriter.writerow([adc_value1_temp, adc_value2_temp, str(toSeconds)])
				dataReceivedFromPi = False

def writeToVideoFile():
	global isLogging, saved_frame, file_out, video_ready
	# only log to file if capture is started
	while isLogging:
		if video_ready:
			file_out.write(saved_frame)
			video_ready = False
    
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

		# TEST CODE FOR SINGLE WINDOW GUI

		# # add a view to that widget
		# view = window.addViewBox() 

		# lock the aspect ratio so the pixels are always aqure (true to life scale)
		# view.setAspectLocked(True)

		# init graphs in view
		# Hall Effect sensor
		# sub1 = window.addLayout()
		# sub1.addLabel("Hall Effect Sensor Voltage vs Time")
		# sub1.nextRow()
		# v1 = sub1.addViewBox()
		# adc1 = pg.PlotDataItem(title="Hall Effect Sensor Voltage vs Time", 
		# 	labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})
		# v1.addItem(adc1)

		# # Force sensor
		# sub2 = window.addLayout()
		# sub2.addLabel("Force Sensor Voltage vs Time")
		# sub2.nextRow()
		# v2 = sub2.addViewBox()
		# v2.setMouseMode(v2.RectMode)
		# adc2 = pg.PlotDataItem(title="Force Sensor Voltage vs Time",
		# 	labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})
		# v2.addItem(adc2)

		# window.nextRow()

		# # Laser tracking display
		# sub3 = window.addLayout()
		# sub3.addLabel("Laser Tracking Display")
		# sub3.nextRow()
		# v3 = sub3.addViewBox()
		# v3.setMouseMode(v3.RectMode)
		# laser_img = pg.ImageItem(border='w')
		# v3.addItem(laser_img)

		adc1 = window.addPlot(row=0,col=0,title="Hall Effect Sensor Voltage vs Time", 
			labels={'left': 'Square Root of Voltage (V)', 'bottom': 'Time (seconds)'})
		
		adc2 = window.addPlot(row=0,col=1,title="Force Sensor Voltage vs Time",
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})


		# antialiasing for better plots
		pg.setConfigOptions(antialias=True)

		# set downsampling and clipping to reduce drawing load
		# adc1.setDownsampling(method='peak')
		# adc2.setDownsampling(method='peak')
		adc1.setDownsampling(mode='peak')
		adc2.setDownsampling(mode='peak')
		adc1.setClipToView(True)
		adc2.setClipToView(True)
		# set axis parameters
		adc1.setRange(xRange=[-100, 10], yRange=[math.sqrt(2.5),math.sqrt(5)])
		adc1.setLimits(xMax=10, yMax=5, yMin=-1)
		adc2.setRange(xRange=[-100, 10], yRange=[-1,5])
		adc2.setLimits(xMax=10, yMax=5, yMin=-1)

		# adc1.dataBounds(0,[-100, 10])
		# adc1.dataBounds(1, [-1,5])
		# adc2.dataBounds(0,[-100, 10])
		# adc1.SetXRange(-100, 10)
		# adc1.SetYRange(-1,5)
		# adc2.SetXRange(-100, 10)
		# adc2.SetYRange(-1,5)
		# adc2.dataBounds(1, [-1,5])

		# init curves
		# curve1 = adc1.curve
		# curve2 = adc2.curve
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
	os._exit(1)

# used to capture video stream
class QtCapture(QtGui.QWidget):
	def __init__(self, *args):
		global isLogging
		super(QtGui.QWidget, self).__init__()

		self.cap = cv2.VideoCapture(*args)
		# set camera resolution to 1280x720 to allow us to take 60 fps video, 640x480 can be used for 120 fps and 1920x1080 can be used for 30 fps.
		# set fps as well
		self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
		self.cap.set(cv2.CAP_PROP_FPS, 60)
		self.fps = self.cap.get(cv2.CAP_PROP_FPS)

		# save height and width for easy access
		self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
		self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
		self.out = 0
		self.video_frame = QtGui.QLabel()
		lay = QtGui.QVBoxLayout()

		lay.addWidget(self.video_frame)
		self.setLayout(lay)

		# turn file logging on or off
		isLogging = False
		print("resolution = " + str(self.width) + "x" + str(self.height))
		print("fps = " + str(self.fps))


	def setFPS(self, fps):
		self.fps = fps

	def nextFrameSlot(self):
		global isLogging, saved_frame, video_ready
		ret, frame = self.cap.read()
		frame = laser_tracking_overlay(ret, frame, self.height, self.width)
		video_ready = True
		saved_frame = frame
		# convert frame colors for proper display
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		# resize frame to smaller size for ease of display
		frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5) 	
		img = QtGui.QImage(frame, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap.fromImage(img)
		self.video_frame.setPixmap(pix)

	def start(self):
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.nextFrameSlot)
		self.timer.start(1000./self.fps)

	def stop(self):
		self.timer.stop()

	def deleteLater(self):
		self.cap.release()
		super(QtGui.QWidget, self).deleteLater()

# laser tracking
def laser_tracking_overlay(ret, frame, width, height):
	# the nitty-gritty math is abstracted away in the ProcessFrame() class
	pf = ProcessFrame()
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
		return frame

class VideoWindow(QtWidgets.QWidget):
	def __init__(self):
		QtWidgets.QWidget.__init__(self)
		self.setWindowTitle('Control Panel')

		self.capture = 0
		self.start_button = QtGui.QPushButton('Start Data Capture',self)
		self.start_button.clicked.connect(self.startCapture)

		self.end_button = QtGui.QPushButton('End Data Capture',self)
		self.end_button.clicked.connect(self.endCapture)

		self.exit_button = QtGui.QPushButton('Exit Program',self)
		self.exit_button.clicked.connect(self.exitProgram)

		vbox = QtGui.QVBoxLayout(self)
		vbox.addWidget(self.start_button)
		vbox.addWidget(self.end_button)
		vbox.addWidget(self.exit_button)

		self.setLayout(vbox)
		self.setGeometry(100,100,200,200)
		self.show()

		# start video stream
		if not self.capture:
			self.capture = QtCapture(0)
			self.exit_button.clicked.connect(self.capture.stop)
			# self.capture.setFPS(1)
			self.capture.setParent(self)
			self.capture.setWindowFlags(QtCore.Qt.Tool)
		self.capture.start()
		self.capture.show()

	# start capture does the following:
	# 1) Generates a folder according to the timestamp that the button was clicked
	# 2) Opens a .csv file that immediately begins logging data from the Pi (that is already coming in)
	# 3) Opens a .avi file that immediately begins writing frames from the attached camera (that are already coming in)
	def startCapture(self):
		global folderName, startTime, isLogging, wp, file_out
		# only runs if not currently capturing
		if not isLogging:
			startTime = datetime.now()
			# create folder
			folderName = round_seconds(str(startTime))
			if not os.path.exists("stored_data/" + folderName):
				os.makedirs("stored_data/" + folderName)
			isLogging = True
			# multithread csv writing
			csvWorker = Worker(writeToCSV)
			wp.threadpool.start(csvWorker)
			# set up video writer and activate it, also multithread
			self.capture.out = cv2.VideoWriter("stored_data/" + folderName + "/laser_data.mp4", cv2.VideoWriter_fourcc((*'mp4v')), self.capture.fps, (int(self.capture.width),int(self.capture.height)))	
			file_out = self.capture.out
			videoWorker = Worker(writeToVideoFile)
			wp.threadpool.start(videoWorker)
		
	def endCapture(self):
		global isLogging
		isLogging = False
		self.capture.out = 0
	
	# exit program and handle closing all resources
	def exitProgram(self):
		if isLogging:
			self.capture.close()
			self.capture.deleteLater()
		client.close()
		qApp.exit();

def main():
	global adc_value1, adc_value2, app, wp

	# set up QT
	app = QtGui.QApplication(sys.argv)
	# get current time to the microsecond, this will be used for syncing with pi
	startTime = datetime.now()
	# set up threadpool and begin connection to pi
	wp = WorkerPool()
	dataWorker = Worker(connectPi)
	wp.threadpool.start(dataWorker)
	# init graphics
	mainwindow = MainWindow()
	video = VideoWindow()
	# init qt event loop
	sys.exit(mainwindow.beginGraphics())

if __name__ == '__main__':
	main()

