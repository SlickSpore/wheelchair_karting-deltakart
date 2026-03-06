import warnings

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*pkg_resources*"
)
import time, datetime, threading, serial
import lib.kart_js as ks


from kart_config import *


# ================== # 

# LOADING KART SETTINGS
k_cfg = Kart_Settings()

# ================== # 

def htons(x, format='big'):
    if format == 'little': return [(x & 0xFF), ((x >> 8) & 0xFF)] if type(x) is int else [(ord(x) & 0xFF), ((ord(x) >> 8) & 0xFF)]
    if format == 'big': return [((x >> 8) & 0xFF), (x & 0xFF)] if type(x) is int else [((ord(x) >> 8) & 0xFF), (ord(x) & 0xFF)]
    return -1

def craft_packet(x, y, z) -> bytes:
    return bytes(
        htons(k_cfg.PACKET_HEADER) + 
        htons(x) + 
        htons(y) + 
        htons(z) + 
        htons(k_cfg.PACKET_FOOTER) + 
        [ord('\r')] + [ord('\n')])

def terminal_log(x):
    if k_cfg.VERBOSE: print(f"{datetime.datetime.now()}: {x}")


class DEBUG_run:
    def attach_arduino(self):
        self.arduino = serial.Serial(
            k_cfg.SERIAL_PORT, 
            baudrate=k_cfg.BAUD_RATE, 
            timeout=1
        )

    def __init__(self):
        self.command = (0,0,0)
        self.running = False
        self.worker = threading.Thread(
            target=self.serial_worker, 
            daemon=True
        )

        print("\n==========>> KART DEBUG RUN BEGIN! <<==========")
        print("-> v1.02\n\tWritten by Ettore Caccioli - 05/03/2026")
        print("\n==========>>       BOOTING!        <<==========")

        self.js = ks.Kart_Joystick_Input()
        self.attach_arduino()

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

    def serial_worker(self):

        self.hello_arduino()

        while self.running:
            x, y, z = self.command
            packet = craft_packet(x, y, z)

            try:
                responce = 0
                self.arduino.write(packet)
                responce = self.arduino.readline().hex().strip()
            except Exception as e:
                terminal_log(f"CONNECTION FAILURE - [{e}], Proceding with LOOP -> {responce}")


            terminal_log(f"{packet.hex().strip()} -> {'OK!' if self.is_valid(responce) else 'FAILURE!'}")

            if not self.is_valid(responce):
                terminal_log(f"ARDUINO FAILURE - [got_no_responce], Attempting Reconnection")
                try:
                    self.reconnect_arduino()
                except Exception as e:
                    terminal_log(f"CONNECTION FAILURE - [{e}], Attempting Reconnection")

            time.sleep(k_cfg.WRITING_SPEED)

    def start(self):
        self.running = True
        self.worker.start()
        try:
            while self.running:
                self.js.trigger_update()
                self.js.load_current_state(
                    k_cfg.JS_AXES, 
                    k_cfg.JS_DTZN
                )

                velocity = self.js.steering_angle

                if self.js.steering_angle > k_cfg.JS_THRESHOLD:
                    direction = k_cfg.MOTOR_LEFT
                elif self.js.steering_angle < -k_cfg.JS_THRESHOLD:
                    direction = k_cfg.MOTOR_RIGHT
                elif -k_cfg.JS_THRESHOLD < self.js.steering_angle < k_cfg.JS_THRESHOLD:
                    direction = k_cfg.MOTOR_HALT

                self.command = (direction, velocity, 0)
                time.sleep(k_cfg.READING_SPEED)
        
        except KeyboardInterrupt:
            self.running = False
            self.worker.join()
            self.arduino.close()

if __name__ == "__main__":
    debug = DEBUG_run()
    debug.start()
