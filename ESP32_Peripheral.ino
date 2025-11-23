/*
  ESP32 BLE measurement peripheral
  - Advertises with device name "LSMD-DIU Central" when PB is pressed
  - PB pin 25 (pulls to 3.3V when pressed)
  - Potentiometer on ADC pin 34
  - Command characteristic (write) to receive commands from laptop
    Commands:
      "MEAS:<seconds>"  -> start measurement for given seconds (integer or float accepted)
      "STOP"            -> stop measurement early
  - Data characteristic (notify): sends measurement strings "0.00 V" ... "3.30 V"
  - Status characteristic (notify): sends status strings such as "PAIR_SUCCESS", "STANDBY", "MEAS_COMPLETE", "SLEEP"
  - If idle (no measurement & no activity) for 5 minutes -> deep sleep
  - Wakes from deep sleep on a single press of PB (GPIO25)
*/

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include "esp_sleep.h"

// ---------- Pin definitions ----------
const int BUTTON_PIN = 25;   // PBNO as described (to 3.3V when pressed)
const int ADC_PIN = 34;      // potentiometer on ADC

// ---------- BLE UUIDs ----------
#define SERVICE_UUID        "e1c1b100-0001-4fda-9f7b-1234567890ab"
#define DATA_CHAR_UUID      "e1c1b100-0002-4fda-9f7b-1234567890ab" // notify: voltage strings
#define CMD_CHAR_UUID       "e1c1b100-0003-4fda-9f7b-1234567890ab" // write: commands
#define STATUS_CHAR_UUID    "e1c1b100-0004-4fda-9f7b-1234567890ab" // notify: status

// ---------- Globals ----------
BLEServer* pServer = nullptr;
BLECharacteristic* pDataChar = nullptr;
BLECharacteristic* pCmdChar = nullptr;
BLECharacteristic* pStatusChar = nullptr;

volatile bool advertisingStarted = false;
volatile bool buttonPressedFlag = false;

volatile bool deviceConnected = false;
volatile bool oldDeviceConnected = false;
unsigned long lastActivityMillis = 0; // last time we saw activity (connect, command, measurement)
const unsigned long IDLE_TIMEOUT_MS = 5UL * 60UL * 1000UL; // 5 minutes

// Measurement control
volatile bool measuring = false;
float measurementDurationSec = 0.0;
volatile bool stopMeasurement = false;

// measurement task handle
TaskHandle_t measTaskHandle = NULL;

// ---------- Helpers ----------
String formatVoltageString(float v) {
  char buf[16];
  snprintf(buf, sizeof(buf), "%.2f V", v);
  return String(buf);
}

float readVoltage() {
  // simple conversion: ADC 12-bit (0-4095) -> 0 - 3.3V
  uint16_t raw = analogRead(ADC_PIN);
  int D = raw - 2800;
  float v = (D * (300/0.02)*(3.3/(125.2*4096)));
  return v;
}

void sendStatus(const char* s) {
  if (pStatusChar) {
    pStatusChar->setValue((uint8_t*)s, strlen(s));
    pStatusChar->notify();
  }
}

// ---------- BLE Callbacks ----------
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    lastActivityMillis = millis();
    sendStatus("PAIR_SUCCESS"); // handshake success
    delay(10); // give BLE stack a moment
    sendStatus("STANDBY");     // enter standby as requested
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    lastActivityMillis = millis();
    // we will keep advertising so peripheral (laptop) can reconnect
    pServer->getAdvertising()->start();
  }
};

class CmdCharCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pCharacteristic) {
    String val = String(pCharacteristic->getValue().c_str());
    lastActivityMillis = millis();

    if (val.length() == 0) return;

    String s = val;
    s.trim();


    // parse commands
    if (s.startsWith("MEAS:") || s.startsWith("meas:") || s.startsWith("Meas:")) {
      String t = s.substring(s.indexOf(':') + 1);
      float secs = t.toFloat();
      if (secs <= 0) secs = 1.0;
      measurementDurationSec = secs;
      stopMeasurement = false;
      // Create measurement task if not running
      if (!measuring) {
        // start measurement task
        measuring = true;
        xTaskCreatePinnedToCore(
          [](void* param)->void {
            // measurement loop
            unsigned long startMs = millis();
            unsigned long durationMs = (unsigned long)(measurementDurationSec * 1000.0f);
            sendStatus("MEAS_START");
            while (!stopMeasurement && (millis() - startMs) < durationMs) {
              float v = readVoltage();
              String vs = formatVoltageString(v);
              if (pDataChar) {
                pDataChar->setValue((uint8_t*)vs.c_str(), vs.length());
                pDataChar->notify();
              }
              vTaskDelay(pdMS_TO_TICKS(200)); // ~5 samples per second; adjust as needed
            }
            // send completion
            sendStatus("MEAS_COMPLETE");
            measuring = false;
            lastActivityMillis = millis();
            vTaskDelete(NULL);
          },
          "measTask", 4096, NULL, 1, &measTaskHandle, 1
        );
      }
    }
    else if (s.equalsIgnoreCase("STOP")) {
      stopMeasurement = true;
      // measurement task will finish and notify completion
    }
    else {
      // unknown command - echo as status
      sendStatus(s.c_str());
    }
  }
};

// ---------- Setup ----------
void setup() {
  // Serial for debug terminal
  Serial.begin(115200);
  delay(100);

  // ADC init
  analogReadResolution(12); // 0..4095
  pinMode(ADC_PIN, INPUT);

  // Button setup - PB pulls to 3.3V when pressed; use INPUT_PULLDOWN if available; else external pull-down recommended.
  pinMode(BUTTON_PIN, INPUT); // assume board has a pulldown; if not, wire accordingly
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), [](){
    // minimal ISR: mark that button was pressed
    buttonPressedFlag = true;
  }, RISING);

  // If we woke from deep sleep, the ESP restarts here.
  // On power-on we do not advertise until PB press, per requirements.
  Serial.println("ESP32 boot - waiting for PB press to start pairing...");
  lastActivityMillis = millis();

  // BLE setup
  BLEDevice::init("LSMD-DIU Central"); // advertised device name (your requested name)
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Data char (notify)
  pDataChar = pService->createCharacteristic(
                 DATA_CHAR_UUID,
                 BLECharacteristic::PROPERTY_NOTIFY
               );
  pDataChar->addDescriptor(new BLE2902());

  // Status char (notify)
  pStatusChar = pService->createCharacteristic(
                  STATUS_CHAR_UUID,
                  BLECharacteristic::PROPERTY_NOTIFY
                );
  pStatusChar->addDescriptor(new BLE2902());

  // Command char (write)
  pCmdChar = pService->createCharacteristic(
               CMD_CHAR_UUID,
               BLECharacteristic::PROPERTY_WRITE
             );
  pCmdChar->setCallbacks(new CmdCharCallbacks());

  pService->start();

  // prepare advertising but do not start until PB pressed
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // functions that help with iPhone connections
  pAdvertising->setMaxPreferred(0x12);

  advertisingStarted = false;
}

// ---------- Loop ----------
void loop() {
  // If button pressed and not advertising yet -> start advertising
  if (buttonPressedFlag && !advertisingStarted) {
    // debounce
    delay(20);
    if (digitalRead(BUTTON_PIN) == HIGH) {
      buttonPressedFlag = false;
      advertisingStarted = true;
      BLEDevice::getAdvertising()->start();
      Serial.println("Button pressed -> advertising started");
      sendStatus("ADVERTISING");
      lastActivityMillis = millis();
    } else {
      buttonPressedFlag = false;
    }
  }

  // If deep sleep wake request: handled by pressing PB - ESP will reboot and start above

  // Idle sleep check (not measuring)
  if (!measuring && !deviceConnected && advertisingStarted) {
    // If advertising but never connected and idle timeout passed -> sleep
    if (millis() - lastActivityMillis > IDLE_TIMEOUT_MS) {
      Serial.println("Idle timeout reached while advertising -> entering deep sleep");
      sendStatus("SLEEP");
      delay(50); // let notif go if possible (best-effort)
      // Prepare deep sleep wakeup on PB (GPIO25) rising
      esp_sleep_enable_ext0_wakeup(GPIO_NUM_25, 1); // wake on HIGH
      // stop advertising to save power (optional)
      BLEDevice::getAdvertising()->stop();
      // go to deep sleep
      esp_deep_sleep_start();
    }
  }

  // Idle while connected but no commands: we'll also put to sleep if connected but idle and not measuring
  if (!measuring && deviceConnected) {
    if (millis() - lastActivityMillis > IDLE_TIMEOUT_MS) {
      // Send SLEEP then disconnect and sleep
      Serial.println("Idle timeout reached while connected -> sending SLEEP and going to deep sleep");
      sendStatus("SLEEP");
      delay(50);
      // disconnect
      pServer->disconnect(0);
      advertisingStarted = false;
      // enable wake on PB
      esp_sleep_enable_ext0_wakeup(GPIO_NUM_25, 1);
      esp_deep_sleep_start();
    }
  }

  // Keep track for BLE-connected state changes for optional serial printing
  if (deviceConnected && !oldDeviceConnected) {
    Serial.println("Device connected");
    oldDeviceConnected = deviceConnected;
  }
  if (!deviceConnected && oldDeviceConnected) {
    Serial.println("Device disconnected");
    oldDeviceConnected = deviceConnected;
  }

  // small loop delay
  delay(100);
}
