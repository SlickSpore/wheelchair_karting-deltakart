#include <Arduino.h>
#include <Servo.h>

#define BAUD_RATE 9600

#define PACKET_SIZE 10
#define HEADER 0x4545
#define FOOTER 0x4646

#define STEERING_S1 33
#define STEERING_S2 31
#define STEERING_SP 9

#define MOTOR_HALT 0x0000
#define MOTOR_LEFT 0x0064
#define MOTOR_RIGHT 0x0032

uint8_t buffer[PACKET_SIZE];
uint8_t responce[] = {0x47, 0x47, 0x0a};
Servo velocity_controller;

struct
{
  uint16_t direction;
  uint16_t velocity;
  uint16_t x;
} steering_data;

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

void setup(){
  Serial.begin(BAUD_RATE);
  while (!Serial.available());

  pinMode(STEERING_S1, OUTPUT);
  pinMode(STEERING_S2, OUTPUT);

  velocity_controller.attach(STEERING_SP);

  Serial.println("run_due version 2 booting!");
}

void serial_flush(){
  while (Serial.available() > 0) 
  Serial.read();
}

uint16_t __gt_word(int x, uint8_t* buffer){
  if (x > PACKET_SIZE) return -1;
  if (x < 0) return -1;
  if ((x%2) != 0) return -1;
  return ((buffer[x] << 8) | buffer[x+1]);
}

int recieve_packet(uint8_t* buf){
  if (Serial.available()){
    int number = Serial.readBytesUntil('\n', buf, PACKET_SIZE);

    if (__gt_word(0, buf) == HEADER && __gt_word(PACKET_SIZE-2, buf) == FOOTER){
      return number;
    }
  }
  return 0;
}

void loop() {
    int s = recieve_packet(buffer);

    steering_data.direction = __gt_word(2, buffer);
    steering_data.velocity = __gt_word(4, buffer);
    steering_data.x = __gt_word(6, buffer);

    if (!s) return;

    switch (steering_data.direction){
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

    velocity_controller.write(steering_data.velocity);

    Serial.write(responce, sizeof(responce));
    serial_flush();
}