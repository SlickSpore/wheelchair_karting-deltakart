import warnings, struct, time

"""
    Written By Ettore Caccioli
    © 2026 Wheelchair Karting
"""


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*pkg_resources*"
)
import time, datetime, threading, serial,  signal
import lib.kart_js as ks
import lib.kart_hs as hs
from lib.kart import *

from config.kart_config import Kart_Settings, CoreModes

# ================== # 

# LOADING KART SETTINGS
k_cfg = Kart_Settings()

# ================== # 

PRECISION = 4

core_running = False
core_command = (0,0,0)
steering_sensibility_curve = get_curve((75, 100))
arduino_serial = None

def get_direction_and_speed(x, death_zone):
    velocity = int(k_cfg.MOTOR_BASEANGLE+((abs(x)-death_zone)/(100-death_zone))*(k_cfg.MOTOR_MAXANGLE-k_cfg.MOTOR_BASEANGLE))
    return k_cfg.MOTOR_LEFT if x > 0 else k_cfg.MOTOR_RIGHT, 0 if abs(x) < death_zone else velocity

def packet_is_valid(x):
    return 1 if x == k_cfg.PACKET_OK else 0

def craft_packet(x, y, z) -> bytes:
    """
    Assembles a packet to be sent to the slave
    """

    return bytes(
        htons(k_cfg.PACKET_HEADER) + 
        htons(x) + 
        htons(y) + 
        htons(z) + 
        htons(k_cfg.PACKET_FOOTER) + 
        [ord('\r')] + [ord('\n')])


def attach_arduino():
    """
    Establishes a connection with the slave.
    
    Errors: Raises Fatal Error -2 if no connection is available.
    The webpage procedes to report the error to the user.
    """
    try:
        return serial.Serial(
            k_cfg.SERIAL_PORT, 
            baudrate=k_cfg.BAUD_RATE, 
            timeout=1
        )
    except serial.SerialException:
        print("[!] FATAL: Serial Failure! -> Check Connections Before Running")
        exit(-2)


def hello_arduino():
    """
    Sends 2 dummy packets waiting for responce to arduino slave.
    """

    arduino_serial.write(
        craft_packet(0,0,0)
    )
    arduino_serial.readline()

    arduino_serial.write(
        craft_packet(0xff, 0xff, 0xff)
    )
    arduino_serial.readline()


def serial_worker():
    """
    Description: This routine estableshes a connection between 
    the arduino slave and the computer core with
    a countinous serial stream running via thread.

    Every Iteration a packet is sent with this format:

                [HEADER]    : 0x4747
                [x]         : 0x0000
                [y]         : 0x0000
                [z]         : 0x0000
                [FOOTER]    : 0x470a

    Errors: In case of error, reconnection is attempted by keeping
    the serial open waiting for arduino's User Reset Interrupt
    or a spontanous one.
    """

    hello_arduino()

    while core_running:
        x, y, z = core_command
        packet = craft_packet(x, y, z)

        try:
            responce = 0
            arduino_serial.write(packet)
            responce = arduino_serial.readline() #.hex().strip()
        except Exception as e:
            print(f"CONNECTION FAILURE - [{e}], Proceding with LOOP -> {responce}")

        print(f"{packet.hex().strip()} -> {'OK!' if packet_is_valid(responce) else 'FAILURE!'}")
        time.sleep(k_cfg.WRITING_SPEED)

class JOYSTICK_RUN:
    """ Joystick Operating Mode """

    def __init__(self):
        global core_running, core_command, arduino_serial

        core_command = (0,0,0)
        core_running = False

        self.worker = threading.Thread(
            target=serial_worker, 
            daemon=True
        )

        self.js = ks.KartJoystickInput()
        arduino_serial = attach_arduino()

        self.responce_format = '<ffffH'

    def start(self):
        global core_running, core_command

        core_running = True
        self.worker.start()

        try:
            print("[+] Kart Core Started, You Can Drive!")
            while core_running:

                self.js.trigger_update()
                self.js.load_current_state(
                    k_cfg.JS_AXES, 
                    k_cfg.JS_DTZN
                )

                direction, velocity = get_direction_and_speed(self.js.steering_angle, k_cfg.JS_THRESHOLD)

                core_command = (direction, velocity, 0)
                time.sleep(k_cfg.READING_SPEED)
        
        except KeyboardInterrupt:
            core_running = False
            self.worker.join()
            arduino_serial.close()

class HEADSET_RUN:
    """ Headset Operating Mode """

    def __init__(self):
        global core_running, core_command, arduino_serial

        core_command = (0,0,0)
        core_running = False

        self.worker = threading.Thread(
            target=serial_worker, 
            daemon=True
        )

        self.headset = hs.KartHeadsetInput(disp_fb=True)
        arduino_serial = attach_arduino()

        self.zero_position = hs.get_center_position(hs.cvt_bb_to_rect(self.headset.zero_bbox), axis=0)

        self.responce_format = '<ffffH'


    def start(self):
        global core_running, core_command

        core_running = True
        self.worker.start()


        try:
            print("[+] Kart Core Started, You Can Drive!")

            while core_running:
                frame, headset_bbox, headset_center = self.headset.get_head_position()

                if headset_bbox == -1: 
                    continue

                input_value = hs.compute_steering_value(self.zero_position, headset_center)*100

                if self.headset.show_frame(frame):
                    hs.cv2.imshow("headset", frame)
                    if hs.cv2.waitKey(1) == 27:
                        break

                direction, velocity = apply_curve(steering_sensibility_curve, input_value)

                print(direction, velocity)

                core_command = (direction, velocity, 0)
                
        except KeyboardInterrupt:
            self.headset.stop_driving()
            core_running = False
            self.worker.join()
            arduino_serial.close()

if __name__ == "__main__":
    print_core_hello()

    match k_cfg.CORE_MODE:
        case CoreModes.JOYSTICK:
            debug = JOYSTICK_RUN()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
        case CoreModes.HEADSET:
            debug = HEADSET_RUN()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
