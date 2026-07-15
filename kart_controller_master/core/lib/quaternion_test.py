from kart_controller_master.core.lib.old.YbImuLib import YbImuSerialLib as ys
from scipy.signal import butter, lfilter
from math import atan2, degrees
import numpy as np
import os
import time


def connect_imu(freq=100):
    imu_serials = ["/dev/tty.usbserial-1130", "/dev/tty.usbserial-11210"]
    bot1 = ys.YbImuSerial(imu_serials[0])
    bot2 = ys.YbImuSerial(imu_serials[1])

    b, a = butter(3, 15/(0.5 * 100), btype="low", analog=False)

    x = [0,0]

    bot1.set_report_rate(freq)
    bot2.set_report_rate(freq)

    while 1:

        gx1, gy1, gz1 = bot1.get_gyroscope_data()
        gx2, gy2, gz2 = bot2.get_gyroscope_data()

        x.append(gx1)

        gx1_filtrato = (
            b[0] * gx1 +
            b[1] * x[0] +
            b[2] * x[1] +
            b[3] * x[2] -
            a[1] * y[0] -
            a[2] * y[1] -
            a[3] * y[2]
        ) / a[0]

        old_data_gx = [old_data_gx[1], old_data_gx[2]]
    

        print(filtered_gx)


connect_imu()

