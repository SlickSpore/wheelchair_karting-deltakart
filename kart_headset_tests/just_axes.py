#!/usr/bin/env python3


import time, numpy, time, os
from YbImuLib import YbImuSerial


SERIAL_PORT = "/dev/ttyUSB0"

def create_serial_device() -> YbImuSerial:
    imu = YbImuSerial(SERIAL_PORT, debug=False)
    imu.create_receive_threading()
    return imu

def get_axes(imu: YbImuSerial):
    return numpy.round(imu.get_accelerometer_data(), 2)

def get_head_track(ay, az, range=250, precision=4):
    modulo = az
    sign = -1 if ay < 0 else + 1
    return round((abs(1-modulo)*sign)*range,precision)

def main():
    print("[+] Connecting to Device!")

    imu = create_serial_device()
    s = True if input("[?] CALIBRATION? (Y/n) ").lower() == 'y' else False

    if s: 
        imu.calibration_imu()

    pname = input("[+] Insert Project Name: ")

    print("[*] Starting Recording:")

    os.mkdir(f"data/{pname}")

    with open(f"data/{pname}/sensor_data.csv", "w+") as f:
        f.write("ACC_X,ACC_Y,ACC_Z,ROLL,PITCH,YAW,HEAD_A\n")

        time_enlapsed = 0

        try:
            while 1:
                ax, ay, az = imu.get_accelerometer_data()
                gx, gy, gz = imu.get_gyroscope_data()

                ha = get_head_track(ay,az)

                f.write(f"{ax},{ay},{az},{gx},{gy},{gz},{ha}\n")
                time.sleep(1/100)
                time_enlapsed += 1/100
                print(f"[i] Enlapsed: {round(time_enlapsed,2)}", end='\r')

        except KeyboardInterrupt:
            print(f"[||] Recording Stopped! Duration: {round(time_enlapsed,2)} Saving and Quitting")
            f.write("\n")
            f.close()        


if __name__ == "__main__":
    main()