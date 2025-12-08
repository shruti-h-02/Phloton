#include <Arduino.h>
#include <esp_adc_cal.h>
#include <Adafruit_NeoPixel.h>
#include <math.h>
//----Sd Card-----
#include <SPI.h>
#include <SD.h>
//----EC200------
#include <HardwareSerial.h>
HardwareSerial ec200uSerial(1);

// ====== Thermistor and ADC parameters ======
#define ADC_ATTEN ADC_ATTEN_DB_6
#define VREF 1100  // mV for esp_adc calibration
static esp_adc_cal_characteristics_t adc_chars;

const float SERIES_RESISTOR = 10000.0;     // 10k pull-up or pull-down resistor
const float NOMINAL_RESISTANCE = 10000.0;  // at 25°C
const float NOMINAL_TEMPERATURE = 25.0;    // 25°C (in Celsius)
const float BETA = 3434.0;                 // Beta value
const float VCC = 3300.0;                  // mV power supply for voltage divider
const int samples = 100;                   // Averaging to reduce noise
const int offset = 25;                     // mV calibration offset, tweak as needed

#define AMBIENT_PIN 8
#define COLDSINK_PIN 3
#define HEATSINK_PIN 9
#define FLASKTOP_PIN 11

// ====== Control, LED, and Current Sense ======
#define LED_PIN 16
#define BUTTON_PIN 10
#define NUM_LEDS 1
#define LED1_PIN 48
#define LID_OPEN_DETECT 46
#define HOTFAN_PIN 7
#define CSFAN_PIN 21

//-----SD CARD-------
#define SD_CS_PIN 42
#define SD_MOSI_PIN 41
#define SD_MISO_PIN 40
#define SD_SCK_PIN 39
//------EC200----------
#define PWRKEY_PIN 35

#define CSFAN_CURR_PIN 14
#define HSFAN_CURR_PIN 15

#define VOLTAGE_PIN 4
#define PIN_VBATISNS 2

#define DIVIDER_RATIO 11

#define SR_SER 13
#define SR_SRCLK 44
#define SR_RCLK 43

#define ADC_MAX 4095
#define GAIN 100.0

#define CSSHUNT_RESISTOR 0.3
#define HSSHUNT_RESISTOR 0.05

#define TEC_COLD_CTRL 1

Adafruit_NeoPixel led(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

volatile bool buttonPressed = false;

bool ec200uPoweredOn = false;

int ledState = 0;
int lastLidState = HIGH;
int lastButtonState = HIGH;

unsigned long prevNeoMillis = 0;
unsigned long prevShiftMillis = 0;
const int neoInterval = 300;
const int shiftInterval = 200;

int neoColorIndex = 0;
bool neoOnPhase = true;

int colors[6][3] = {
  { 255, 0, 0 },    // red
  { 0, 255, 0 },    // green
  { 0, 0, 255 },    // blue
  { 255, 255, 0 },  // yellow
  { 0, 255, 255 },  // cyan
  { 255, 0, 255 }
};

int shiftPhase = 0;
int shiftIndex = 0;

// ================= SD CARD STATUS FLAG =================
// This controls CREATE FILE only when LED mode is active.
bool sdInitialized = false;

void IRAM_ATTR buttonISR() {
  buttonPressed = true;
}
// --------EC200------------------------
void sendAT(String cmd) {
  Serial.println("\n>>> " + cmd);
  ec200uSerial.println(cmd);

  delay(300);

  unsigned long t = millis();
  while (millis() - t < 2000) {
    while (ec200uSerial.available()) {
      Serial.write(ec200uSerial.read());
    }
  }
}

void powerOnEC200U() {
  digitalWrite(PWRKEY_PIN, HIGH);
  delay(2000);
  digitalWrite(PWRKEY_PIN, LOW);
  Serial.println("Power ON sequence done. Waiting for module to boot...");
  //delay(8000);
  ec200uPoweredOn = true;
  //delay(3000);
}

void powerOffEC200U() {
  Serial.println("\n>>> Powering OFF EC200U...");
  digitalWrite(PWRKEY_PIN, HIGH);
  delay(5000);
  digitalWrite(PWRKEY_PIN, LOW);
  Serial.println("Power OFF sequence done.");

  delay(8000);
  ec200uPoweredOn = false;
}

// --- Modern averaged calibrated thermistor readout ---
float readThermistor(int pin) {
  uint32_t raw = 0;
  float voltage = 0.0;
  for (int i = 0; i < samples; i++) {
    raw += analogReadMilliVolts(pin);
    voltage += analogReadMilliVolts(pin);
    delay(1);
  }
  raw /= samples;
  voltage /= samples;
  voltage += offset;

  // Sensor disconnected check: tune these if needed
  const int threshold_low = 50;
  const int threshold_high = 4050;
  if (raw < threshold_low || raw > threshold_high) {
    return NAN;  // Not-a-Number: sensor not plugged in
  }
  float resistance = (voltage * SERIES_RESISTOR) / (VCC - voltage);

  float steinhart = resistance / NOMINAL_RESISTANCE;
  steinhart = log(steinhart);
  steinhart /= BETA;
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15);
  steinhart = 1.0 / steinhart;
  steinhart -= 273.15;
  return steinhart;
}

void printTemperature(float temp, const char* name) {
  if (isnan(temp)) {
    Serial.printf("%s -> Thermistor disconnected!\n", name);
  } else {
    Serial.printf("%s -> Temp: %.2f °C\n", name, temp);
  }
}
void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(static_cast<adc_attenuation_t>(ADC_ATTEN));
  led.begin();
  led.show();

  //---------------------------
  //calibrateACS();

  //  SD CARD INITIALIZATION
  Serial.println("\nInitializing SD card...");
  SPI.begin(SD_SCK_PIN, SD_MISO_PIN, SD_MOSI_PIN, SD_CS_PIN);

  if (!SD.begin(SD_CS_PIN, SPI)) {
    Serial.println("SD Card Mount Failed");
  } else {
    Serial.println("SD Card Ready");
    sdInitialized = true;
  }
  //---------EC200----------------------
  ec200uSerial.begin(115200, SERIAL_8N1, 18, 17);

  pinMode(PWRKEY_PIN, OUTPUT);
  digitalWrite(PWRKEY_PIN, LOW);
  //Serial.println("\nEC200U Debug Tool Ready!");
  //printMenu();
  Serial.println("Enter option number:");

  //-------------------------------------
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(BUTTON_PIN, buttonISR, FALLING);

  pinMode(LID_OPEN_DETECT, INPUT_PULLUP);
  pinMode(LED1_PIN, OUTPUT);
  pinMode(HOTFAN_PIN, OUTPUT);
  pinMode(CSFAN_PIN, OUTPUT);
  pinMode(TEC_COLD_CTRL, OUTPUT);

  pinMode(SR_SER, OUTPUT);
  pinMode(SR_SRCLK, OUTPUT);
  pinMode(SR_RCLK, OUTPUT);

  // ADC calibration
  esp_adc_cal_value_t efuse_config = esp_adc_cal_characterize(
    ADC_UNIT_1, ADC_ATTEN, ADC_WIDTH_BIT_12, VREF, &adc_chars);

  switch (efuse_config) {
    case ESP_ADC_CAL_VAL_EFUSE_VREF:
      Serial.println("Characterized using eFuse Vref");
      break;
    case ESP_ADC_CAL_VAL_EFUSE_TP:
      Serial.println("Characterized using Two Point Value stored in eFuse");
      break;
    case ESP_ADC_CAL_VAL_DEFAULT_VREF:
      Serial.println("Characterized using Default Vref (no eFuse)");
      break;
    case ESP_ADC_CAL_VAL_EFUSE_TP_FIT:
      Serial.println("Characterized using Two Point values and fitting curve coefficients stored in eFuse");
      break;
    default:
      Serial.println(F("ALERT, ADC calibration failed"));
  }
  Serial.printf("Gradient of ADC-Voltage curve: %d\n", adc_chars.coeff_a);
  Serial.printf("Offset of ADC-Voltage curve: %d\n", adc_chars.coeff_b);
  Serial.printf("Vref used by lookup table %d mV\n", adc_chars.vref);
}

void loop() {

  if (buttonPressed) {
    buttonPressed = false;
    ledState = !ledState;
    //    CREATE CSV FILE WHEN LEDSTATE BECOMES ACTIVE
    if (ledState == 1 && sdInitialized) {
      Serial.println("Button → Creating data.csv...");

      File file = SD.open("/data.csv", FILE_WRITE);
      if (!file) {
        Serial.println("Failed to create data.csv");
      } else {
        file.close();
        Serial.println("data.csv created!");
      }
    }
    // ========= POWER ON EC200U ON BUTTON PRESS =========
    //if (!ec200uPoweredOn) powerOnEC200U();
  }

  // --------- EC200U serial command menu ----------
  if (Serial.available()) {
    int option = Serial.parseInt();
    switch (option) {
      case 0:
        // Optional: Letting serial power on as well (redundant, since button does it). Remove if not desired.
        if (!ec200uPoweredOn) powerOnEC200U();
        else Serial.println("EC200U already powered ON.");
        break;
      case 16:
        if (ec200uPoweredOn) powerOffEC200U();
        else Serial.println("EC200U already powered OFF.");
        break;
      default:
        if (!ec200uPoweredOn) {
          Serial.println("EC200U is OFF. Power on by pressing the button.");
        } else {
          // Only allow AT commands if powered ON
          switch (option) {
            case 1: sendAT("AT"); break;
            case 2: sendAT("AT+CPIN?"); break;
            case 3: sendAT("AT+CIMI"); break;
            case 4: sendAT("AT+CSQ"); break;
            case 5: sendAT("AT+CREG?"); break;
            case 6: sendAT("AT+CEREG?"); break;
            case 7: sendAT("AT+COPS?"); break;
            case 8: sendAT("AT+QNWINFO"); break;
            case 9: sendAT("AT+QENG=\"servingcell\""); break;
            case 10: sendAT("AT+CGATT?"); break;
            case 11: sendAT("AT+CGDCONT?"); break;
            case 12: sendAT("AT+QIACT?"); break;
            case 13: sendAT("AT+QPING=1,\"8.8.8.8\""); break;
            case 14: sendAT("AT+GSN"); break;
            case 15: sendAT("AT+GMR"); break;
            default: Serial.println("Invalid option!"); break;
          }
        }
        break;
    }
    Serial.println("Enter option number (for EC200U):");
  }

  // Always parse URC messages from EC200U
  while (ec200uSerial.available()) {
    Serial.write(ec200uSerial.read());
  }
  //----------------------------------------------
  int currentLidState = digitalRead(LID_OPEN_DETECT);

  if (currentLidState != lastLidState) {
    if (currentLidState == HIGH) {
      Serial.println("LID OPEN");

      digitalWrite(HOTFAN_PIN, LOW);
      //digitalWrite(CSFAN_PIN, LOW);
      digitalWrite(LED1_PIN, LOW);

      led.clear();
      led.show();
      writeShift(0);
    } else {
      Serial.println("LID CLOSED");
    }
  }
  lastLidState = currentLidState;

  if (ledState == 1 && currentLidState == LOW) {
    digitalWrite(HOTFAN_PIN, HIGH);
    digitalWrite(CSFAN_PIN, HIGH);
    digitalWrite(LED1_PIN, HIGH);
    digitalWrite(LED1_PIN, HIGH);
    digitalWrite(TEC_COLD_CTRL, HIGH);

  } else {
    digitalWrite(HOTFAN_PIN, LOW);
    digitalWrite(CSFAN_PIN, LOW);
    digitalWrite(LED1_PIN, LOW);
    digitalWrite(TEC_COLD_CTRL, LOW);
  }

  if (ledState == 1 && currentLidState == LOW) {
    runMulticolor();
    runShiftPattern();
  } else {
    allOff();
  }

  static unsigned long prevMillis = 0;
  unsigned long now = millis();

  if (now - prevMillis >= 1000) {
    prevMillis = now;

    // ------ Temperature readings ------
    float tA = readThermistor(AMBIENT_PIN);
    float tC = readThermistor(COLDSINK_PIN);
    float tH = readThermistor(HEATSINK_PIN);
    float tF = readThermistor(FLASKTOP_PIN);

    printTemperature(tA, "Ambient");
    printTemperature(tC, "Cold Sink");
    printTemperature(tH, "Heat Sink");
    printTemperature(tF, "Flask Top");

    int adcCold = analogReadMilliVolts(CSFAN_CURR_PIN);
    float voltageCSFan = adcCold * (VCC / ADC_MAX);
    //float voltageCSFan = esp_adc_cal_raw_to_voltage(adcCold, &adc_chars); // V
    float currentCold = voltageCSFan / (GAIN * CSSHUNT_RESISTOR) / 1000;

    int adcHot = analogReadMilliVolts(HSFAN_CURR_PIN);
    float voltageHSFan = adcHot * (VCC / ADC_MAX);
    //float voltageHSFan = esp_adc_cal_raw_to_voltage(adcHot, &adc_chars); // V
    float currentHot = voltageHSFan / (GAIN * HSSHUNT_RESISTOR) / 1000;

    int adcValue = analogRead(VOLTAGE_PIN);
    float inputVoltage = (esp_adc_cal_raw_to_voltage(adcValue, &adc_chars)) * DIVIDER_RATIO;

    //------VBATISNS-------------------------------
    const int NUM_SAMPLES = 10;
    long sum_mv = 0;

    for (int i = 0; i < NUM_SAMPLES; i++) {
      sum_mv += analogReadMilliVolts(PIN_VBATISNS);
      delay(10);
    }

    int adcisns = sum_mv / NUM_SAMPLES;
    float voltageISNS = adcisns / 1000.0;
    float currentisns = (adcisns - 1650) / 132.0;
    //------------------------------------------------
    Serial.printf("Current CSFAN: %.3f A\n", currentCold);
    Serial.printf("Current HSFAN: %.3f A\n", currentHot);
    Serial.printf("CurrentISNS: %.3f A\n", currentisns);
    Serial.printf("Voltage: %.3f V\n", inputVoltage);
    //Serial.printf("VoltageHS: %.3f V\n", voltageHSFan);
    //Serial.printf("VoltageCS: %.3f V\n", voltageCSFan);

    //Serial.printf("ADCCold: %d\n", adcCold);
    //Serial.printf("ADCHot: %d\n", adcHot);
    //Serial.printf("ADCISNS: %d\n", adcValue);
    //Serial.printf("ADCISNS(mV): %d\n", adcisns);
  }
}

void runMulticolor() {
  unsigned long now = millis();
  if (now - prevNeoMillis < neoInterval) return;
  prevNeoMillis = now;

  if (neoOnPhase) {
    int r = colors[neoColorIndex][0];
    int g = colors[neoColorIndex][1];
    int b = colors[neoColorIndex][2];
    led.setPixelColor(0, led.Color(r, g, b));
  } else {
    led.clear();
    neoColorIndex++;
    if (neoColorIndex >= 6) neoColorIndex = 0;
  }

  led.show();
  neoOnPhase = !neoOnPhase;
}

void runShiftPattern() {
  unsigned long now = millis();
  if (now - prevShiftMillis < shiftInterval) return;
  prevShiftMillis = now;

  if (shiftPhase == 0) {
    writeShift(shiftIndex + 1);
    shiftIndex++;
    if (shiftIndex >= 8) shiftPhase = 1;
  } else if (shiftPhase == 1) {
    writeShift(8);
    shiftPhase = 2;
  } else if (shiftPhase == 2) {
    writeShift(shiftIndex - 1);
    shiftIndex--;
    if (shiftIndex <= 0) shiftPhase = 0;
  }
}

void writeShift(int count) {
  byte value = 0;
  for (int i = 0; i < count; i++) value |= (1 << i);
  shiftOut(SR_SER, SR_SRCLK, MSBFIRST, value);
  latchUpdate();
}

void latchUpdate() {
  digitalWrite(SR_RCLK, HIGH);
  delayMicroseconds(5);
  digitalWrite(SR_RCLK, LOW);
}

void allOff() {
  shiftOut(SR_SER, SR_SRCLK, MSBFIRST, 0x00);
  latchUpdate();
  led.clear();
  led.show();
}