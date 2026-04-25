#include <Arduino.h>
#include <Servo.h>

#define BAUD_RATE 115200
#define PACKET_SIZE 10
#define HEADER 0x4545
#define FOOTER 0x4646

#define DIR_PIN 3
#define PWM_PIN 9

#define STOP_PIN 7

#define set_steer_direction_d(a, b) PORTD = b ? (PORTD | (b<<(a))) : (PORTD & (b<<(a)))
#define check_safety(a) ((PIND&(1<<a))>>a)

uint8_t buffer[PACKET_SIZE];

struct
{
  uint16_t direction;
  uint16_t velocity;
  uint16_t x;
} steering_data;

struct
{
  float acc1;
  float acc2;
  float acc3;
  float temp;
  int16_t footer;
} core_responce;


void setup(){
  Serial.begin(BAUD_RATE);

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STOP_PIN, INPUT);
  pinMode(13, OUTPUT);

  set_steer_direction_d(DIR_PIN, LOW);
  analogWrite(PWM_PIN, 0);

  while (!Serial.available());
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

int receive_packet(uint8_t* buf){
  if (Serial.available()){
    int number = Serial.readBytesUntil('\n', buf, PACKET_SIZE);

    if (__gt_word(0, buf) == HEADER && __gt_word(PACKET_SIZE-2, buf) == FOOTER){
      return number;
    }
  }
  return 0;
}


void loop() {
    int s = receive_packet(buffer);

    digitalWrite(LED_BUILTIN, check_safety(STOP_PIN));

    steering_data.direction = __gt_word(2, buffer);
    steering_data.velocity = check_safety(STOP_PIN) ? 0 : __gt_word(4, buffer);
    steering_data.x = __gt_word(6, buffer);

    if (!s) return;

    core_responce = {
      0.0,
      0.0,
      0.0,
      0.0,
      0x0a47
    };

    analogWrite(PWM_PIN, steering_data.velocity);

    set_steer_direction_d(DIR_PIN, steering_data.direction);

    Serial.write((uint8_t *)&core_responce, sizeof(core_responce));
    serial_flush();
}