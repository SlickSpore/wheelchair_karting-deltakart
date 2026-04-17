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


class DEBUG_run:
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

        self.js = ks.Kart_Joystick_Input()
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

            #self.try_reconnection(responce)

            time.sleep(k_cfg.WRITING_SPEED)

    def get_direction_and_speed(self, js_angle, death_zone):
        velocity = abs(int(js_angle/100*k_cfg.MOTOR_MAXANGLE))
        return k_cfg.MOTOR_LEFT if js_angle < 0 else k_cfg.MOTOR_RIGHT, 0 if abs(js_angle) < death_zone else velocity

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

if __name__ == "__main__":
    debug = DEBUG_run()
    signal.signal(signal.SIGTERM, handler)
    debug.start()
