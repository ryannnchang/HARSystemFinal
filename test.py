from infer import predict
from sensor import read_acc
from infer import convert
from screen import display, off
import numpy as np
import torch
import time
import RPi.GPIO as GPIO

try: 
	#Data Labels
	data_labels = {0.0:"Walk", 1.0: "WalkUp", 2.0: "WalkDw", 3.0: "Sit", 4.0: "Stand", 5.0: "Lay"}

	##Button Pin Definition
	button = 17
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(button, GPIO.IN)

	while GPIO.input(button) != False: 
		window = [[], [], []]
		window_size = 128	

		while len(window[0]) < window_size:
			ax, ay, az = read_acc()
			window[0].append(ax)
			window[1].append(ay)
			window[2].append(az)
			time.sleep(0.02)
		
		window = convert(window)
		prediction, con = predict(window)

		display(str(data_labels[prediction]), str(round(con*100)))
		print(f"Prediction: {data_labels[prediction]} \t Confidence: {round(con*100)}%")
	
	off()
except KeyboardInterrupt:
	print("Exiting Program")
	off()
