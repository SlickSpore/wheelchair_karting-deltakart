import gpiozero, enum, platform

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
        self.macos = "macos" in platform.platform(terse=True).lower()

        self.rgb_leds = {
            "g":    None,
            "r":    None,
            "b":    None,
        }

        if not self.macos:
            self.rgb_leds = {
                "g":    gpiozero.LED(LedPins.GREEN.value),
                "r":    gpiozero.LED(LedPins.RED.value),
                "b":    gpiozero.LED(LedPins.BLUE.value),
            }
    
    def turn_off(self):
        if self.macos:
            return
        for i in self.rgb_leds:
            self.rgb_leds[i].off()

    def set_status(self, status=LedStatus.READY, multiple_leds=False):
        if self.macos:
            return
        if status != self.last_status:
            if not multiple_leds: self.turn_off()
            self.rgb_leds[status.value].on()
        self.last_status = status
