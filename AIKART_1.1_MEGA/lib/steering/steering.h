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

/* Init Params and Global */
#define MOTOR_R 1
#define MOTOR_L !MOTOR_R


/* Encoder/Motor Pin Codes */
struct steering_pins{
  int ENC_PHASE_A,
      ENC_PHASE_B,
      ENC_VCC,
      ENC_GND,
      DRV_DS1,
      DRV_DS2;
};

/* Motor class structure with all params and children routines */
struct steering_motor_t
{
  float angle;
  volatile long position;
  long last_position;
  int max_range, rotor_drift, tolerance;
  steering_pins pin_layout;
  bool mode;
  volatile bool irq_phase_a;

  // Children Routines
  void (*turn_direction)(steering_motor_t *self, int direction); // Signals the motor to rotate in the specified direction.
  void (*halt_motor)(steering_motor_t *self);                    // Signals the motor to stop rotating. 
  void (*calibrate_motor)(steering_motor_t *self);              // Starts a calibration routine, by now it's purely serial based. (Z: Pos=0, S: MAX_POS=x, D: Quit)
  void (*interrupt_request)(steering_motor_t *self);            // Handles the occurring interrupt request    
  void (*goto_angle)(steering_motor_t *self, int x);
};

extern steering_motor_t attach_steering(
  int enc_phase_a,      // Rotary encoder Phase 1 Interrupt Pin (2 suggested)
  int enc_phase_b,      // Rotary encoder Phase 2 Interrupt Pin (3 suggested)
  int enc_vcc,          // Encoder 5V (13 suggested)
  int enc_gnd,          // Encoder Ground (12 suggested)
  int drv_ds1,          // Motor Driver Drain Signal 1  (9 suggested)
  int drv_ds2,          // Motor Driver Drain Signal 2  (8 suggested)
  int max_range,        // Max number of steps per revolution
  int tolerance,
  void (irq_trigger)()  // IRQ trigger function (Refer to docs)
);
