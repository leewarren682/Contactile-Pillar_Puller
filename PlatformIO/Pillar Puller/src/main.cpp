// CODE TO BE USED WITH THE TMC5160 MOTOR DRIVER AND THE PCB
#include <TMCStepper.h>
#include <AccelStepper.h>
#include <Adafruit_NAU7802.h>
#include <Arduino.h>
#include <bounce2.h>
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

// Variables for debouncing
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50; // milliseconds
int lastSwitchState = LOW;
int switchState;

// Variables to be plotted (force and platform position)
float mass;
float platformTravel;

// Bounce2 library button initialization
// INSTANTIATE A Button OBJECT
Bounce2::Button limitSwitch = Bounce2::Button();


// CHANGE THESE PIN NUMBERS TO MATCH THE SCHEMATIC
#define CS_PIN 10    //CS chip select
#define MOSI_PIN 11  //SDI/MOSI (ICSP: 4, Uno: 11, Mega: 51)
#define MISO_PIN 12  //SDO/MISO (ICSP: 1, Uno: 12, Mega: 50)
#define SCK_PIN 13   //CLK/SCK  (ICSP: 3, Uno: 13, Mega: 52)

#define R_SENSE 0.2f  //TMC5160: 0.075 Ohm

TMC5160Stepper tmc = TMC5160Stepper(CS_PIN, R_SENSE, MOSI_PIN, MISO_PIN, SCK_PIN);  //use software SPI
AccelStepper stepper = AccelStepper(stepper.DRIVER, STEP_PIN, DIR_PIN);
Adafruit_NAU7802 nau;

// Create a low pass filter class.
class LowPassFilter {
  public:
    LowPassFilter(float alpha) {
      _alpha = alpha;
      _first = true;
    }

    float filter(float value) {
      if (_first) {
        _first = false;
        _filtered_value = value;
      } else {
        _filtered_value = _alpha * value + (1 - _alpha) * _filtered_value;
      }
      return _filtered_value;
    }

  private:
    float _alpha;
    float _filtered_value;
    bool _first;
};

// Function to read and print data
void readAndPrintData() {
  int32_t val = nau.read();
  float mass = (val - 3000.0) / 600.0;
  float platformTravel = (float(stepper.currentPosition()) / 3200.00) * 2.00;
  float filtered_mass = 0;

  // Filter the force values.
  LowPassFilter filter(0.8);
  filter.filter(mass);

  // Print the values in serial format
  Serial.print(millis());
  Serial.print(",");
  Serial.print(mass);
  Serial.print(",");
  Serial.print(platformTravel);
  Serial.print(",");
  Serial.println(filter.filter(mass));
}

// Function to stop the motor. Sets idle current to 400mA.
void stop() {
  stepper.setSpeed(0);
  tmc.rms_current(400);
  readAndPrintData();
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

// Function to open the rig to a specific position provided in millimeters.
void move_to_position(int desired_position) {

  float converted_position = (desired_position / 2.00) * 3200.00;
  stepper.moveTo(converted_position);
  stepper.setSpeed(speed);

  // Continuously run the motor until a force condition is met.
  while (stepper.distanceToGo() != 0) {
    readAndPrintData();
    stepper.run();
  }
  stop();
}

// Function to open the rige to a specific force provided in Newtons.
void move_to_force(int desired_force) {
  while (mass < desired_force) {
    open();
    stepper.run();
    readAndPrintData();
  }
  stop(); // Stop the motor after the desired force is reached.
}

void readLimitSwitch() {
  limitSwitch.update();
  int reading = digitalRead(LIMIT_SWITCH_PIN);
  lastSwitchState = reading;
}

// Function to use a homing switch to find the zero position.
void home() {
  limitSwitchState = digitalRead(LIMIT_SWITCH_PIN);
  while (limitSwitchState == HIGH) {
    stepper.setSpeed(speed);
    stepper.run();
    limitSwitchState = digitalRead(LIMIT_SWITCH_PIN);
    readLimitSwitch(); // Continuously read the switch state
    readAndPrintData();
  
    if (limitSwitchState == LOW) {
      break;
    }
  }

  SerialUSB1.println("Limit switch is pressed, stopping and breaking out of the loop.");
  stop();
  SerialUSB1.println("Stopped. Setting the current position to 24.");
  stepper.setCurrentPosition(0);
  SerialUSB1.println("Moving to position 0.");
  move_to_position(-22);
  stepper.setCurrentPosition(0);
  SerialUSB1.println("Homing complete.");
}

// Function to detect if the rig has reached a failure force.
// If the current force is lower than the previous force by 50%, stop the motor.
boolean break_detection() {
  float previous_mass = mass;
  SerialUSB1.print("Previous mass: ");
  SerialUSB1.println(previous_mass);
  readAndPrintData();
  SerialUSB1.print("Current mass: ");
  SerialUSB1.println(mass);
  if (mass < (previous_mass * 0.8)) {
    SerialUSB1.println("Force has decreased by 1.2x, stopping the motor.");
    stop();
    return true;
  } else {
    return false;
  }
}

// Function which opens the rig until a failure force is detected or the limit switch is hit.
void open_until_break() {
  while (break_detection() == false) {
    // open();
    // stepper.run();
  }
  SerialUSB1.println("BREAK HAS BEEN DETECTED, STOPPING.");
  stop();
}

// Function to process the commands received from the serial port.
void processCommand(String command) {

  if (command.startsWith("open")) { // Find a command to remove whitespace
    // Run the open command until another command is received.
    while (Serial.available() == 0) {
      open();
      stepper.run();
      readAndPrintData();
    }
  } else if (command.startsWith("close")) {
    while (Serial.available() == 0) {
      close();
      stepper.run();
      readAndPrintData();
    }
  } else if (command.startsWith("stop")) {
    stop();
  } else if (command.indexOf("move_to_position") != -1) {
    int desired_position = command.substring(strlen("move_to_position")).toInt();
    while (Serial.available() == 0) {
      move_to_position(desired_position);
      readAndPrintData();
    }
  } else if (command.indexOf("move_to_force") != -1) {
      int desired_force = command.substring(strlen("move_to_force")).toInt();
      while (Serial.available() == 0) {
        move_to_force(desired_force);
        readAndPrintData();
      }
  } else if (command.startsWith("home")) {
      home();
  } else if (command.startsWith("open_until_break")) {
      open_until_break();
  } else {
    Serial.println("Invalid command");
  }
}



void setup() {
  Serial.begin(115200);  //init serial port and set baudrate
  SerialUSB1.begin(115200);

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

  // SELECT ONE OF THE FOLLOWING :
  // 1) IF YOUR BUTTON HAS AN INTERNAL PULL-UP
  // button.attach( BUTTON_PIN ,  INPUT_PULLUP ); // USE INTERNAL PULL-UP
  // 2) IF YOUR BUTTON USES AN EXTERNAL PULL-UP
  limitSwitch.attach(LIMIT_SWITCH_PIN, INPUT_PULLUP);

  // Debounce interval in milliseconds
  limitSwitch.interval(5);

  // Indicate that low state is physically pressing the button
  limitSwitch.setPressedState(LOW);

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
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP); // Homing switch
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
  // Update the limit switch every loop.
  limitSwitch.update();

  static uint32_t last_time = 0;
  uint32_t ms = millis();
  uint32_t Ms = micros();

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }


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

  // Read and print the data
  readAndPrintData();

  openButtonState = digitalRead(OPEN_BUTTON_PIN);
  closeButtonState = digitalRead(CLOSE_BUTTON_PIN);
  limitSwitchState = digitalRead(LIMIT_SWITCH_PIN);

  // // Print the state of the limit switch
  // SerialUSB1.print("Limit Switch is ");
  // if (limitSwitchState == HIGH) {
  //   SerialUSB1.println("HIGH");
  // } else {
  //   SerialUSB1.println("LOW");
  // }

  if (openButtonState == LOW && closeButtonState == HIGH) {
    open();
  } else if (closeButtonState == LOW && openButtonState == HIGH) {
    close();
  } else {
    stop();
  }
  stepper.runSpeed();
}
