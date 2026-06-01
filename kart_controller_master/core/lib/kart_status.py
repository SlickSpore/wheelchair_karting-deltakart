import gpiozero, enum

class LedPins(enum.Enum):
    RED   = 20
    GREEN = 21
    BLUE  = 26

class LedStatus(enum.Enum):
    READY = "g"
    SET   = "b"
    FAIL  = "r"

class StatusLeds:
    def __init__(self):
        self.last_status = None
        self.rgb_leds = {
            "g":    gpiozero.LED(LedPins.GREEN.value),
            "r":    gpiozero.LED(LedPins.RED.value),
            "b":    gpiozero.LED(LedPins.BLUE.value),
        }
    
    def turn_off(self):
        for i in self.rgb_leds:
            self.rgb_leds[i].off()

    def set_status(self, status=LedStatus.READY, multiple_leds=False):
        print(status, self.last_status)
        if status != self.last_status:
            if not multiple_leds: self.turn_off()
            self.rgb_leds[status.value].on()
        self.last_status = status
