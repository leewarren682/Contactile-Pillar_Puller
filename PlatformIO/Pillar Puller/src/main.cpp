// CODE TO BE USED WITH THE TMC5160 MOTOR DRIVER AND THE PCB
#include <TMCStepper.h>
#include <AccelStepper.h>
#include <Adafruit_NAU7802.h>
#include <Arduino.h>
// #define EN_PIN    7 //enable ENABLE IS GROUNDED ON THE PCB - ACTIVE LOW
// CHANGE THESE PIN NUMBERS TO MATCH THE SCHEMATIC
#define DIR_PIN 20   //direction
#define STEP_PIN 21  //step


#define OPEN_BUTTON_PIN 15   // TEENSY PIN 16
#define CLOSE_BUTTON_PIN 16  // TEENSY PIN 15f
#define LIMIT_SWITCH_PIN 17  // TEENSY PIN 17
int openButtonState = 0;
int closeButtonState = 0;
int limitSwitchState = 0;
int speed = 1500;

// Variables to be plotted (force and platform position)
float mass;
float platformTravel;


// CHANGE THESE PIN NUMBERS TO MATCH THE SCHEMATIC
#define CS_PIN 10    //CS chip select
#define MOSI_PIN 11  //SDI/MOSI (ICSP: 4, Uno: 11, Mega: 51)
#define MISO_PIN 12  //SDO/MISO (ICSP: 1, Uno: 12, Mega: 50)
#define SCK_PIN 13   //CLK/SCK  (ICSP: 3, Uno: 13, Mega: 52)

#define R_SENSE 0.2f  //TMC5160: 0.075 Ohm

TMC5160Stepper tmc = TMC5160Stepper(CS_PIN, R_SENSE, MOSI_PIN, MISO_PIN, SCK_PIN);  //use software SPI
AccelStepper stepper = AccelStepper(stepper.DRIVER, STEP_PIN, DIR_PIN);
Adafruit_NAU7802 nau;

// Function to stop the motor. Sets idle current to 400mA.
void stop() {
  stepper.setSpeed(0);
  tmc.rms_current(400);
}

// Function to open the rig. Sets speed to constant.
void open() {
  tmc.rms_current(1000);  //1000mA RMS
  stepper.setSpeed(speed);
}

// Function to close the rig. Sets speed to constant.
void close() {
  tmc.rms_current(1000);  //1000mA RMS
  stepper.setSpeed(-speed);
}

// Function to open the rig to a specific force.
void open_till_force() {
  Serial.println("Opening till force 4");
  while (mass < 4) {
    open();
  }
}

void setup() {
  Serial.begin(115200);  //init serial port and set baudrate

  //set pins
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, LOW);  //direction: LOW or HIGH
  pinMode(STEP_PIN, OUTPUT);
  digitalWrite(STEP_PIN, LOW);
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);
  pinMode(MOSI_PIN, OUTPUT);
  digitalWrite(MOSI_PIN, LOW);
  pinMode(MISO_PIN, INPUT);
  digitalWrite(MISO_PIN, HIGH);
  pinMode(SCK_PIN, OUTPUT);
  digitalWrite(SCK_PIN, LOW);

  //Set driver config
  tmc.begin();
  tmc.toff(4);         //off time
  tmc.blank_time(24);  //blank time
  tmc.microsteps(16);     //16 microstep
  tmc.rms_current(400);  //Initial RMS of 400mA

  // Stepper settings
  stepper.setMaxSpeed(10000);
  stepper.setAcceleration(50000);
  stepper.setCurrentPosition(0);

  pinMode(OPEN_BUTTON_PIN, INPUT_PULLUP);
  pinMode(CLOSE_BUTTON_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);
  Serial.println("NAU7802");
  if (!nau.begin()) {
    Serial.println("Failed to find NAU7802");
  }

  nau.setLDO(NAU7802_3V3);
  nau.setRate(NAU7802_RATE_320SPS); //320 is fastest, 10 is slowest
  nau.setGain(NAU7802_GAIN_32); // Gain at 32. Don't change will mess with force readings.

  // Take 10 readings to flush out readings
  for (uint8_t i = 0; i < 10; i++) {
    while (!nau.available()) delay(1);
    nau.read();
  }

  while (!nau.calibrate(NAU7802_CALMOD_INTERNAL)) {
    Serial.println("Failed to calibrate internal offset, retrying!");
    delay(1000);
  }
}

void loop() {
  static uint32_t last_time = 0;
  uint32_t ms = millis();
  uint32_t Ms = micros();
  if ((ms - last_time) > 1000)  //run every 1s
  {
    last_time = ms;

    if (tmc.diag0_error()) { Serial.println(F("DIAG0 error")); }
    if (tmc.ot()) { Serial.println(F("Overtemp.")); }
    if (tmc.otpw()) { Serial.println(F("Overtemp. PW")); }
    if (tmc.s2ga()) { Serial.println(F("Short to Gnd A")); }
    if (tmc.s2gb()) { Serial.println(F("Short to Gnd B")); }
    if (tmc.ola()) { Serial.println(F("Open Load A")); }
    if (tmc.olb()) { Serial.println(F("Open Load B")); }
  }
  // Serial.print("reading from the nau");

  int32_t val = nau.read();
  float mass = (val - 3000.0) / 600.0;
  float platformTravel = (float(stepper.currentPosition()) / 3200.00) * 2.00;

// --- Print the values in serial format. So that it can be transformed into csv file.
  Serial.print(Ms);
  Serial.print(",");
  Serial.print(mass);
  Serial.print(",");
  Serial.println(platformTravel);
  Serial.println("Opening till force 4");




  openButtonState = digitalRead(OPEN_BUTTON_PIN);
  closeButtonState = digitalRead(CLOSE_BUTTON_PIN);

  if (openButtonState == LOW && closeButtonState == HIGH) {
    open();
  } else if (closeButtonState == LOW && openButtonState == HIGH) {
    close();
  } else {
    open_till_force();
  }
  stepper.runSpeed();
}
