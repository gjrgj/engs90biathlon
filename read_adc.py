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
from timeout import timeout
from paramiko.py3compat import input
from paramiko.py3compat import u

import paramiko
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False

# plotting
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
global curve1, curve2, app

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

class WorkerPool():
	def __init__(self, *args, **kwargs):
		self.threadpool = QThreadPool()

def connectPi():
	global adc_value1, adc_value2, ptr, run_started, client, wifi

	# # first check if biathlon_rifle is current network
	# if "biathlon_rifle" in subprocess.check_output("iwgetid -r"):
	# 	print("Connected to rifle!")
	# else:
	# 	print("Please connect to the rifle.")
	# 	sys.exit(1)

	# get hostname
	username = 'pi'
	password = 'biathlon'
	hostname = '192.168.4.1'

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
	if str(error) == 'None':
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
	
	# # returns list of nearby networks
	# network_list = os.popen("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport --scan | awk '{print $1}'")

	# # is rifle nearby? initialize to false.
	# rifle_nearby = False

	# while 1:
	# 	line = network_list.readline()
	# 	if line == 'biathlon_rifle\n':
	# 		rifle_nearby = True
	# 	if not line: 
	# 		break

	# # if rifle is nearby, proceed
	# if rifle_nearby == True:
	# 	print('Biathlon rifle is nearby.')
	# else:
	# 	print('Biathlon rifle is not nearby, please try and get closer to connect.')
	# 	sys.exit(2)



	# Paramiko client configuration
	UseGSSAPI = paramiko.GSS_AUTH_AVAILABLE             # enable "gssapi-with-mic" authentication, if supported by your python installation
	DoGSSAPIKeyExchange = paramiko.GSS_AUTH_AVAILABLE   # enable "gssapi-kex" key exchange, if supported by your python installation
	# UseGSSAPI = False
	# DoGSSAPIKeyExchange = False
	port = 22

	# adc_value initialized for two channels
	adc_value1_temp = 0
	adc_value2_temp = 0
	time = 0

	# now, connect and use paramiko Client to negotiate SSH2 across the connection
	try:
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

						# save numbers once they start coming in, we assume both sensors are always connected
						# first check to see if both sensors are attached
						# zero attached
						# if len(x.split(' ')) == 2:
						# 	print('No sensors attached!')
						# only one attached
						if len(x.split(' ')) == 3:
							# check which one is attached
							if x[:3] == 'Ch1':
								adc_value1_temp = float(x.split(' ')[1])
								adc_value1.append(adc_value1_temp)
							elif x[:3] == 'Ch2':
								adc_value2_temp = float(x.split(' ')[1])
								adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')

						# both attached
						elif len(x.split(' ')) == 4:
							adc_value1_temp = float(x.split(' ')[1])
							adc_value1.append(adc_value1_temp)
							adc_value2_temp = float(x.split(' ')[3])
							adc_value2.append(adc_value2_temp)
							ptr += 1
							print(x + '\r')						

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

class MainWindow(QMainWindow):
	global window
	keyPressed = QtCore.pyqtSignal()
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.initUI()
	
	def initUI(self):
		global app, adc1, adc2, curve1, curve2, ptr, window

		# define a top-level widget to hold everything
		window = pg.GraphicsLayoutWidget()
		# create grid to manage widget size and position
		layout = QtGui.QGridLayout()
		window.setLayout(layout)

		# init graphs in widget
		adc1 = window.addPlot(row=0,col=0,title="Hall Effect Sensor Voltage vs Time", 
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})
		adc2 = window.addPlot(row=0,col=1,title="Force Sensor Voltage vs Time",
			labels={'left': 'Voltage (V)', 'bottom': 'Time (seconds)'})

		# init buttons
		# button = window.addItem(QtGui.Button(),row=1, col=0)

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

def main():
	global adc_value1, adc_value2, app

	# set up QT
	app = QtGui.QApplication(sys.argv)

	# multithread graphics and pi connections
	wp = WorkerPool()
	dataWorker = Worker(connectPi)
	wp.threadpool.start(dataWorker)

	mainwindow = MainWindow()

	# handle ctrl+c
	signal.signal(signal.SIGINT, sigint_handler)
	timer = QTimer()
	timer.start(50)  # You may change this if you wish.
	timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

	sys.exit(mainwindow.beginGraphics())

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtGui.QApplication.quit()


if __name__ == '__main__':
	import sys
	main()

