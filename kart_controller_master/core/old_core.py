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
import lib.kart_js as js
import kart_controller_master.core.lib.old.kart_hs as hs

from config.kart_config import *


# ================== # 

# LOADING KART SETTINGS
k_cfg = Kart_Settings()

# ================== # 

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
    return bytes(
        htons(k_cfg.PACKET_HEADER) + 
        htons(x) + 
        htons(y) + 
        htons(z) + 
        htons(k_cfg.PACKET_FOOTER) + 
        [ord('\r')] + [ord('\n')])

def terminal_log(x, end='\n'):
    if k_cfg.VERBOSE: print(f"{datetime.datetime.now()}: {x}", end=end)


class JOYSTICK_RUN:
    def attach_arduino(self):
        try:
            self.arduino = serial.Serial(
                k_cfg.SERIAL_PORT, 
                baudrate=k_cfg.BAUD_RATE, 
                timeout=1
            )
        except serial.SerialException:
            print("[!] FATAL: Serial Failure! -> Check Connections Before Running")
            exit(-2)

    def __init__(self):
        self.command = (0,0,0)
        self.running = False
        self.worker = threading.Thread(
            target=self.serial_worker, 
            daemon=True
        )

        print("===   ©   Wheelchair Karting® 2026     ===")
        print(" *                                      *")
        print(" *         DeltaKart Core V2.0          *")
        print(" *                                      *")
        print("====== Written by Ettore Caccioli =======")

        self.js = js.KartJoystickInput()
        self.attach_arduino()

        terminal_log("|RunTime|=====|X-Accel|========|Y-Accel|=======|G-Accel|=======|CoreTemp|")
        self.responce_format = '<ffffH'
        self.start_time = time.time()

    def is_valid(self, x):
        return 1 if x == k_cfg.PACKET_OK else 0

    def hello_arduino(self):
        self.arduino.write(
            craft_packet(0,0,0)
        )
        self.arduino.readline()

        self.arduino.write(
            craft_packet(0xff, 0xff, 0xff)
        )
        self.arduino.readline()

    def reconnect_arduino(self):
        self.arduino.close()
        self.attach_arduino()
        self.hello_arduino()

    def load_core_data(self, responce):

        acc1, acc2, acc3, temp, _ = struct.unpack(self.responce_format, responce)

        self.acc1 = round(acc1,2) 
        self.acc2 = round(acc2,2) 
        self.acc3 = round(acc3,2)
        self.temp = round(temp,2)

    def try_reconnection(self, responce):
        if not self.is_valid(responce):
            terminal_log(f"ARDUINO FAILURE - [got_no_responce], Attempting Reconnection")
            try:
                self.reconnect_arduino()
            except Exception as e:
                terminal_log(f"CONNECTION FAILURE - [{e}], Attempting Reconnection")

    def serial_worker(self):

        self.hello_arduino()

        while self.running:
            x, y, z = self.command
            packet = craft_packet(x, y, z)

            try:
                responce = 0
                self.arduino.write(packet)
                responce = self.arduino.readline() #.hex().strip()
                self.load_core_data(responce)

                terminal_log(f" {round(time.time()-self.start_time, 2):.3f}s\t\t{("+" if self.acc1 > 0 else '-') + str(abs(self.acc1))}g\t\t{("+" if self.acc2 > 0 else '-' )+ str(abs(self.acc2))}g\t\t{("+" if self.acc3 > 0 else '-') + str(abs(self.acc3))}g\t\t{self.temp}°C", end='\r')

            except Exception as e:
                terminal_log(f"CONNECTION FAILURE - [{e}], Proceding with LOOP -> {responce}")


            terminal_log(f"{packet.hex().strip()} -> {'OK!' if self.is_valid(responce) else 'FAILURE!'}")

            time.sleep(k_cfg.WRITING_SPEED)

    def get_direction_and_speed(self, js_angle, death_zone):
        velocity = int(k_cfg.MOTOR_BASEANGLE+((abs(js_angle)-death_zone)/(100-death_zone))*(k_cfg.MOTOR_MAXANGLE-k_cfg.MOTOR_BASEANGLE))
        return k_cfg.MOTOR_LEFT if js_angle > 0 else k_cfg.MOTOR_RIGHT, 0 if abs(js_angle) < death_zone else velocity

    def start(self):
        self.running = True
        self.worker.start()
        try:
            print("[+] Kart Core Started, You Can Drive!")
            while self.running:
                self.js.trigger_update()
                self.js.load_current_state(
                    k_cfg.JS_AXES, 
                    k_cfg.JS_DTZN
                )

                direction, velocity = self.get_direction_and_speed(self.js.steering_angle, k_cfg.JS_THRESHOLD)

                self.command = (direction, velocity, 0)
                time.sleep(k_cfg.READING_SPEED)
        
        except KeyboardInterrupt:
            self.running = False
            self.worker.join()
            self.arduino.close()

core_running = False
core_command = (0,0,0)

arduino_serial = None

def attach_arduino():
    try:
        return serial.Serial(
            k_cfg.SERIAL_PORT, 
            baudrate=k_cfg.BAUD_RATE, 
            timeout=1
        )
    except serial.SerialException:
        print("[!] FATAL: Serial Failure! -> Check Connections Before Running")
        exit(-2)

def is_valid(x):
    return 1 if x == k_cfg.PACKET_OK else 0


def hello_arduino(self):
    arduino_serial.write(
        craft_packet(0,0,0)
    )
    arduino_serial.readline()

    arduino_serial.write(
        craft_packet(0xff, 0xff, 0xff)
    )
    arduino_serial.readline()


def serial_worker(self):
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


        terminal_log(f"{packet.hex().strip()} -> {'OK!' if is_valid(responce) else 'FAILURE!'}")

        time.sleep(k_cfg.WRITING_SPEED)

def print_core_hello():
    print("===   ©   Wheelchair Karting® 2026     ===")
    print(" *                                      *")
    print(" *         DeltaKart Core V3.0          *")
    print(" *                                      *")
    print("====== Written by Ettore Caccioli =======")

def get_direction_and_speed(x, death_zone):
    velocity = int(k_cfg.MOTOR_BASEANGLE+((abs(x)-death_zone)/(100-death_zone))*(k_cfg.MOTOR_MAXANGLE-k_cfg.MOTOR_BASEANGLE))
    return k_cfg.MOTOR_LEFT if x > 0 else k_cfg.MOTOR_RIGHT, 0 if abs(x) < death_zone else velocity


class HEADSET_RUN:
    def __init__(self):
        print_core_hello()

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

        # add calibration


    def start(self):
        global core_running, core_command

        core_running = True
        self.worker.start()

        center = [0,0]

        try:
            print("[+] Kart Core Started, You Can Drive!")
            while core_running:

                hs_id, hs_pos = self.hs.get_headset_position(show=True)

                pos = (1 if center[0] < 0 else -1) * hs.relative_distance(center, self.hs.cam_center[0])

                if hs_id == -1:
                    continue
                elif hs_id == 0:
                    break
                
                center = hs.get_center_position(hs_pos)-self.hs.cam_center

                direction, velocity = get_direction_and_speed(pos,k_cfg.HS_DTZN)

                core_command = (direction, velocity, 0)
                time.sleep(k_cfg.READING_SPEED)
        
        except KeyboardInterrupt:
            core_running = False
            self.worker.join()
            arduino_serial.close()

if __name__ == "__main__":
    print(k_cfg.CORE_MODE)
    match k_cfg.CORE_MODE:
        case CoreModes.JOYSTICK:
            debug = JOYSTICK_RUN()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
        case CoreModes.HEADSET:
            debug = HEADSET_RUN()
            signal.signal(signal.SIGTERM, handler)
            debug.start()
