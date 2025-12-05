/*
  Wheelchair Karting® AIKART_1® Rev 1.0

  === =============== STEERING LIBRARY ============== ===

      This implementation is used to control the kart 
      steering wheel with a 250w 12v DC motor and an
      800 step rotary encoder to achieve a full 
      drive-by-wire.

      Written by Ettore and Danilo Caccioli
                                          5/12/2025
  =======================================================
*/



#include <steering.h>

#ifndef STEERING_H_
#include <Arduino.h>
#include <utils.h>
#endif


/* IRQ Handler logic */
static void __interrupt_request(steering_motor_t *self){
  bool A = digitalRead(self->pin_layout.ENC_PHASE_A);
  bool B = digitalRead(self->pin_layout.ENC_PHASE_B);
  if (A != self->irq_phase_a) {
    if (A == B) self->position++;
    else self->position--;
  }
  self->irq_phase_a = A;
  self->angle = abs((self->position % self->max_range) * 360.0 / self->max_range);
}

/* *** Private Routines *** */

static void __turn_direction(steering_motor_t *self, int direction){
  PIN_DW(self->pin_layout.DRV_DS1, direction);
  PIN_DW(self->pin_layout.DRV_DS2, !direction);
}

static void __halt_motor(steering_motor_t *self){
  PIN_DW(self->pin_layout.DRV_DS1, LOW);
  PIN_DW(self->pin_layout.DRV_DS2, LOW);
}

static void __calibrate_motor(steering_motor_t *self){
  S_PNT_LN("CALIB:");
  S_PNT(self->angle);

  char __cmd;

  while (true){
    S_GCH(__cmd);

    if (!Serial.available()) continue;
    if (__cmd == 'd') break;

    switch (__cmd) {
      case 'z':               // set to 0 the step number
        self->position = 0;
        break;
      case 's':
        if (self->position < 0) S_PNT_LN("MAX RANGE LOWER THAN 0!");
        else self->max_range = self->position;
        break;
    }
    S_PNT_LN(self->angle);
  }

}

void __goto_angle(steering_motor_t *self,  int x){
  char __cmd;

  S_GCH(__cmd);

  while (true){
    S_GCH(__cmd);
    if (__cmd == 's') break;

    S_PNT_TB(x);
    S_PNT_LN(self->angle);

    if (x - self->tolerance <= self->angle && self->angle <= x + self->tolerance) {
      self->halt_motor(self);
      S_PNT_LN("ANGLE IN RANGE!");
      break;
    }

    if (self->angle < x) self->turn_direction(self, MOTOR_L);
    if (self->angle > x) self->turn_direction(self, MOTOR_R);

  }
}

/* Full Steering (Encoder/Motor) Pin/IRQ Initialization */
steering_motor_t attach_steering(
  int enc_phase_a,      // Rotary encoder Phase 1 Interrupt Pin (2 suggested)
  int enc_phase_b,      // Rotary encoder Phase 2 Interrupt Pin (3 suggested)
  int enc_vcc,          // Encoder 5V (13 suggested)
  int enc_gnd,          // Encoder Ground (12 suggested)
  int drv_ds1,          // Motor Driver Drain Signal 1  (9 suggested)
  int drv_ds2,          // Motor Driver Drain Signal 2  (8 suggested)
  int max_range,        // Max number of steps per revolution
  int tolerance,
  void (irq_trigger)()  // IRQ trigger function (Refer to docs)
){
  steering_motor_t motor = {
    0,
    0,
    0,
    max_range,
    0,
    tolerance,
    {
      enc_phase_a,
      enc_phase_b,
      enc_vcc,
      enc_gnd,
      drv_ds1,
      drv_ds2,
    },
    0,
    0,
    &__turn_direction,
    &__halt_motor,
    &__calibrate_motor,
    &__interrupt_request,
    &__goto_angle
  };

  PIN_M(enc_phase_a, INPUT_PULLUP);
  PIN_M(enc_phase_b, INPUT_PULLUP);
  PIN_M(enc_vcc, OUTPUT);
  PIN_M(enc_gnd, OUTPUT);
  PIN_M(drv_ds1, OUTPUT);
  PIN_M(drv_ds2, OUTPUT);

  PIN_DW(enc_vcc, HIGH);
  PIN_DW(enc_gnd, LOW);

  attachInterrupt(digitalPinToInterrupt(motor.pin_layout.ENC_PHASE_A), irq_trigger, CHANGE);

  return motor;
}
