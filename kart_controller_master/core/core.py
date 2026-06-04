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
import time, datetime, threading, serial, sys, signal
import lib.kart_js as ks
import lib.kart_hs as hs

from config.kart_config import *


# ================== # 

# LOADING KART SETTINGS
k_cfg = Kart_Settings()

# ================== # 


core_running = False
core_command = (0,0,0)

arduino_serial = None

def print_core_hello():
    print("===   ©   Wheelchair Karting® 2026     ===")
    print(" *                                      *")
    print(" *         DeltaKart Core V3.0          *")
    print(" *                                      *")
    print("====== Written by Ettore Caccioli =======")

def get_direction_and_speed(x, death_zone):
    velocity = int(k_cfg.MOTOR_BASEANGLE+((abs(x)-death_zone)/(100-death_zone))*(k_cfg.MOTOR_MAXANGLE-k_cfg.MOTOR_BASEANGLE))
    return k_cfg.MOTOR_LEFT if x > 0 else k_cfg.MOTOR_RIGHT, 0 if abs(x) < death_zone else velocity

def packet_is_valid(x):
    return 1 if x == k_cfg.PACKET_OK else 0

def handler(sig, frame):
    print("SIGTERM_QUIT!")
    sys.exit(0)

def htons(x, format='big'):
    if format == 'little': return [(x & 0xFF), ((x >> 8) & 0xFF)] if type(x) is int else [(ord(x) & 0xFF), ((ord(x) >> 8) & 0xFF)]
    if format == 'big': return [((x >> 8) & 0xFF), (x & 0xFF)] if type(x) is int else [((ord(x) >> 8) & 0xFF), (ord(x) & 0xFF)]
    return -1

def twos_complement(val, bits) -> int:
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

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

def terminal_log(x, end='\n'):
    if k_cfg.VERBOSE: print(
        f"{datetime.datetime.now()}: {x}",
        end=end
    )

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
            terminal_log(f"CONNECTION FAILURE - [{e}], Proceding with LOOP -> {responce}")

        terminal_log(f"{packet.hex().strip()} -> {'OK!' if packet_is_valid(responce) else 'FAILURE!'}")
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

        self.hs = hs.KartHeadsetInput()
        arduino_serial = attach_arduino()

        self.responce_format = '<ffffH'


    def start(self):
        global core_running, core_command

        core_running = True
        self.worker.start()

        center = [0,0]

        try:
            print("[+] Kart Core Started, You Can Drive!")

            while core_running:
                hs_id, hs_pos = self.hs.get_headset_position()

                pos = (1 if center[0] < 0 else -1) * hs.relative_distance(center, self.hs.cam_center[0])

                direction, velocity = get_direction_and_speed(pos,k_cfg.HS_DTZN)

                core_command = (direction, velocity, 0)
                
                if hs_id == -1:
                    print("[+] Heaset Lost!")
                    pos = 0
                    continue
                elif hs_id == 0:
                    break
                
                print(f"[-] Headset Found!")

                center = hs.get_center_position(hs_pos)-self.hs.cam_center
        
        except KeyboardInterrupt:
            core_running = False
            self.worker.join()
            arduino_serial.close()

class SOCKET_RUN_Reciever:
    def __init__(self, x):
        self = x

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
        case CoreModes.SOCKET_RECIEVER:
            debug = SOCKET_RUN_Reciever()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
        case CoreModes.SOCKET_TRANSMITTER:
            debug = SOCKET_RUN_Transmitter()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
