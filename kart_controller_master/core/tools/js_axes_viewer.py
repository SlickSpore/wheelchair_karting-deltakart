import lib.kart_js as Joystick

js = Joystick.KartJoystickInput()

while True:
    js.trigger_update()
    print([js.get_specified_axes(i) for i in range(js.js.get_maxaxes())])