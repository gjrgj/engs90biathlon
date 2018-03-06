import cv2
import math
import numpy as np
# use this value to compute a good radius for the function
# global startRadius
# startRadius = 50

class ProcessFrame:
	def __init__(self):
		# global startRadius
		# # init hough function parameters
		# self.image = 0
		# self.method = cv2.HOUGH_GRADIENT
		# self.dp = 2.5
		# self.minDist = 250
		# self.param1 = 36
		# self.param2 = 60
		# self.minRadius = 65
		# self.maxRadius = 78
		# # init circle data for previous iteration
		# self.circles_prev = None
		# self.circles_curr = None
		# # offset comparisons
		# self.firstQuery = True
		pass

	# finds target locations
	def find_targets(self, frame):
		# Takes a cv2.imread COLOR image and returns [y_center, x_center, radius] of all circles
		# https://www.pyimagesearch.com/2014/07/21/detecting-circles-images-using-opencv-hough-circles/
		frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
	
		circles = cv2.HoughCircles(frame,cv2.HOUGH_GRADIENT,2.5,250,
            param1=36,param2=60,minRadius=65,maxRadius=78)
		# get initial values to start with
		# self.image = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
		# circles = cv2.HoughCircles(self.image,self.method,self.dp,self.minDist,
		# 	self.param1,self.param2,self.minRadius,self.maxRadius)
		# # start disjoint comparisons
		# if self.firstQuery:		
		# 	self.circles_prev = circles
		# 	self.firstQuery = False
		# else:
		# 	# compare and adjust params accordingly
		# 	self.circles_curr = circles
		# 	self.adjustHough()
		# 	self.circles_prev = self.circles_curr
		# 	self.circles_curr = None
		return circles

	# automatically adjusts hough parameters to find the best ones for the current test
	# because HoughCircles is a relatively quick function (linear time) we can iterate over many
	# different combinations of parameter values from both sides (large -> small, small -> large)
	# in order to settle on the best fit values
	# https://dsp.stackexchange.com/questions/22648/in-opecv-function-hough-circles-how-does-parameter-1-and-2-affect-circle-detecti
	def adjustHough(self):
		global startRadius
		# check and make sure there have been circles detected, if not then don't continue
		if self.circles_curr is None or self.circles_prev is None:
			return
		if len(self.circles_curr) == 1 or len(self.circles_prev) == 1:
			return
		# if the circle center distance change is less than a threshold, don't adjust values
		# else adjust parameters based on a step rate defined by how far the centers are from their previous values
		# first calculate total distance between individual circles from each run
		curr_total = 0
		prev_total = 0
		# self.circles_curr = np.uint16(np.around(self.circles_curr))
		# self.circles_prev = np.uint16(np.around(self.circles_prev))
		for i in self.circles_curr[0,:]:
			for j in self.circles_curr[0,:]:
				if (len(i) >= 2 and len(j) >= 2):
					curr_total += math.sqrt(math.pow(i[0] - j[0],2) + math.pow(i[1] - j[1],2))
		for i in self.circles_prev[0,:]:
			for j in self.circles_prev[0,:]:
				if (len(i) >= 2 and len(j) >= 2):
					prev_total += math.sqrt(math.pow(i[0] - j[0],2) + math.pow(i[1] - j[1],2))
		# now calculate the percentage change by dividing the total distances, adjust params in different ways depending on the magnitude of difference
		# reset radii if the difference is too great
		if (abs(curr_total) - abs(prev_total) == 0):
			print('Equal')
			return
		if abs(curr_total-prev_total) > 1000:
			self.minRadius = startRadius-5
			self.maxRadius = startRadius+5
			self.minDist = int(self.minRadius/2)
		if abs(curr_total-prev_total) > 500:
			self.minRadius += 5
			self.maxRadius += 5
			self.minDist = int(self.minRadius/2)
		if abs(curr_total-prev_total) > 250:
			self.minRadius += 5
			self.maxRadius += 5
			self.minDist = int(self.minRadius/2)
		if abs(curr_total-prev_total) > 100:
			self.minRadius += 5
			self.maxRadius += 5
		# if the distance change is less than 2%, we have the right values and can move on

	# finds laser point location
	def find_laser(self, frame):
		# Takes a cv2.imread image and returns the cartesian coordinate pair of a
		# red laser dot in the image
		# https://github.com/bradmontgomery/python-laser-tracker
		# https://docs.opencv.org/3.4.0/d7/d4d/tutorial_py_thresholding.html
		# https://www.pyimagesearch.com/2015/09/14/ball-tracking-with-opencv/

		# Convert image to HSV and split into three channels
		hsv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
		h, s, v = cv2.split(hsv_img)

		# Define HSV threshold values
		hue_min = 0
		hue_max = 300

		sat_min = 0
		sat_max = 255

		val_min = 255
		val_max = 255

		# Threshold the three channels
		# cv2.THRESH_BINARY for regular binary
		# cv2.ADAPTIVE_THRESH_MEAN_C, cv2.ADAPTIVE_THRESH_GAUSSIAN_C different types of adaptive
		ret, binary_h = cv2.threshold(h, hue_min, hue_max, cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
		ret, binary_s = cv2.threshold(s, sat_min, sat_max, cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
		ret, binary_v = cv2.threshold(v, val_min, val_max, cv2.ADAPTIVE_THRESH_GAUSSIAN_C)

		# Bitwise and the three channels so only the laser is left
		laser = cv2.bitwise_and(h, s)
		laser = cv2.bitwise_and(laser, v)
		ret, laser = cv2.threshold(laser, 127, 245, cv2.THRESH_BINARY) # For some reason 'laser' isn't really binary after the last two lines so do one more cutoff

		# Find the laser's position
		contours = cv2.findContours(laser, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

		if len(contours) > 0:
			c = max(contours, key=cv2.contourArea)
			((x, y), radius) = cv2.minEnclosingCircle(c)
			moments = cv2.moments(c)

			if moments["m00"] > 0:
				center = int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"])
				return center

			else:
				center = int(x), int(y)
				return center

		return (-1, -1) # If the laser isn't found
