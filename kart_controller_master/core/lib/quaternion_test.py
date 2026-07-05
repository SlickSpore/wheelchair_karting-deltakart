from lib.YbImuLib import YbImuSerialLib as ys
from math import atan2, degrees
import os
import time

class KalmanRoll:
    def __init__(self):
        # Stati: [angolo, bias]
        self.angle = 0.0
        self.bias = 0.0
        
        # Matrice di covarianza dell'errore
        self.P = [[0.0, 0.0],
                  [0.0, 0.0]]
        
        # Parametri di rumore del filtro
        self.Q_angle = 0.001  
        self.Q_bias = 0.003   
        self.R_measure = 0.03 

    def update(self, new_angle, new_rate, dt):
        # 1. PREDIZIONE
        rate = new_rate - self.bias
        self.angle += dt * rate

        self.P[0][0] += dt * (dt * self.P[1][1] - self.P[0][1] - self.P[1][0] + self.Q_angle)
        self.P[0][1] -= dt * self.P[1][1]
        self.P[1][0] -= dt * self.P[1][1]
        self.P[1][1] += self.Q_bias * dt

        # 2. CORREZIONE
        y = new_angle - self.angle  

        S = self.P[0][0] + self.R_measure
        K0 = self.P[0][0] / S
        K1 = self.P[1][0] / S

        self.angle += K0 * y
        self.bias  += K1 * y

        p00_temp = self.P[0][0]
        p01_temp = self.P[0][1]

        self.P[0][0] -= K0 * p00_temp
        self.P[0][1] -= K0 * p01_temp
        self.P[1][0] -= K1 * p00_temp
        self.P[1][1] -= K1 * p01_temp

        return self.angle

def connect_imu(serial_port):
    bot = ys.YbImuSerial(serial_port, debug=True)
    bot.create_receive_threading()
    return bot    

def get_bias(bot):
    return sum(bot.get_gyroscope_data()[2] for _ in range(500)) / 500

def init_headset_and_frame():
    serials = ["/dev/ttyUSB1", "/dev/ttyUSB2"]

    return connect_imu(serial_port=serials[0]), connect_imu(serial_port=serials[1])

class KartHeadsetInput2:
    def __init__(self, time_interval):
        self.time_interval = time_interval
        self.turn_threshold = 0.15 

        self.kalman = KalmanRoll()
        self.final_roll = 0.0
        self.bot1, self.bot2 = init_headset_and_frame()
        self.bias = get_bias(self.bot1)

    def get_headset_postition(self, max_angle=40):
        # Lettura Quaternioni
        w_f, x_f, y_f, z_f = tuple(self.bot1.get_imu_quaternion_data())
        w_h, x_h, y_h, z_h = tuple(self.bot2.get_imu_quaternion_data())

        # Lettura Giroscopi
        gx_f, gy_f, gz_f = tuple(self.bot1.get_gyroscope_data())
        gx_h, gy_h, gz_h = tuple(self.bot2.get_gyroscope_data())

        # Quaternione Relativo (Differenziale)
        w_r = w_f*w_h + x_f*x_h + y_f*y_h + z_f*z_h  
        x_r = w_f*x_h - x_f*w_h - y_f*z_h + z_f*y_h 
        y_r = w_f*y_h + x_f*z_h - y_f*w_h - z_f*x_h  
        z_r = w_f*z_h - x_f*y_h + y_f*x_h - z_f*w_h  

        # Compensazione Bias Yaw e calcolo Rollio differenziale
        gz_f_calibrato = gz_f - self.bias
        gx_r = gx_f - gx_h

        r_roll_q = degrees(atan2(2 * (w_r*x_r + y_r*z_r), 1 - 2 * (x_r**2 + y_r**2)))

        # Gating anti-centrifuga adattivo
        if abs(gz_f_calibrato) > self.turn_threshold:
            self.kalman.R_measure = 1000.0  # In curva: escludi la correzione del quaternione
        else:
            self.kalman.R_measure = 0.03    # In rettilineo: usa il quaternione per correggere il drift

        # Roll generico e Fusione dei dati con Filtro di Kalman
        r_roll_k = self.kalman.update(r_roll_q, gx_r, self.time_interval)

        r_roll_q = (-1 if r_roll_q < 0 else 1) * min(100, (100 * abs(r_roll_q)/max_angle))
        r_roll_k = (-1 if r_roll_k < 0 else 1) * min(100, (100 * abs(r_roll_k)/max_angle))

        return r_roll_q, r_roll_k

if __name__ == "__main__":

    hs = KartHeadsetInput2(0.05)

    try:
        while True:
            quaternion, kalman = hs.get_headset_postition()            

            print(" "*80, end='\r')
            print(f"Q_Roll (Raw): {round(quaternion, 3)}° | Fused_Roll (Kalman): {round(kalman, 3)}°", end='\r')

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopped")