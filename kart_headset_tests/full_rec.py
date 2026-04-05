#!/usr/bin/env python3


import time, numpy, time, os, cv2
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

def set_camera_and_video(fname):
    cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[!] Unable to open Webcam! Quitting")
        exit(-1)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(fname, fourcc, 20.0, (frame_width, frame_height))

    return cap, out

def write_frame(cap, out, t):
    ts = time.time()
    ret, frame = cap.read()
    cv2.putText(frame, f"Time: {round(t,2)}", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2, cv2.LINE_AA)
    cv2.imshow('Webcam', frame)
    out.write(frame)
    return time.time() - ts

def check_quit():
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return True
    return False
    

def close_videos(cap, out):
    cap.release()
    out.release()
    cv2.destroyAllWindows()

def start_recording():
    print("=== Wheelchair Karting's HEAD DRIVE Test Program ===")
    print("Written By Ettore Caccioli V.2.0")

    pname = "data/" + input("[~] Insert Project Name: ")

    os.mkdir(pname)

    print("[+] Initializing WebCam and IMU Serial Device")
    video_capture, video_output = set_camera_and_video(f"{pname}/video_data.avi")
    print("[+] Camera Connected!")

    imu = create_serial_device()
    print("[+] IMU Connected!")

    s = True if input("[~] Perform IMU Calibration? (Y/n) ").lower() == 'y' else False

    if s: 
        imu.calibration_imu()
        print("[+] IMU Successfully Calibrated!")


    print("[*] Starting Recording:")


    with open(f"{pname}/sensor_data.csv", "w+") as f:
        f.write("ACC_X,ACC_Y,ACC_Z,ROLL,PITCH,YAW,HEAD_A\n")

        time_enlapsed = 0

        try:
            while 1:
                time_delta = write_frame(video_capture, video_output, time_enlapsed)

                ax, ay, az = imu.get_accelerometer_data()
                gx, gy, gz = imu.get_gyroscope_data()

                ha = get_head_track(ay,az)

                f.write(f"{ax},{ay},{az},{gx},{gy},{gz},{ha}\n")
                # time.sleep(1/100)
                time_enlapsed += 1/24
                print(f"[i] Enlapsed: {round(time_enlapsed,2)}", end='\r')

                if check_quit():
                    break

        except KeyboardInterrupt:
            print(f"[||] Recording Stopped! Duration: {round(time_enlapsed,2)} Saving and Quitting")
            f.write("\n")
            f.close()     
            close_videos(video_capture, video_output)



if __name__ == "__main__":
    start_recording()