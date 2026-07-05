import sounddevice as sd
import kart_js as k_js
import numpy as np
import threading
import pandas as pd
import math
import time

direction = 0.0
running = True
lock = threading.Lock()


def get_panning(direction):
    pan_val = (direction + 1.0) / 2.0
    theta = pan_val * (np.pi / 2.0)
    return np.cos(theta), np.sin(theta)

def get_wave(direction, direction_pan_coef=1.7, duration=0.1, amp=1, sample_rate=44100):

    frequency = 1000 if direction > 0 else 2000
    frequency = frequency if direction != 0 else 800

    t_wave = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    l, r = get_panning((1 if direction>0 else -1) * min(100, abs(direction*direction_pan_coef)))

    if direction > 0.05:
        wave_right = amp * np.sin(2 * np.pi * 1500 * t_wave).astype(np.float32) 
        return np.column_stack((wave_right * l, wave_right * r))
    elif direction < -0.05:
        wave_left = amp * np.sin(2 * np.pi * 1000 * t_wave).astype(np.float32)   
        return np.column_stack((wave_left * l, wave_left * r))
    else:
        wave_zero = amp * np.sin(2 * np.pi * 800 * t_wave).astype(np.float32)  
        return np.column_stack((wave_zero, wave_zero))

def beep_routine():
    global running, direction
    
    sample_rate = 44100
    time_max = 0.3
    last_beep = 0.0

    with sd.OutputStream(samplerate=sample_rate, channels=2) as stream:
        while True:
            wave = get_wave(direction)
            
            with lock:
                if not running:
                    break
                current_interval = time_max * (1-abs(direction))

            time_now = time.time()
            if time_now - last_beep >= current_interval:
                stream.write(wave)
                last_beep = time_now 
            
            time.sleep(0.001)

def test_audio_indications():
    global direction, running

    x = threading.Thread(target=beep_routine)
    x.start()

    js = k_js.KartJoystickInput()
    try: 
        while True:
            js.trigger_update()
            js.load_current_state([2,2,2], 1)

            steering = js.steering_angle if js.steering_angle != 0 else 10
            
            with lock:
                direction = (-1 if steering < 0 else 1) * (math.log10(abs(steering)/10))

            time.sleep(0.02) 

    except KeyboardInterrupt:
        ...
    
    with lock:
        running = False
        
    x.join()

def create_track():
    js = k_js.KartJoystickInput()

    js_positions = []

    sample_rate = 1/100

    try:
        print("Started Reading")
        while True:
            js.trigger_update()
            js.load_current_state(k_js.JS_SETUP, k_js.JS_DZ)
            js_positions.append(js.steering_angle)

            time.sleep(sample_rate) 

    except KeyboardInterrupt:
        df = pd.DataFrame(np.array(js_positions))
        df.to_csv("core/lib/old/pista_esempio.csv")

def test_track():
    global direction, running

    data = pd.read_csv("core/lib/old/pista_esempio.csv")

    positions = data.to_numpy(np.int32)[:, 1]

    differences = []

    x = threading.Thread(target=beep_routine)
    x.start()

    js = k_js.KartJoystickInput()
    try: 
        for i in positions:
            js.trigger_update()
            js.load_current_state([0,0,0], k_js.JS_DZ)

            steer_difference = js.steering_angle - i
            
            differences.append(abs(steer_difference))

            print(" "*150, end='\r')
            print(f"Target: {i}\t Joystick: {js.steering_angle}\t Difference: {steer_difference}\t Precision: {100-np.round(np.mean(np.array(differences)),2)}", end="\r")

            with lock:
                direction = (steer_difference/100)

            time.sleep(0.02) 

    except KeyboardInterrupt:
        ...
    
    with lock:
        running = False
        
    x.join()

    print(f"\nScore: {100-np.round(np.mean(np.array(differences)), 2)}")

if __name__ == "__main__":
    test_track()
    # create_track()