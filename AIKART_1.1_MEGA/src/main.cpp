
/*
  Wheelchair Karting® AIKART_1® Rev 1.0
  === ================ Main Controller =============== ===

      This is the second version of the code used to 
      control an Arduino Mega 2560 R3 to implement a 
      full drive-by-wire kart.
                                          5/12/2025
  =======================================================

  TODO:
    -IMU DATASHEET -> https://docs.google.com/spreadsheets/d/1IuBSfexS8KSehjWDmZlVP3vLu-mIEJwa/edit?gid=477402796#gid=477402796
*/

#include <Arduino.h>
#include <utils.h>
#include <steering.h>

#define PIN_PHASE_A 2
#define PIN_PHASE_B 3


void irq_handler();

steering_motor_t motor = attach_steering(PIN_PHASE_A,PIN_PHASE_B, 13, 12, 8, 9, 800, 10, irq_handler);

void setup() {
  Serial.begin(9600);
}

void loop() {
}

void irq_handler(){
  motor.interrupt_request(&motor);
}