import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame


JS_SETUP = [2,5,4]
JS_DZ = 10

class Kart_Joystick_Input:
    def __init__(self, id=0):

        self.steering_angle = 0
        self.gas_pedal = 0
        self.brake_pedal = 0

        print(f"\n[@] Pairing to Joystick {id}!")

        pygame.init()
        pygame.joystick.init()
        try:
            self.js = pygame.joystick.Joystick(id)
            self.js.init()
        except Exception as e:
            print("[!] FATAL: Joystick Failure! -> Check Connections Before Running")
            exit(-1)
        print(f"[+] Successfully paired to: {self.js.get_name()}")

    def get_specified_axes(self, axes: list[int]):
        self.raw_values = [round(self.js.get_axis(x), 2) * 100 for x in axes]

    def apply_death_zone(self, value):
        self.raw_values = [j if j < -value or j > value else 0 for j in self.raw_values]

    def load_current_state(self, axes, death_zone):
        self.get_specified_axes(axes)
        self.apply_death_zone(death_zone)

        self.steering_angle = int(round(self.raw_values[0],2))
        self.gas_pedal = self.raw_values[1]
        self.brake_pedal = self.raw_values[2]

        self.gas_pedal /= 2
        self.gas_pedal += 50

        self.brake_pedal /= 2
        self.brake_pedal += 50

    def trigger_update(self):
        pygame.event.pump()



if __name__ == "__main__":
    js = kart_joystick_input()

    while True:
        pygame.event.pump()
        js.load_current_state(JS_SETUP, JS_DZ)
        
        print(js.brake_pedal)