from collections import deque
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter
import time
import lib.YbImuLib as yb

GLOBAL_FREQUENCY = 100  # Hz
DT = 1.0 / GLOBAL_FREQUENCY
GLOBAL_FILTER = 0.5
GYRO_IN_DEGREES = False

def generate_filter(cutoff=5.0, fs=GLOBAL_FREQUENCY, order=2):
    nyquist = fs * 0.5
    b, a = butter(order, cutoff / nyquist, btype="low")
    return b, a

def get_sensor_bias(sensor: yb.YbImuSerial, cicles=100):
    gyro_data = []

    for _ in range(cicles):
        gyro_data.append(sensor.get_gyroscope_data())
        time.sleep(1/GLOBAL_FREQUENCY)
    
    return tuple(np.mean(gyro_data, axis=0))

def init_sensor(serial_port):
    bot1 = yb.YbImuSerial(serial_port)
    bot1.create_receive_threading()
    bot1.calibration_imu()
    bias = get_sensor_bias(bot1)
    return bias, bot1

class RTButterFilter:
    def __init__(self, coeffs=None):
        if coeffs is None:
            coeffs = generate_filter()

        self.b, self.a = coeffs

        self.x = deque([0.0] * len(self.b), maxlen=len(self.b))
        self.y = deque([0.0] * (len(self.a) - 1), maxlen=len(self.a) - 1)

    def update(self, sample):
        self.x.appendleft(sample)
        y = 0.0
        for bi, xi in zip(self.b, self.x):
            y += bi * xi
        for ai, yi in zip(self.a[1:], self.y):
            y -= ai * yi
        y /= self.a[0]
        self.y.appendleft(y)
        return y

class ComplementaryRoll:
    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.roll = 0.0

    def update(self, gyro_x, acc_y, acc_z):
        self.roll += gyro_x * DT

        roll_acc = math.atan2(acc_y, acc_z)

        self.roll = (
            self.alpha * self.roll +
            (1.0 - self.alpha) * roll_acc
        )
        return self.roll

class KartHeadsetInput:
    def __init__(self, speed, range=45, floor=10, cutoff_filter_freq=3, precision=3):
        """Tells the steering where to go based on the headset roll position
        
        Parameters
        ----------
        speed : int
            Delta Time in seconds between each packet.
        
        range : int
            Maximum Absoulute bound in degrees of motion
        
        floor : int
            Minimum Absolute bound in degrees of motion
        
        cutoff_filter_freq : int
            Cutoff frequency in hertz
        
        precision : int
            Rounding Precision
        
        Returns
        _______
        KartHeadsetInput Class Istance
        
        """
        global GLOBAL_FILTER
        GLOBAL_FILTER = 1/speed
        self.precision = precision
        self.max_bounds = range
        self.min_bounds = floor

        (self.gx_bias_headset, _, _), self.headset_imu = init_sensor("/dev/tty.usbserial-1210")
        (self.gx_bias_frame, _, _), self.frame_imu = init_sensor("/dev/tty.usbserial-130")

        self.headset_roll_filter = RTButterFilter(generate_filter(cutoff=cutoff_filter_freq))
        self.frame_roll_filter = RTButterFilter(generate_filter(cutoff=cutoff_filter_freq))
        self.headset_roll_complementary = ComplementaryRoll(alpha=0.98)
        self.frame_roll_complementary = ComplementaryRoll(alpha=0.98)

    def get_headset_position(self):

        try:
            while True:
                gx, _, _ = self.headset_imu.get_gyroscope_data()
                _, ay, az = self.headset_imu.get_accelerometer_data()

                gx -= self.gx_bias_headset
                headset_roll = self.headset_roll_complementary.update(gx, ay, az)

                gx, _, _ = self.frame_imu.get_gyroscope_data()
                _, ay, az = self.frame_imu.get_accelerometer_data()

                gx -= self.gx_bias_frame
                frame_roll = self.frame_roll_complementary.update(gx, ay, az)

                filtered_headset_roll = np.array(self.headset_roll_filter.update(headset_roll))
                filtered_frame_roll = np.array(self.frame_roll_filter.update(frame_roll))

                final_roll = math.degrees(filtered_frame_roll-filtered_headset_roll)

                yield (
                    max(
                        self.min_bounds,
                        min(
                            self.max_bounds+self.min_bounds, 
                            abs(
                                np.round(
                                    final_roll, 
                                    self.precision
                                )
                            )
                        )
                    ) - self.min_bounds
                ) / self.max_bounds * 100 * (-1 if final_roll < 0 else 1)
        except KeyboardInterrupt:
            print("Quitting!")
            return

if __name__ == "__main__":
    
    hs = KartHeadsetInput()
    
    for roll in hs.get_headset_position():
        print(roll)
        time.sleep((1/GLOBAL_FREQUENCY))

    exit(-1)
    df = pd.read_csv("data/frame_imu_recording_4curve.csv")

    gyro_x = df["gyro_x"].to_numpy()
    acc_y = df["acc_y"].to_numpy()
    acc_z = df["acc_z"].to_numpy()

    roll_filter = RTButterFilter(generate_filter(cutoff=GLOBAL_FILTER))

    estimator = ComplementaryRoll(alpha=0.98)

    roll_estimated = []
    roll_acc = []
    roll_gyro = []

    gyro_only = 0.0

    for gx, ay, az in zip(gyro_x, acc_y, acc_z):

        if GYRO_IN_DEGREES:
            gyro = math.radians(gx)

        gyro_only += gx * DT

        roll, acc_roll = estimator.update(gx, ay, az)

        roll_filtered = roll_filter.update(roll)

        roll_estimated.append(math.degrees(roll_filtered))
        roll_acc.append(math.degrees(acc_roll))
        roll_gyro.append(math.degrees(gyro_only))

    df = pd.read_csv("data/headset_imu_recording_4curve.csv")

    gyro_x = df["gyro_x"].to_numpy()
    acc_y = df["acc_y"].to_numpy()
    acc_z = df["acc_z"].to_numpy()

    roll_filter = RTButterFilter(generate_filter(cutoff=GLOBAL_FILTER))

    estimator = ComplementaryRoll(alpha=0.98)

    roll_estimated1 = []
    roll_acc1 = []
    roll_gyro1 = []

    gyro_only = 0.0

    for gx, ay, az in zip(gyro_x, acc_y, acc_z):

        if GYRO_IN_DEGREES:
            gyro = math.radians(gx)

        gyro_only += gx * DT

        roll, acc_roll = estimator.update(gx, ay, az)

        roll_filtered = roll_filter.update(roll)

        roll_estimated1.append(math.degrees(roll_filtered))
        roll_acc1.append(math.degrees(acc_roll))
        roll_gyro1.append(math.degrees(gyro_only))

    plt.figure(figsize=(12,6))
    plt.plot(roll_estimated, label="Headset Complementary Filter", linewidth=2, alpha=.4)
    plt.plot(roll_estimated1, label="Frame Complementary Filter", linewidth=2, alpha=.4)
    plt.plot(-np.array(roll_estimated)+np.array(roll_estimated1[:-6]), label="Combined Telemetry", linewidth=2)
    plt.xlabel("Campione")
    plt.ylabel("Roll [°]")
    plt.title("Stima del Roll")
    plt.title("Headset Angle View")
    plt.grid(True)
    plt.legend()
    plt.show()