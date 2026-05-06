MOTOR_RIGHT = 1
MOTOR_LEFT = -1
MOTOR_MAXANGLE = 180

def get_direction_and_speed(js_angle, death_zone):
    velocity = int((abs(js_angle)-death_zone)/(100-death_zone)*MOTOR_MAXANGLE)
    return MOTOR_LEFT if js_angle < 0 else MOTOR_RIGHT, 0 if abs(js_angle) < death_zone else velocity


for i in range(-100,101):
    print(i, get_direction_and_speed(i, 10))