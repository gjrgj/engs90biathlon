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
from paramiko.py3compat import input
from paramiko.py3compat import u

# paramiko for ssh
import select
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

# csv and video file writing
import csv
from Queue import Queue
global frame_queue
frame_queue = Queue()

# rounds time to seconds
def round_seconds(dt):
    result = []
    date = dt.split()[0]
    h, m, s = [dt.split()[1].split(':')[0],
               dt.split()[1].split(':')[1],
               str(round(float(dt.split()[1].split(':')[-1])))]
    result = (date + ' ' + h + '.' + m + '.' + s)
    return result

# file loading globals
global csvToLoad, videoToLoad, isLoading, adc_value1_loaded, adc_value2_loaded, timestamps_loaded, ptr_load
adc_value1_loaded = [0]
adc_value2_loaded = [0]
timestamps_loaded = [0]
isLoading = False

# video
global video

# foldername will be updated with each press of the Capture button
global folderName, fileName, filePointer, fileWriter, isLogging, startTime
isLogging = False

# multithreading
global wp

# set adc values as globals
# these are lists that have each new value appended to them
global adc_value1, adc_value2, adc_value1_temp, adc_value2_temp, ptr, dataReceivedFromPi, timestamps, currentTime, connectionStartTime
adc_value1 = [0]
adc_value2 = [0]
timestamps = [0]
adc_value1_temp = 0
adc_value2_temp = 0
dataReceivedFromPi = False
ptr = 0

# worker class for multithreading
class Worker(QRunnable):
	def __init__(self, fn, *args, **kwargs):
		super(Worker, self).__init__()
		self.fn = fn
		self.args = args
		self.kwargs = kwargs

	@pyqtSlot()
	def run(self):
		# Initialise the runner function with passed self.args, self.kwargs.
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
	global adc_value1, adc_value2, adc_value1_temp, adc_value2_temp, ptr, client, client, dataReceivedFromPi, currentTime, timestamps, connectionStartTime
	# setup logging
	# paramiko.util.log_to_file('demo_simple.log')

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
	
	# check if we are currently connected to rifle, if not then try to connect to it, if any error then quit the program
	while 1:
		try:
			current_network = os.popen("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print substr($0, index($0, $2))}'")
			if current_network.readline() == 'biathlon_rifle\n':
				break	
			else:
				os.popen("networksetup -setairportnetwork en0 biathlon_rifle biathlon")
				time.sleep(2)
		except Exception as e:
			print('*** Caught exception: %s: %s' % (e.__class__, e))
			print('Unable to connnect to rifle')
			sys.exit(1)
	print('Successfully connected to rifle!')		
	
	# Paramiko client configuration
	UseGSSAPI = paramiko.GSS_AUTH_AVAILABLE             # enable "gssapi-with-mic" authentication, if supported by your python installation
	DoGSSAPIKeyExchange = paramiko.GSS_AUTH_AVAILABLE   # enable "gssapi-kex" key exchange, if supported by your python installation

	# now, connect and use paramiko Client to negotiate SSH2 across the connection
	try:
		# set username, pass, hostname, and port to negotiate successful connection
		# note that due to the manual DHCP server config on the Pi, its address on the network will always default to 192.168.4.1
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
		# boot Shell on pi to run scripts
		chan = client.invoke_shell()
		print('*** Successfully started ssh!')
		oldtty = termios.tcgetattr(sys.stdin)
		try:
			tty.setraw(sys.stdin.fileno())
			tty.setcbreak(sys.stdin.fileno())
			chan.settimeout(0.0)
			# send command to Pi to trigger data collection and gather the results through ssh
			chan.send('python ~/biathlon/readvoltage.py\n')
			connectionStartTime = datetime.now()
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
							currentTime = datetime.now()
							timestamps.append(float((currentTime - connectionStartTime).total_seconds()))
							if isLogging:
								writeToCSV()

						# both attached
						elif len(x.split(' ')) == 4 and RepresentsFloat(x.split(' ')[1]) and RepresentsFloat(x.split(' ')[3]):
							adc_value1_temp = math.sqrt(float(x.split(' ')[1]))
							adc_value2_temp = float(x.split(' ')[3])
							adc_value1.append(adc_value1_temp)
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')
							currentTime = datetime.now()							
							timestamps.append(float((currentTime - connectionStartTime).total_seconds()))
							if isLogging:
								writeToCSV()

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
	global fileWriter, folderName, isLogging, adc_value1_temp, adc_value2_temp, dataReceivedFromPi, currentTime, filePointer, startTime
	with open("stored_data/" + folderName + "/sensor_data.csv", "a") as filePointer:
		# get current time passed since start in seconds
		toSeconds = float((datetime.now() - startTime).total_seconds())
		# write values to 4 decimal points
		csv.writer(filePointer, delimiter=',').writerow(["{0:.4f}".format(adc_value1_temp), "{0:.4f}".format(adc_value2_temp), "{0:.4f}".format(toSeconds)])


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

		adc1 = window.addPlot(row=0,col=0,title="Hall Effect Sensor Voltage vs Time", 
			labels={'left': 'Square Root of Voltage (V)', 'bottom': 'Time (seconds)'})
		adc2 = window.addPlot(row=0,col=1,title="Force Sensor Voltage vs Time",
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})

		# antialiasing for better plots
		pg.setConfigOptions(antialias=True)

		# set downsampling and clipping to reduce drawing load
		adc1.setDownsampling(mode='peak')
		adc2.setDownsampling(mode='peak')
		adc1.setClipToView(True)
		adc2.setClipToView(True)

		# set axis parameters
		# adc1.setRange(xRange=[-100, 10], yRange=[math.sqrt(3),math.sqrt(3.7)])
		adc1.setRange(xRange=[-10, 1], yRange=[-1,5])
		adc1.setLimits(xMax=10, xMin=-15, yMax=5, yMin=-1)
		adc2.setRange(xRange=[-10, 1], yRange=[-1,5])
		adc2.setLimits(xMax=10, xMin=-15, yMax=5, yMin=-1)
		# makes color of both pens yellow
		curve1 = adc1.plot(pen='y')
		curve2 = adc2.plot(pen='y')

	def beginGraphics(self):
		global app, adc1, adc2, curve1, curve2, ptr, window, timestamps, isLoading, adc_value1_loaded, adc_value2_loaded, timestamps_loaded, ptr_load

		# updates plots in real-time and keeps the most recent values the focus
		def update():
    		# check if loading or displaying realtime data, then set curve data accordingly
			if isLoading:
				curve1.setData(timestamps_loaded[:ptr_load], adc_value1_loaded[:ptr_load])
				curve1.setPos(-timestamps_loaded[ptr_load-1], 0)
				curve2.setData(timestamps_loaded[:ptr_load], adc_value2_loaded[:ptr_load])
				curve2.setPos(-timestamps_loaded[ptr_load-1], 0)
			else:
				curve1.setData(timestamps[:ptr], adc_value1[:ptr])
				curve1.setPos(-timestamps[ptr-1], 0)
				curve2.setData(timestamps[:ptr], adc_value2[:ptr])
				curve2.setPos(-timestamps[ptr-1], 0)

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


# used to capture video stream
class QtCapture(QtGui.QWidget):
	def __init__(self, *args):
		global isLogging
		super(QtGui.QWidget, self).__init__()
		self.cap = cv2.VideoCapture(*args)
		self.capLoaded = 0
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

	def displayNextFrame(self):
		global isLogging, frame_queue, isLoading
		# display frame either from live usb camera or loaded file depending on current mode
		if not isLoading:
			ret, frame = self.cap.read()
			frame = laser_tracking_overlay(ret, frame, self.height, self.width)
		else:
			ret, frame = self.capLoaded.read()
		if isLogging:
			# add frame to queue to be written
			frame_queue.put(frame)
			# draw recording symbol on video feed to show it's capturing
			cv2.circle(frame,(int(self.width - 60), int(60)), 30, (0, 0, 255), -1)
			cv2.putText(frame, 'REC', (int(self.width - 165), int(70)), cv2.FONT_HERSHEY_PLAIN, 2,(0,0,0), 4, lineType=8)
		if not isLogging and frame_queue.empty == False:
			cv2.putText(frame, 'PROCESSING FRAMES', (int(self.width/30), int(self.height/2)), cv2.FONT_HERSHEY_PLAIN, 7,(0,0,0), 7, lineType=8)
			cv2.putText(frame, 'PLEASE WAIT', (int(23*self.width/100), int(2 * self.height/3)), cv2.FONT_HERSHEY_PLAIN, 7,(0,0,0), 8, lineType=8)
		# resize frame to smaller size for ease of display
		frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5) 
		# convert frame colors for proper display
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)	
		img = QtGui.QImage(frame, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap.fromImage(img)
		self.video_frame.setPixmap(pix)

	def start(self):
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.displayNextFrame)
		self.timer.start(1000./self.fps)

	def stop(self):
		self.timer.stop()

	def deleteLater(self):
		self.cap.release()
		super(QtGui.QWidget, self).deleteLater()


# utilize a queue/buffer to separate video file writing from the main thread so it doesn't block anything
def videoFileWriting():
	global frame_queue, isLogging, video, isLogging
	# only save frame if logging
	while frame_queue.empty() == False:
		video.capture.out.write(frame_queue.get())
		time.sleep(1/video.capture.fps)

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

# control panel 
class VideoWindow(QtWidgets.QWidget):
	def __init__(self):
		QtWidgets.QWidget.__init__(self)
		self.setWindowTitle('Control Panel')

		self.capture = 0
		self.start_button = QtGui.QPushButton('Start Data Capture',self)
		self.start_button.clicked.connect(self.startCapture)

		self.end_button = QtGui.QPushButton('End Data Capture',self)
		self.end_button.clicked.connect(self.endCapture)

		self.load_button = QtGui.QPushButton('Load and Replay Data',self)
		self.load_button.clicked.connect(self.loadCapture)

		self.exit_button = QtGui.QPushButton('Exit Program',self)
		self.exit_button.clicked.connect(self.exitProgram)

		vbox = QtGui.QVBoxLayout(self)
		vbox.addWidget(self.start_button)
		vbox.addWidget(self.end_button)
		vbox.addWidget(self.load_button)
		vbox.addWidget(self.exit_button)

		self.setLayout(vbox)
		self.setGeometry(100,100,200,200)
		self.show()

		# start video stream
		if not self.capture:
			self.capture = QtCapture(0)
			self.exit_button.clicked.connect(self.capture.stop)
			self.capture.setParent(self)
			self.capture.setWindowFlags(QtCore.Qt.Tool)
		self.capture.start()
		self.capture.show()


	# start capture does the following:
	# 1) Generates a folder according to the timestamp that the button was clicked
	# 2) Opens a .csv file that immediately begins logging data from the Pi (that is already coming in)
	# 3) Opens a .avi file that immediately begins writing frames from the attached camera (that are already coming in)
	def startCapture(self):
		global folderName, startTime, isLogging, wp, fileWriter, frame_queue
		# reset the contents of frame_queue
		frame_queue = Queue()
		# only runs if not currently capturing
		if not isLogging and not isLoading:
			startTime = datetime.now()
			# create folder
			folderName = round_seconds(str(startTime))
			if not os.path.exists("stored_data/" + folderName):
				os.makedirs("stored_data/" + folderName)
			isLogging = True
			# write to CSV file, column headers first
			with open("stored_data/" + folderName + "/sensor_data.csv", "w+") as filePointer:
				csv.writer(filePointer, delimiter=',').writerow(['Square Root of Hall Effect Sensor Voltage (V)', 'Force Sensor Voltage (V)', 'Time (seconds)'])
			# set up video writer
			self.capture.out = cv2.VideoWriter("stored_data/" + folderName + "/laser_data.avi", cv2.VideoWriter_fourcc((*'XVID')), self.capture.fps, (int(self.capture.width),int(self.capture.height)))

	# end current capture and set logging to false
	def endCapture(self):
		global isLogging, isLoading, wp
		# write all frames to file first, turn off logging too
		isLogging = False
		videoWorker = Worker(videoFileWriting)
		wp.threadpool.start(videoWorker)	

	# can only load data if not logging, so if this is pressed will end current logging and load from disk
	def loadCapture(self):
		global adc_value1_loaded, adc_value2_loaded, timestamps_loaded, ptr_load, wp
    	# end current capture if there is one happening
		if isLogging == True:
			self.endCapture()
		# reset loading vars
		adc_value1_loaded = [0]
		adc_value2_loaded = [0]
		timestamps_loaded = [0]
		ptr_load = 0

		loadedDataDir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
		isLoading = True
		# load video file and begin displaying
		self.capture.capLoaded = cv2.VideoCapture(loadedDataDir + "/laser_data.avi")
		# load csv file and begin graphing, after loading each value, sleep for as long as the read timestamp to simulate a real run
		with open(loadedDataDir + "/sensor_data.csv", 'rt', encoding='utf8') as csvfile:
			sensor_data = csv.reader(csvfile, delimiter=',')
			# iterate through all rows but skip header
			next(sensor_data,None)
			for row in sensor_data:
    			# parse each row and pull data out, append to data lists at same rate as it came in
				adc_value1_loaded.append(float(row[0]))
				adc_value2_loaded.append(float(row[1]))
				timestamps_loaded.append(float(row[2]))
				ptr_load += 1
				time.sleep(abs(timestamps_loaded[ptr_load-2]-timestamps_loaded[ptr_load-1]))
				# check if still loading, if it has been overridden by user then close file
				if not isLoading:
					break
		isLoading = False
				
	# exit program and handle closing all resources
	def exitProgram(self):
		global isLogging, isLoading
		if isLogging or isLoading:
			isLoading = False
			isLogging = False
			self.capture.close()
			self.capture.deleteLater()
		client.close()
		qApp.exit();


def main():
	global adc_value1, adc_value2, app, wp, video
	# set up QT
	app = QtGui.QApplication(sys.argv)
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

