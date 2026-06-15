import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

JS_SETUP = [2,5,4]
JS_BUTTONS = [0,1]
JS_DZ = 10

NORMAL_SENS = 0
LOW_SENS = 1
HIGH_SENS = 2

class KartJoystickInput:
    def __init__(self, id=0):

        self.steering_angle = 0
        self.gas_pedal = 0
        self.brake_pedal = 0

        self.raw_values = [0,0]
        self.raw_buttons = [0,0]

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

    def get_specified_buttons(self, buttons=JS_BUTTONS):
        self.raw_buttons = [self.js.get_button(x) for x in buttons]

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

        high_sens_b, low_sens_b = self.raw_buttons[0], self.raw_buttons[1]

        self.steering_precision = NORMAL_SENS

        if high_sens_b and low_sens_b:
            self.steering_precision = NORMAL_SENS
        elif high_sens_b:
            self.steering_precision = HIGH_SENS
        elif low_sens_b:
            self.steering_precision = LOW_SENS

    def trigger_update(self):
        pygame.event.pump()



if __name__ == "__main__":
    js = KartJoystickInput()

    print("[+] Kart Core Started, You Can Drive!")


    while True:
        js.get_specified_buttons(JS_BUTTONS)

        js.trigger_update()
        js.load_current_state(
            JS_SETUP, 
            JS_DZ
        )

        print(js.steering_precision)