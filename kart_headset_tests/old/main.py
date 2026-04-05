#!/usr/bin/env python3


import time, math, numpy, time, datetime
from YbImuLib import YbImuSerial


SERIAL_PORT = "/dev/ttyUSB0"

READ_INTERVAL = 0.1

HEAD_RANGE = 5


def create_serial_device() -> YbImuSerial:
    imu = YbImuSerial(SERIAL_PORT, debug=False)
    imu.create_receive_threading()
    return imu


def get_euler_axes(imu: YbImuSerial):
    roll, pitch, yaw = imu.get_imu_attitude_data()
    return (roll, pitch, yaw)

def quaternion_to_yaw(q):
    w, x, y, z = q
    return math.atan2(2.0 * (w*z + x*y), 1 - 2 * (y*y + z*z))

def get_head_track(imu: YbImuSerial):
    axes = numpy.round(imu.get_accelerometer_data(),2)

    modulo = axes[2]
    sign = -1 if axes[1] < 0 else + 1
    return round((abs(1-modulo)*sign)*250,2)

def print_data(x):
    print(' '*(10+(int(x/10))), "X", ' '*(10-(int(x/10))), end='\r')


def main() -> None:
    imu = create_serial_device()

    imu.calibration_imu()
    with open("reading.txt", "w+") as f:

        try:
            version = imu.get_version()
            print(f"Firmware version: {version}")
        except Exception:
            print("Firmware version: unavailable in serial mode")

        while KeyboardInterrupt:
            print_data(get_head_track(imu))
            f.write(f"{str(datetime.datetime.now())},{str(get_head_track(imu))}\n")
            time.sleep(1/100)
    f.close()
if __name__ == "__main__":
    main()