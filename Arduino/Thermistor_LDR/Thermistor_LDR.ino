
#include <math.h>

#define COMM_RATE 115200
#define LOOP_DELAY_MS 23
#define SMOOTHING 0.75
#define V_REF 5.2
#define OHM_REF 10000
#define C_KELVIN_OFFSET 273.15

// https://www.skyeinstruments.com/wp-content/uploads/Steinhart-Hart-Eqn-for-10k-Thermistors.pdf
#define A  0.001125308852122 
#define B  0.000234711863267 
#define C  0.000000085663516

#define LDR_THRESHHOLD 10


float ldr, thermistor;

float read_ldr() {
  int sig = analogRead(A1);
  int ref = analogRead(A2);
  // float value = V_REF * float(sig) / float(ref); // voltage, VDC
  float value = OHM_REF / (float(ref) / float(sig) - 1);  // resistance, ohms
  return(value);
}

float read_thermistor() {
  // NTC 10K with 10k resistor in series
  int sig = analogRead(A0);
  int ref = analogRead(A2);
  // float value = V_REF * float(sig) / float(ref); // voltage, VDC
  float value = OHM_REF / (float(ref) / float(sig) - 1);  // resistance, ohms
  // use Steinhart-Hart approximation to get temperature
  value = log(value);
  value = 1/(A + B*value + C*value*value*value) - C_KELVIN_OFFSET;
  return(value);
}

float smoothing(float value, float reading) {
  value *= SMOOTHING;
  value += reading * (1-SMOOTHING);
  return(value);
}

void setup() {
  Serial.begin(COMM_RATE);
  ldr = read_ldr();
  thermistor = read_thermistor();
}

void loop() {
  ldr = smoothing(ldr, read_ldr());
  thermistor = smoothing(thermistor, read_thermistor());

  Serial.print(micros() * 1.0e-6, 3);
  Serial.print("  thermistor (A0): ");
  Serial.print(thermistor);
  Serial.print("  LDR (A1): ");
  Serial.println(ldr, 0);

  if (ldr >= LDR_THRESHHOLD)
    digitalWrite(LED_BUILTIN, HIGH);
  else
    digitalWrite(LED_BUILTIN, LOW);

  delay(LOOP_DELAY_MS);
}
