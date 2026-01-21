// ESP32 Dual-Mode Communication: BLE + USB Serial
// Only sends data after receiving "START" command
// Detects which connection type is active and uses only that one

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <string.h>

// ===================================
// 1. UUID Definitions
// ===================================

#define SERVICE_UUID           "4FA4A4AA-0001-4000-8000-000000000000"
#define NOTIFY_CHARACTERISTIC_UUID "4FA4A4AA-0002-4000-8000-000000000000"
#define RECEIVE_CHARACTERISTIC_UUID "4FA4A4AA-0003-4000-8000-000000000000"

#define DEVICE_NAME "ESP32_WROOM_DA_Comm"

// ===================================
// 2. Global Variables
// ===================================

BLECharacteristic *pNotifyCharacteristic = nullptr;
BLECharacteristic *pReceiveCharacteristic = nullptr;
BLEServer *pServer = nullptr;

// Connection states
bool bleConnected = false;

// Which connection is being used (only one at a time)
enum ConnectionType {
  CONN_NONE,
  CONN_USB,
  CONN_BLE
};
ConnectionType activeConnection = CONN_NONE;

// Data streaming state
bool streamingEnabled = false;

long lastSendTime = 0;
const int SEND_INTERVAL_MS = 2000;

// ===================================
// 3. Forward Declarations
// ===================================

void handleCommand(const char* command, ConnectionType source);
void sendData(const char* message);
void initBLE();
void simulateDisconnect();

// ===================================
// 4. Callback Classes
// ===================================

class ServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      bleConnected = true;
      Serial.println("\n--- BLE Client Connected! ---");
      Serial.println("Waiting for START command...");
    };

    void onDisconnect(BLEServer* pServer) {
      bleConnected = false;
      
      // If BLE was the active connection, reset everything
      if (activeConnection == CONN_BLE) {
        activeConnection = CONN_NONE;
        streamingEnabled = false;
        Serial.println("--- BLE Disconnected. Streaming stopped. ---");
      }
      
      Serial.println("--- Restarting BLE advertising... ---");
      // This makes the device "searchable" again immediately
      BLEDevice::startAdvertising();
    }
};

class CharacteristicCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      const uint8_t* data = pCharacteristic->getData();
      size_t length = pCharacteristic->getLength();

      if (length > 0) {
        char tempBuf[length + 1];
        memcpy(tempBuf, data, length);
        tempBuf[length] = '\0';
        
        handleCommand(tempBuf, CONN_BLE);
      }
    }
};

// ===================================
// 5. Command Handler
// ===================================

void handleCommand(const char* command, ConnectionType source) {
  // Always print received command to Serial Monitor
  Serial.print("[");
  Serial.print(source == CONN_USB ? "USB" : "BLE");
  Serial.print("] Received: ");
  Serial.println(command);
  
  // START command - begin streaming
  if (strcasecmp(command, "START") == 0) {
    if (activeConnection == CONN_NONE) {
      activeConnection = source;
      streamingEnabled = true;
      lastSendTime = millis();
      
      Serial.print(">>> Streaming STARTED via ");
      Serial.println(source == CONN_USB ? "USB" : "BLE");
      
      sendData("OK:STARTED");
    } 
    else if (activeConnection == source) {
      sendData("OK:ALREADY_STARTED");
    }
    else {
      Serial.println(">>> Rejected: Another connection is active");
    }
  }
  // STOP command - stop streaming
  else if (strcasecmp(command, "STOP") == 0) {
    if (activeConnection == source) {
      streamingEnabled = false;
      activeConnection = CONN_NONE;
      
      Serial.println(">>> Streaming STOPPED");
      sendData("OK:STOPPED");
    }
  }
  // STATUS command - report current state
  else if (strcasecmp(command, "STATUS") == 0) {
    char statusMsg[64];
    snprintf(statusMsg, sizeof(statusMsg), "STATUS:%s:%s",
             activeConnection == CONN_NONE ? "IDLE" : (activeConnection == CONN_USB ? "USB" : "BLE"),
             streamingEnabled ? "STREAMING" : "STOPPED");
    
    if (source == CONN_USB) {
      Serial.println(statusMsg);
    } else if (source == CONN_BLE && bleConnected) {
      pNotifyCharacteristic->setValue((uint8_t*)statusMsg, strlen(statusMsg));
      pNotifyCharacteristic->notify();
    }
  }
  // DISCONNECT command - simulate disconnect for testing
  else if (strcasecmp(command, "DISCONNECT") == 0 || strcasecmp(command, "D") == 0) {
    Serial.println(">>> DISCONNECT command received.");
    simulateDisconnect();
  }
  // Any other command - just echo it
  else {
    Serial.print(">>> Unknown command, echoing: ");
    Serial.println(command);
  }
}

// ===================================
// 6. Data Sender
// ===================================

void sendData(const char* message) {
  if (activeConnection == CONN_NONE) {
    return;
  }
  
  if (activeConnection == CONN_USB) {
    Serial.println(message);
    Serial.flush();
  } 
  else if (activeConnection == CONN_BLE && bleConnected && pNotifyCharacteristic) {
    pNotifyCharacteristic->setValue((uint8_t*)message, strlen(message));
    pNotifyCharacteristic->notify();
    delay(20);
  }
}

// ===================================
// 7. BLE Initialization
// ===================================

void initBLE() {
  BLEDevice::init(DEVICE_NAME);
  
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pNotifyCharacteristic = pService->createCharacteristic(
                                     NOTIFY_CHARACTERISTIC_UUID,
                                     BLECharacteristic::PROPERTY_NOTIFY
                                   );
  pNotifyCharacteristic->addDescriptor(new BLE2902());

  pReceiveCharacteristic = pService->createCharacteristic(
                                     RECEIVE_CHARACTERISTIC_UUID,
                                     BLECharacteristic::PROPERTY_WRITE
                                   );
  pReceiveCharacteristic->setCallbacks(new CharacteristicCallbacks());

  pService->start();

  BLEAdvertising *pAdvertising = pServer->getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMaxPreferred(0x12);
  BLEDevice::startAdvertising();
  
  Serial.println("BLE initialized and advertising.");
}

// ===================================
// 8. Simulated Disconnect
// ===================================

void simulateDisconnect() {
  Serial.println(">>> Sending disconnect acknowledgment...");
  
  if (bleConnected && pNotifyCharacteristic) {
    const char* msg = "OK:DISCONNECTING";
    pNotifyCharacteristic->setValue((uint8_t*)msg, strlen(msg));
    pNotifyCharacteristic->notify();
    delay(200); // Give time for the notification to be sent
  }
  
  Serial.println("--- Forcing BLE Disconnect... ---");
  
  // We simply drop the connection. The 'onDisconnect' callback 
  // (Lines 57-72) will automatically reset the state and restart 
  // advertising for us without crashing the board.
  if (pServer != nullptr) {
    pServer->disconnect(pServer->getConnId());
  }
  
  Serial.println("--- Disconnect request sent. Ready for search. ---");
}

// ===================================
// 9. Setup Function
// ===================================

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(500);
  
  Serial.println();
  Serial.println("========================================");
  Serial.println("ESP32 Dual-Mode Communication Server");
  Serial.println("USB Serial: 115200 baud");
  Serial.println("BLE: Enabled");
  Serial.println("========================================");
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  START      - Begin data streaming");
  Serial.println("  STOP       - Stop data streaming");
  Serial.println("  STATUS     - Get current connection status");
  Serial.println("  DISCONNECT - Simulate BLE disconnect");
  Serial.println();
  Serial.println("========================================");
  
  initBLE();
  
  Serial.println("Waiting for connection...");
}

// ===================================
// 10. Loop Function
// ===================================

void loop() {
  // Check for incoming USB serial data
  if (Serial.available()) {
      Serial.setTimeout(50);  // Short timeout to collect complete message
      String received = Serial.readString();
      received.trim();

      if (received.length() > 0) {
        handleCommand(received.c_str(), CONN_USB);
      }
  }

  // Detect intentional GUI disconnect by checking Serial status
  if (activeConnection == CONN_USB && !Serial) {
    streamingEnabled = false;
    activeConnection = CONN_NONE;
  }
  
  // Send data at interval only if streaming is enabled
  if (streamingEnabled && (millis() - lastSendTime >= SEND_INTERVAL_MS)) {
    const char* message = "Lorem ipsum dolor sit amet, consectetur adipiscing elit.";
    
    sendData(message);
    
    lastSendTime = millis();
  }

  delay(10);
}