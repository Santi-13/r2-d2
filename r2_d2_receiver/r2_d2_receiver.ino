#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include "BluetoothSerial.h" // <--- LIBRERÍA NATIVA

// --- CONFIGURACIÓN BLUETOOTH ---
BluetoothSerial SerialBT;
const char* deviceName = "R2D2_CONTROL_BT"; // Nombre que verás en la PC

// --- CONFIGURACIÓN DE PINES (Tus pines originales) ---
#define PIN_STEP_1 14
#define PIN_DIR_1 12
#define PIN_STEP_2 26
#define PIN_DIR_2 27

#define PIN_CUERPO 2
#define PIN_OJOS  4
#define PIN_TORRETA 16
#define PIN_CUELLO_LARGA 17

#define NUM_LEDS_CUERPO 7
#define NUM_LEDS_OJO    8  
#define NUM_LEDS_TORRETA 8 
#define NUM_LEDS_CUELLO 8

// --- OBJETOS DE HARDWARE ---
Adafruit_NeoPixel tiraCuerpo(NUM_LEDS_CUERPO, PIN_CUERPO, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel tiraOjos(NUM_LEDS_OJO, PIN_OJOS, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel tiraTorreta(NUM_LEDS_TORRETA, PIN_TORRETA, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel tiraCuello(NUM_LEDS_CUELLO, PIN_CUELLO_LARGA, NEO_GRB + NEO_KHZ800);

AccelStepper motor1(AccelStepper::DRIVER, PIN_STEP_1, PIN_DIR_1);
AccelStepper motor2(AccelStepper::DRIVER, PIN_STEP_2, PIN_DIR_2);

const int PASOS_PARA_90_GRADOS = 200; 
StaticJsonDocument<200> doc;

// --- VARIABLES DE ESTADO ---

// 1. Cuerpo (Lógica Individual Verde/Azul)
struct BodyLedState {
  uint8_t r, g, b;   
  uint8_t target;    
};
BodyLedState bodyLeds[NUM_LEDS_CUERPO]; 
unsigned long lastBodyUpdate = 0;       

// 2. Ojos (Talking)
bool isTalking = false;
unsigned long lastBlink = 0;
bool eyeState = false;

// 3. Torreta (Parpadeo Blanco ON/OFF) <-- MODIFICADO
unsigned long lastTurretBlink = 0;
bool turretState = false;  // false = apagado, true = encendido

// 4. Cuello (Naranja-Amarillo)
unsigned long lastNeckFade = 0;
int neckGreenVal = 100; 
int neckDir = 2;

// --- COMANDOS JSON ---
void processCommand() {
  const char* device = doc["device"];
  const char* action = doc["action"];

  // (Tu lógica de comandos idéntica)
  if (strcmp(device, "eye") == 0) {
    if (strcmp(action, "talk") == 0) isTalking = true;
    else if (strcmp(action, "silent") == 0) {
      isTalking = false;
      for(int i=0; i<NUM_LEDS_TORRETA; i++) tiraTorreta.setPixelColor(i, 0);
      tiraTorreta.show();
    }
  }
  else if (strcmp(device, "motor") == 0) {
    if (strcmp(action, "left") == 0) motor1.move(PASOS_PARA_90_GRADOS); 
    else if (strcmp(action, "right") == 0) motor1.move(-PASOS_PARA_90_GRADOS);
    else if (strcmp(action, "spin") == 0) {
       motor1.move(PASOS_PARA_90_GRADOS);
       motor2.move(-PASOS_PARA_90_GRADOS);
    }
  }
}

void setup() {
  Serial.begin(115200); // Para debug USB
  
  // --- INICIO BLUETOOTH ---
  SerialBT.begin(deviceName); 
  Serial.println("Bluetooth Iniciado! Busca 'R2D2_CONTROL_BT' en tu PC.");

  // --- INICIO HARDWARE (Copia tu setup de hardware aquí) ---
  randomSeed(analogRead(0)); 
  tiraCuerpo.begin(); tiraCuerpo.show();
  tiraOjos.begin();   tiraOjos.show();
  tiraTorreta.begin(); tiraTorreta.show();
  tiraCuello.begin();  tiraCuello.show();
  
  // Inicializar cuerpo random...
  for (int i = 0; i < NUM_LEDS_CUERPO; i++) {
    if (random(2) == 0) bodyLeds[i] = {0, 255, 0, 1}; 
    else bodyLeds[i] = {0, 0, 255, 0}; 
    tiraCuerpo.setPixelColor(i, tiraCuerpo.Color(bodyLeds[i].r, bodyLeds[i].g, bodyLeds[i].b));
  }
  tiraCuerpo.show();

  motor1.setMaxSpeed(1000); motor1.setAcceleration(500);
  motor2.setMaxSpeed(1000); motor2.setAcceleration(500);
}

// --- LOGICA LEDS ---

void updateBody() {
  if (millis() - lastBodyUpdate > 50) {
    lastBodyUpdate = millis();

    for (int i = 0; i < NUM_LEDS_CUERPO; i++) {
      if (bodyLeds[i].target == 0) { // Ir a Verde
        if (bodyLeds[i].b > 0) bodyLeds[i].b -= 10;   
        if (bodyLeds[i].g < 255) bodyLeds[i].g += 10; 
      } else { // Ir a Azul
        if (bodyLeds[i].g > 0) bodyLeds[i].g -= 10;   
        if (bodyLeds[i].b < 255) bodyLeds[i].b += 10; 
      }

      // Flash Blanco en transición
      if (bodyLeds[i].g > 200 && bodyLeds[i].b > 200) {
        bodyLeds[i].r = 255; 
      } else {
        bodyLeds[i].r = 0;
      }

      tiraCuerpo.setPixelColor(i, tiraCuerpo.Color(bodyLeds[i].r, bodyLeds[i].g, bodyLeds[i].b));

      // Cambio de objetivo
      if (bodyLeds[i].target == 0 && bodyLeds[i].g >= 255 && bodyLeds[i].b == 0) {
        bodyLeds[i].target = 1; 
      } else if (bodyLeds[i].target == 1 && bodyLeds[i].b >= 255 && bodyLeds[i].g == 0) {
        bodyLeds[i].target = 0; 
      }
    }
    tiraCuerpo.show();
  }
}

void updateEye() {
  if (isTalking) {
    if (millis() - lastBlink > 100) {
      lastBlink = millis();
      eyeState = !eyeState;
    }
    uint32_t c = eyeState ? tiraOjos.Color(255, 255, 255) : tiraOjos.Color(255, 0, 0);
    for(int i=0; i<NUM_LEDS_OJO; i++) tiraOjos.setPixelColor(i, c);
  } else {
    for(int i=0; i<NUM_LEDS_OJO; i++) tiraOjos.setPixelColor(i, tiraOjos.Color(255, 0, 0));
  }
  tiraOjos.show();
}

// --- FUNCIÓN MODIFICADA: TORRETA (PARPADEO) ---
void updateTurret() {
  // Cambia de estado cada 1000ms (1 segundo)
  if (millis() - lastTurretBlink > 1000) {
    lastTurretBlink = millis();
    
    // Invertir estado (ON <-> OFF)
    turretState = !turretState;
    
    uint32_t color;
    if (turretState) {
      // Encendido: Blanco
      color = tiraTorreta.Color(255, 255, 255);
    } else {
      // Apagado: Negro
      color = tiraTorreta.Color(0, 0, 0);
    }

    // Aplicar a toda la tira
    for(int i=0; i<NUM_LEDS_TORRETA; i++) {
      tiraTorreta.setPixelColor(i, color);
    }
    tiraTorreta.show();
  }
}

void updateNeck() {
  if (millis() - lastNeckFade > 40) {
    lastNeckFade = millis();
    neckGreenVal += neckDir;
    if (neckGreenVal >= 255) { neckGreenVal = 255; neckDir = -2; }
    else if (neckGreenVal <= 80) { neckGreenVal = 80; neckDir = 2; } 

    uint32_t color = tiraCuello.Color(255, neckGreenVal, 0);
    for(int i=0; i<NUM_LEDS_CUELLO; i++) tiraCuello.setPixelColor(i, color);
    tiraCuello.show();
  }
}


void loop() {
  // 1. LEER COMANDOS DESDE BLUETOOTH
  if (SerialBT.available()) {
    String input = SerialBT.readStringUntil('\n');
    // Serial.println(input); // Debug opcional en USB
    DeserializationError error = deserializeJson(doc, input);
    if (!error) processCommand();
  }

  // 2. Tareas en segundo plano
  motor1.run();
  motor2.run();

  updateBody();
  updateEye();
  updateTurret();
  updateNeck();
}