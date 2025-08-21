
from lsm6ds3 import LSM6DS3
import time

lsm = LSM6DS3()
sent = 0.000061

def read_acc():
	ax, ay, az, gx, gy, gz = lsm.get_readings()
	ax = sent * ax
	ay = sent * ay
	az = sent * az
	
	return ax, ay, az
