#include <Arduino.h>
#include <Servo.h>

#define BAUD_RATE 115200
#define SERIAL_SLEEP_INTERVAL 1000
#define PACKET_SIZE 10

#define STEERING_S1 33
#define STEERING_S2 31

#define MOTOR_HALT 0x00
#define MOTOR_LEFT 0x32
#define MOTOR_RIGHT 0x64

#define MOTOR_DIRECTION_ADDR 0x02
#define MOTOR_VELOCITY_ADDR 0x04

typedef struct {
  uint16_t steering_direction;
  uint16_t angular_velocity;
} interface_command_t;

uint8_t frame[PACKET_SIZE];
interface_command_t command;

Servo velocity_pot;


/*

  Serial Reading/Writing Routines

*/


uint16_t get_value_from_frame(uint8_t frame[PACKET_SIZE], int pos){
  if ((pos%2)!=0) return 0;
  if (pos > PACKET_SIZE - 1) return 0;
  if (pos < 0) return 0;
  return (frame[pos] << 8) | frame[pos+1];
}

void retrieve_packet(interface_command_t* command) {
  static uint8_t buffer[PACKET_SIZE];
  static uint8_t idx = 0; 

  while (Serial.available()) {
    uint8_t b = Serial.read();

    if (idx == 0 && b != 0x45) continue;
    if (idx == 1 && b != 0x45) {
      idx = 0;
      continue;
    }

    buffer[idx++] = b;
    if (idx != PACKET_SIZE) continue;
    if (buffer[PACKET_SIZE - 2] != 0x46 || buffer[PACKET_SIZE - 1] != 0x46) break;
    
    command->angular_velocity = get_value_from_frame(buffer, MOTOR_VELOCITY_ADDR);
    command->steering_direction = get_value_from_frame(buffer, MOTOR_DIRECTION_ADDR);

    idx = 0;
    break;
  }  
}

void keep_alive(){
  unsigned long this_time = millis();
  static unsigned long last_time = 0;

  if (this_time-last_time >= SERIAL_SLEEP_INTERVAL){
    Serial.print(this_time/1000);
    Serial.print(command.angular_velocity, HEX);
    Serial.println(command.steering_direction, HEX);
    last_time = this_time;
  }

}


/*

  Kart Control Routines

*/



void steer_left(){
  digitalWrite(STEERING_S1, HIGH);
  digitalWrite(STEERING_S2, LOW);
}

void steer_right(){
  digitalWrite(STEERING_S1, LOW);
  digitalWrite(STEERING_S2, HIGH);
}

void steer_halt(){
  digitalWrite(STEERING_S1, LOW);
  digitalWrite(STEERING_S2, LOW);
}


/*

  Main Loop

*/


void setup(){
  Serial.begin(BAUD_RATE);
  while (Serial.available()<0);;
  Serial.println("kart_controller_unit version 3.0 booting up!");
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop(){
  keep_alive();

  retrieve_packet(&command);
  digitalWrite(LED_BUILTIN, command.steering_direction == 0x6161 ? HIGH: LOW);

  switch (command.steering_direction){
    case MOTOR_HALT:
      steer_halt();
      break;
    case MOTOR_LEFT:
      steer_left();
      break;
    case MOTOR_RIGHT:
      steer_right();
      break;
    default:
      break;
  }

}