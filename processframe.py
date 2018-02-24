import cv2

class ProcessFrame:
	def __init__(self):
		pass

	def find_targets(self, frame):
		# Takes a cv2.imread COLOR image and returns [y_center, x_center, radius] of all circles
		# https://www.pyimagesearch.com/2014/07/21/detecting-circles-images-using-opencv-hough-circles/

		frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
		#frame = cv2.medianBlur(frame,3)
		circles = cv2.HoughCircles(frame,cv2.HOUGH_GRADIENT,1,20,
			param1=100,param2=100,minRadius=85,maxRadius=125)

		return circles

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
