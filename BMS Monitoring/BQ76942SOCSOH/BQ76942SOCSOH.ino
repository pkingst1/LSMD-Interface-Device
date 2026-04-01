#include <Wire.h>

// =============================================================================
// BQ76942 Battery Monitor - Recovery & Configuration Sketch v3
//
// v3 changes vs v2:
//   A.  FET_TEST MODE FIX: OTP defaults load FET_TEST=2 (MFG_STATUS bit6:5 = 0x40).
//       This overrides normal FET control. MFG_STATUS_INIT now explicitly set to
//       0x0006 with FET_TEST bits (6:5) forced to 0. Belt-and-suspenders: after
//       exiting CONFIG_UPDATE, we write the runtime MFG status directly via
//       subcommand 0x0057 to ensure FET_EN + SLEEP_DIS take effect.
//   B.  Runtime MFG status verification loop: after setting MFG status, we poll
//       until FET_EN (bit1) is confirmed set in the runtime readback, or timeout.
//   C.  Added MFGR_ACCESS write (0x0057) to directly manipulate runtime MFG status
//       post-config. The init register (0x9343) only sets the boot default - the
//       runtime copy is what actually controls FET behavior.
//   D.  Full 16-bit CP_STATUS decode for better diagnostics.
//   E.  Sleep still cycling - added DEEPSLEEP check and more aggressive wake sequence.
// =============================================================================

#define BQ_ADDR 0x08

// --- Direct Command Registers ---
#define BATTERY_STATUS   0x12
#define SAFETY_STATUS_A  0x03
#define SAFETY_STATUS_B  0x05
#define PF_STATUS_A      0x0B
#define PF_STATUS_B      0x0D
#define PF_STATUS_C      0x0F
#define PF_STATUS_D      0x11
#define FET_STATUS       0x7F
#define CELL1_VOLTAGE    0x14
#define CELL2_VOLTAGE    0x16
#define CELL3_VOLTAGE    0x18
#define CELL4_VOLTAGE    0x26
#define PACK_VOLTAGE     0x36
#define CC2_CURRENT      0x3A   // Signed 16-bit, units = mA (with proper calibration)
#define INT_TEMP         0x68   // Internal die temperature (0.1K units)
#define ACCUM_CHARGE_LO  0x70   // Accumulated charge low word
#define ACCUM_CHARGE_HI  0x72   // Accumulated charge high word
#define ACCUM_TIME_LO    0x74   // Accumulated time low word
#define ACCUM_TIME_HI    0x76   // Accumulated time high word

// --- Subcommands ---
#define SUB_RESET         0x0012
#define SET_CFGUPDATE     0x0090
#define EXIT_CFGUPDATE    0x0092
#define FET_ENABLE        0x0022
#define ALL_FETS_ON       0x0096
#define ALL_FETS_OFF      0x0097
#define SUB_SLEEP_DISABLE 0x0099
#define SUB_MFG_STATUS    0x0057   // Read/write runtime Manufacturing Status
#define SUB_CP_STATUS     0x0075
#define CLR_SAFETY_A      0x2714
#define CLR_SAFETY_B      0x2715
#define CLR_SAFETY_C      0x2716

// --- Data Memory Addresses ---
#define ADDR_COMM_TYPE    0x9239   // 1 byte
#define ADDR_VCELL_MODE   0x9304   // 2 bytes
#define ADDR_TEMP_CONF    0x9262   // 1 byte
#define ADDR_MFG_STATUS   0x9343   // 2 bytes - Mfg Status Init (boot default)
#define ADDR_FET_OPTIONS  0x9308   // 1 byte
#define ADDR_COV_THRESH   0x9278   // 1 byte
#define ADDR_CUV_THRESH   0x9275   // 1 byte
#define ADDR_SLEEP_CONF   0x9231   // 1 byte
#define ADDR_POWER_CONF   0x9234   // 2 bytes
#define ADDR_PF_ENABLE_B  0x9261   // 1 byte
#define ADDR_REG_CTRL     0x9236   // 1 byte
#define ADDR_UTC_THRESH   0x927F   // 1 byte
#define ADDR_UTD_THRESH   0x9282   // 1 byte
#define ADDR_UT_HYST      0x9285   // 1 byte
#define ADDR_UT_DISABLE   0x9286   // 1 byte

// =============================================================================
// BATTERY PARAMETERS - Adjust these for your cells
// =============================================================================
#define CELL_FULL_MV      4200   // 100% SOC (fully charged OCV)
#define CELL_EMPTY_MV     3000   // 0% SOC (cutoff voltage)
#define CELL_NOMINAL_MV   3700   // Nominal voltage
#define NUM_CELLS          4
#define DESIGN_CAPACITY_MAH 1500 // Design capacity of your cells in mAh

// Sense resistor: 1 mOhm (R17 on your schematic between SRN/SRP)
// BQ76942 CC2 register: raw value in units that depend on the sense resistor.
// With 1 mOhm: 1 LSB of CC2 = approximately 8.44mA (per TRM section 9.3.8)
// Current (mA) = CC2_raw * 8.44  (for 1 mOhm)
// Adjust this if your sense resistor is different.
#define SENSE_RESISTOR_MOHM  1
#define CC2_LSB_UA           8440  // Microamps per LSB for 1 mOhm sense resistor

// SOH tracking
#define HEALTHY_SPREAD_MV   30
#define BAD_SPREAD_MV      200

// Coulomb counter state (stored in SRAM, resets on power cycle)
// For persistent tracking across power cycles, you would save to EEPROM
int32_t  g_remainingCapacityUah;   // Remaining capacity in microamp-hours
int32_t  g_fullCapacityUah;        // Full capacity estimate in microamp-hours
uint32_t g_lastLoopTimeMs;         // Timestamp of last loop iteration
bool     g_coulombInitialized = false;

// =============================================================================
// FUNCTION DECLARATIONS
// =============================================================================
uint16_t readDirectCommand(uint8_t reg);
bool     isBusValid(uint16_t val);
void     sendSubcommand(uint16_t sub);
uint16_t readSubcommandResult();
void     writeSubcommandData(uint16_t sub, uint16_t data);
bool     enterConfigUpdate();
void     exitConfigUpdate();
void     writeDataMemory(uint16_t address, uint32_t data, uint8_t length);
uint16_t readDataMemory(uint16_t address, uint8_t length);
void     verifyWrite(uint16_t address, uint16_t expected, uint8_t length, const __FlashStringHelper* label);
void     sendUnsealKeys();
void     readPFDetails();
void     clearSafetyFaults();
uint16_t readMfgStatus();
void     printMfgStatus(uint16_t status);
void     readCPStatus();
bool     setRuntimeMfgStatus(uint16_t desired);
void     enableFETs();
uint8_t  calculateSOC_OCV(uint16_t cellMv);
uint8_t  calculateSOH(uint16_t vc1, uint16_t vc2, uint16_t vc3, uint16_t vc4);
int16_t  readCurrent();
void     initCoulombCounter(uint16_t minCellMv);
uint8_t  updateCoulombSOC(int16_t currentMa, uint16_t dtMs, uint16_t minCellMv);

// =============================================================================
// SETUP
// =============================================================================
void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(9600);
  delay(500);

  Serial.println(F("========================================"));
  Serial.println(F("  BQ76942 Recovery v3"));
  Serial.println(F("========================================"));

  // --- Step 1: Wait for chip to be ready on I2C ---
  Serial.println(F("[1] Connecting to BQ76942..."));
  delay(1000);  // Let chip finish its own power-on init

  uint16_t bStat = 0xFFFF;
  for (uint8_t attempt = 0; attempt < 15; attempt++) {
    sendUnsealKeys();
    delay(50);
    bStat = readDirectCommand(BATTERY_STATUS);
    if (isBusValid(bStat)) {
      Serial.print(F("    Connected on attempt ")); Serial.println(attempt + 1);
      break;
    }
    Serial.print(F("    Attempt ")); Serial.print(attempt + 1);
    Serial.println(F(" - no response..."));
    delay(500);
  }
  if (!isBusValid(bStat)) {
    Serial.println(F("[ERROR] I2C invalid after 15 attempts."));
    Serial.println(F("    Check: SDA/SCL wiring, pullups, chip soldering."));
    while (1);
  }

  // --- Step 2: Check for PF, RESET only if needed ---
  Serial.println(F("[2] Checking PF status..."));
  if (bStat & 0x1000) {
    Serial.println(F("    PF active - issuing RESET to clear..."));
    sendSubcommand(SUB_RESET);
    delay(2000);  // Long delay for full reboot

    // Re-establish communication after reset
    for (uint8_t attempt = 0; attempt < 10; attempt++) {
      sendUnsealKeys();
      delay(50);
      bStat = readDirectCommand(BATTERY_STATUS);
      if (isBusValid(bStat)) break;
      delay(500);
    }
    if (!isBusValid(bStat)) {
      Serial.println(F("[ERROR] Lost comms after RESET. Halting."));
      while (1);
    }
    if (bStat & 0x1000) {
      Serial.println(F("[ERROR] PF still active after RESET!"));
      readPFDetails();
      while (1);
    }
  }
  Serial.println(F("    PF clear."));

  // --- Step 3: Unseal ---
  Serial.println(F("[3] Unsealing..."));
  sendUnsealKeys();
  delay(10);

  // --- Step 4: Pre-config diagnostics ---
  Serial.println(F("[4] Pre-config state:"));
  uint16_t mfgPre = readMfgStatus();
  printMfgStatus(mfgPre);
  readCPStatus();

  // --- Step 5: Try to fix MFG status BEFORE config ---
  // If FET_TEST is set in OTP, we need to clear it in runtime first
  if (mfgPre & 0x0060) {
    Serial.println(F("[5] FET_TEST detected in OTP defaults!"));
    Serial.println(F("    Clearing via runtime write..."));
    // Write desired runtime status: FET_EN + SLEEP_DIS, FET_TEST=0
    setRuntimeMfgStatus(0x0006);
    uint16_t mfgCheck = readMfgStatus();
    printMfgStatus(mfgCheck);
  } else {
    Serial.println(F("[5] No FET_TEST in defaults."));
  }

  // --- Step 6: Enter CONFIG_UPDATE ---
  Serial.println(F("[6] Entering CONFIG_UPDATE..."));
  if (!enterConfigUpdate()) {
    Serial.println(F("[ERROR] CONFIG_UPDATE timeout. Halting."));
    while (1);
  }
  Serial.println(F("    Active."));

  // --- Step 7: Write config ---
  Serial.println(F("[7] Writing config..."));

  writeDataMemory(ADDR_COMM_TYPE,   0x08,   1);
  writeDataMemory(ADDR_VCELL_MODE,  0x0207, 2);
  writeDataMemory(ADDR_TEMP_CONF,   0x00,   1);

  // MFG_STATUS_INIT: 0x0006 = FET_EN(bit1) + SLEEP_DIS(bit2)
  // FET_TEST bits (6:5) explicitly 0 - overrides the 0x40 OTP default
  writeDataMemory(ADDR_MFG_STATUS,  0x0006, 2);

  writeDataMemory(ADDR_FET_OPTIONS, 0x00,   1);
  writeDataMemory(ADDR_COV_THRESH,  0x54,   1);
  writeDataMemory(ADDR_CUV_THRESH,  0x3B,   1);
  writeDataMemory(ADDR_SLEEP_CONF,  0x00,   1);
  writeDataMemory(ADDR_POWER_CONF,  0x2968, 2);
  writeDataMemory(ADDR_PF_ENABLE_B, 0x00,   1);
  writeDataMemory(ADDR_REG_CTRL,    0x03,   1);
  writeDataMemory(ADDR_UTC_THRESH,  0x01,   1);
  writeDataMemory(ADDR_UTD_THRESH,  0x01,   1);
  writeDataMemory(ADDR_UT_HYST,     0x01,   1);
  writeDataMemory(ADDR_UT_DISABLE,  0x03,   1);

  // --- Step 7b: Verify ---
  Serial.println(F("[7b] Verifying writes..."));
  verifyWrite(ADDR_SLEEP_CONF,  0x0000, 1, F("SLEEP_CONF "));
  verifyWrite(ADDR_POWER_CONF,  0x2968, 2, F("POWER_CONF "));
  verifyWrite(ADDR_VCELL_MODE,  0x0207, 2, F("VCELL_MODE "));
  verifyWrite(ADDR_MFG_STATUS,  0x0006, 2, F("MFG_INIT   "));
  verifyWrite(ADDR_FET_OPTIONS, 0x0000, 1, F("FET_OPTIONS"));
  verifyWrite(ADDR_REG_CTRL,    0x0003, 1, F("REG_CTRL   "));
  verifyWrite(ADDR_PF_ENABLE_B, 0x0000, 1, F("PF_ENAB_B  "));
  verifyWrite(ADDR_TEMP_CONF,   0x0000, 1, F("TEMP_CONF  "));
  verifyWrite(ADDR_UTC_THRESH,  0x0001, 1, F("UTC_THRESH "));
  verifyWrite(ADDR_UTD_THRESH,  0x0001, 1, F("UTD_THRESH "));
  verifyWrite(ADDR_UT_DISABLE,  0x0003, 1, F("UT_DISABLE "));

  // --- Step 8: Exit CONFIG_UPDATE ---
  Serial.println(F("[8] Exiting CONFIG_UPDATE..."));
  exitConfigUpdate();

  unsigned long t = millis();
  while (readDirectCommand(BATTERY_STATUS) & 0x0001) {
    if (millis() - t > 2000) {
      Serial.println(F("[WARN] CFGUPDATE slow to clear."));
      break;
    }
    delay(20);
  }
  delay(200);

  // --- Step 9: RESET so chip reloads MFG_STATUS_INIT into runtime ---
  // The init register (0x9343) only takes effect after a reset/power cycle.
  // Without this, the runtime MFG status stays at OTP defaults (0x0000).
  Serial.println(F("[9] RESET to load new config..."));
  sendSubcommand(SUB_RESET);
  delay(2000);

  // Re-establish communication
  Serial.println(F("[10] Reconnecting..."));
  bStat = 0xFFFF;
  for (uint8_t attempt = 0; attempt < 10; attempt++) {
    sendUnsealKeys();
    delay(50);
    bStat = readDirectCommand(BATTERY_STATUS);
    if (isBusValid(bStat)) {
      Serial.print(F("    Connected on attempt ")); Serial.println(attempt + 1);
      break;
    }
    delay(500);
  }
  if (!isBusValid(bStat)) {
    Serial.println(F("[ERROR] Lost comms after RESET. Halting."));
    while (1);
  }

  // --- Step 11: Verify MFG status loaded correctly ---
  Serial.println(F("[11] Post-reset MFG status:"));
  uint16_t mfgPost = readMfgStatus();
  printMfgStatus(mfgPost);

  if (!(mfgPost & 0x0002)) {
    Serial.println(F("    FET_EN still not set after reset."));
    Serial.println(F("    Trying direct runtime write..."));
    setRuntimeMfgStatus(0x0006);
    mfgPost = readMfgStatus();
    printMfgStatus(mfgPost);
  }

  // --- Step 12: Sleep disable ---
  Serial.println(F("[12] SLEEP_DISABLE..."));
  sendSubcommand(SUB_SLEEP_DISABLE);
  delay(50);

  // --- Step 13: Clear faults ---
  Serial.println(F("[13] Clearing safety faults..."));
  clearSafetyFaults();
  delay(50);

  // --- Step 14: Enable FETs ---
  Serial.println(F("[14] Enabling FETs..."));
  enableFETs();

  // --- Step 15: Final diagnostics ---
  Serial.println(F("[15] Final diagnostics:"));
  readCPStatus();
  uint16_t mfgRuntime = readMfgStatus();
  Serial.print(F("    Runtime MFG: "));
  printMfgStatus(mfgRuntime);

  uint8_t fStat = readDirectCommand(FET_STATUS) & 0xFF;
  uint8_t safA  = readDirectCommand(SAFETY_STATUS_A) & 0xFF;
  uint8_t safB  = readDirectCommand(SAFETY_STATUS_B) & 0xFF;
  bStat = readDirectCommand(BATTERY_STATUS);

  Serial.println(F("--- POST-INIT ---"));
  Serial.print(F("BattStat: 0x")); Serial.print(bStat, HEX);
  if (bStat & 0x8000) Serial.print(F(" [SLEEP]"));
  if (bStat & 0x0800) Serial.print(F(" [SAFE_MODE]"));
  if (bStat & 0x0080) Serial.print(F(" [INITCOMP]"));
  Serial.println();

  Serial.print(F("FET: 0x")); Serial.print(fStat, HEX);
  Serial.print(F("  SafA: 0x")); Serial.print(safA, HEX);
  Serial.print(F("  SafB: 0x")); Serial.println(safB, HEX);

  // Detailed FET decode
  Serial.print(F("  DSG_FET=")); Serial.print((fStat & 0x04) ? F("ON") : F("OFF"));
  Serial.print(F("  CHG_FET=")); Serial.print((fStat & 0x01) ? F("ON") : F("OFF"));
  Serial.print(F("  PDSG=")); Serial.print((fStat & 0x08) ? F("ON") : F("OFF"));
  Serial.print(F("  ALRT=")); Serial.print((fStat & 0x02) ? F("ON") : F("OFF"));
  Serial.println();
  Serial.print(F("  DCHG_DRV=")); Serial.print((fStat & 0x40) ? F("HI") : F("LO"));
  Serial.print(F("  CHG_DRV=")); Serial.print((fStat & 0x10) ? F("HI") : F("LO"));
  Serial.print(F("  PDSG_DRV=")); Serial.print((fStat & 0x80) ? F("HI") : F("LO"));
  Serial.println();

  if (fStat & 0x04) {
    Serial.println(F("    DSG FET is ON!"));
  } else {
    Serial.println(F("    DSG still OFF."));
    if (!(mfgRuntime & 0x0002)) {
      Serial.println(F("    ROOT CAUSE: FET_EN not set in runtime."));
      Serial.println(F("    The chip ignores FET commands without FET_EN."));
    }
    if (mfgRuntime & 0x0060) {
      Serial.println(F("    ROOT CAUSE: FET_TEST active in OTP."));
      Serial.println(F("    This chip may be a test/eval unit with"));
      Serial.println(F("    locked FET_TEST mode. Normal FET control"));
      Serial.println(F("    is disabled in FET_TEST modes."));
    }
    Serial.println(F("    Also check HW: DCHG pin, CP cap, FET gate."));
  }

  Serial.println(F("========================================"));
  Serial.println(F("  Init complete. Monitoring."));
  Serial.println(F("========================================"));
}

// =============================================================================
// MAIN LOOP
// =============================================================================
void loop() {
  uint16_t bStat = readDirectCommand(BATTERY_STATUS);
  uint8_t  fStat = readDirectCommand(FET_STATUS) & 0xFF;
  uint8_t  safA  = readDirectCommand(SAFETY_STATUS_A) & 0xFF;
  uint8_t  safB  = readDirectCommand(SAFETY_STATUS_B) & 0xFF;

  if (!isBusValid(bStat) || !isBusValid(fStat) || !isBusValid(safA)) {
    Serial.println(F("[WARN] I2C dropout."));
    delay(2000);
    return;
  }

  uint16_t vc1 = readDirectCommand(CELL1_VOLTAGE);
  uint16_t vc2 = readDirectCommand(CELL2_VOLTAGE);
  uint16_t vc3 = readDirectCommand(CELL3_VOLTAGE);
  uint16_t vc4 = readDirectCommand(CELL4_VOLTAGE);
  uint32_t stackV = (uint32_t)vc1 + vc2 + vc3 + vc4;
  uint16_t packV = readDirectCommand(PACK_VOLTAGE);

  // Print every 40 loops (40 x 500ms delay = ~20 seconds)
  static uint8_t printCount = 0;
  printCount++;
  bool doPrint = (printCount >= 40);
  if (doPrint) printCount = 0;

  if (doPrint) {
    Serial.println(F("--- STATUS ---"));

    Serial.print(F("BattStat: 0x")); Serial.print(bStat, HEX);
    if (bStat & 0x8000) Serial.print(F(" [SLEEP]"));
    if (bStat & 0x0800) Serial.print(F(" [SAFE_MODE]"));
    if (bStat & 0x0400) Serial.print(F(" [SS]"));
    if (bStat & 0x0200) Serial.print(F(" [WD]"));
    if (bStat & 0x0080) Serial.print(F(" [INITCOMP]"));
    Serial.println();

    Serial.print(F("FET:0x")); Serial.print(fStat, HEX);
    Serial.print(F(" SafA:0x")); Serial.print(safA, HEX);
    Serial.print(F(" SafB:0x")); Serial.println(safB, HEX);
  }

  if (doPrint) {
    Serial.print(F("VC1:")); Serial.print(vc1); Serial.print(F("mV "));
    Serial.print(F("VC2:")); Serial.print(vc2); Serial.print(F("mV "));
    Serial.print(F("VC3:")); Serial.print(vc3); Serial.print(F("mV "));
    Serial.print(F("VC4:")); Serial.print(vc4); Serial.println(F("mV"));

    Serial.print(F("Stack:")); Serial.print(stackV); Serial.print(F("mV"));
    uint32_t packMv = (uint32_t)packV * 10;
    Serial.print(F(" Pack:")); Serial.print(packMv); Serial.println(F("mV"));
  }

  // --- Current measurement ---
  int16_t currentMa = readCurrent();

  if (doPrint) {
    Serial.print(F("Current: ")); Serial.print(currentMa); Serial.println(F("mA"));
  }

  // --- SOC (State of Charge) ---
  uint16_t minCell = vc1;
  if (vc2 < minCell) minCell = vc2;
  if (vc3 < minCell) minCell = vc3;
  if (vc4 < minCell) minCell = vc4;

  uint16_t maxCell = vc1;
  if (vc2 > maxCell) maxCell = vc2;
  if (vc3 > maxCell) maxCell = vc3;
  if (vc4 > maxCell) maxCell = vc4;

  // Time delta for coulomb counting
  uint32_t now = millis();
  uint16_t dtMs = (uint16_t)(now - g_lastLoopTimeMs);
  g_lastLoopTimeMs = now;

  // Coulomb-counted SOC (hybrid with voltage correction)
  uint8_t soc = updateCoulombSOC(currentMa, dtMs, minCell);
  uint8_t socOcv = calculateSOC_OCV(minCell);
  uint8_t soh = calculateSOH(vc1, vc2, vc3, vc4);

  if (doPrint) {
    Serial.print(F("SOC: ")); Serial.print(soc); Serial.print(F("%"));
    Serial.print(F(" (OCV:")); Serial.print(socOcv); Serial.print(F("%)"));
    Serial.print(F("  SOH: ")); Serial.print(soh); Serial.print(F("%"));
    Serial.print(F("  Spread: ")); Serial.print(maxCell - minCell); Serial.println(F("mV"));

    // Fault flags
    if (bStat & 0x1000) { Serial.println(F("[CRIT] PF!")); readPFDetails(); }
    if (safA & 0x80)    Serial.println(F("[ALERT] SCD"));
    if (safA & 0x40)    Serial.println(F("[ALERT] OCD2"));
    if (safA & 0x20)    Serial.println(F("[ALERT] OCD1"));
    if (safA & 0x08)    Serial.println(F("[ALERT] COV"));
    if (safA & 0x04)    Serial.println(F("[ALERT] CUV"));
    if (safB & 0x10)    Serial.println(F("[ALERT] OTC"));
    if (safB & 0x08)    Serial.println(F("[ALERT] OTD"));
    if (safB & 0x02)    Serial.println(F("[ALERT] UTC"));
    if (safB & 0x01)    Serial.println(F("[ALERT] UTD"));
  }

  // --- Aggressive FET keep-alive ---
  // Always: sleep disable -> clear faults -> FET enable -> FETs on -> clear again
  // The SCD fault from output cap inrush must be cleared AFTER FETs turn on
  sendSubcommand(SUB_SLEEP_DISABLE);
  delay(10);
  clearSafetyFaults();
  delay(10);
  sendSubcommand(FET_ENABLE);
  delay(30);
  sendSubcommand(ALL_FETS_ON);
  delay(30);
  // Clear SCD that may have tripped from inrush current
  clearSafetyFaults();
  delay(10);
  // Re-send FET on in case the fault clear toggled them off
  sendSubcommand(FET_ENABLE);
  delay(10);
  sendSubcommand(ALL_FETS_ON);
  delay(30);

  // Re-read FET status after commands
  uint8_t fCheck = readDirectCommand(FET_STATUS) & 0xFF;
  if (doPrint) {
    Serial.print(F("FET cmd: 0x")); Serial.print(fCheck, HEX);
    Serial.print(F(" DSG=")); Serial.print((fCheck & 0x04) ? F("ON") : F("OFF"));
    Serial.print(F(" CHG=")); Serial.println((fCheck & 0x01) ? F("ON") : F("OFF"));
    Serial.println();
  }
  delay(500);  // Very short delay - must beat the sleep timer
}

// =============================================================================
// SET RUNTIME MFG STATUS
// Writes directly to the runtime Manufacturing Status register via subcommand.
// This is different from the data memory init register (0x9343) which only
// sets the boot default. The runtime register is what actually controls behavior.
//
// The BQ76942 allows writing to MAC data area after sending the subcommand
// address, then writing data to 0x40, then writing checksum+length to 0x60.
// =============================================================================
bool setRuntimeMfgStatus(uint16_t desired) {
  // Write the subcommand address to 0x3E
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E);
  Wire.write(SUB_MFG_STATUS & 0xFF);
  Wire.write((SUB_MFG_STATUS >> 8) & 0xFF);
  Wire.endTransmission();
  delay(2);

  // Write desired data to 0x40
  uint8_t dLo = desired & 0xFF;
  uint8_t dHi = (desired >> 8) & 0xFF;

  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x40);
  Wire.write(dLo);
  Wire.write(dHi);
  Wire.endTransmission();

  // Checksum + length to 0x60
  uint8_t sum = (SUB_MFG_STATUS & 0xFF) + ((SUB_MFG_STATUS >> 8) & 0xFF) + dLo + dHi;
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x60);
  Wire.write((uint8_t)~sum);
  Wire.write((uint8_t)6);  // 4 (overhead) + 2 (data bytes)
  Wire.endTransmission();
  delay(10);

  // Verify
  uint16_t actual = readMfgStatus();
  Serial.print(F("    MFG write: want=0x")); Serial.print(desired, HEX);
  Serial.print(F(" got=0x")); Serial.print(actual, HEX);
  bool ok = ((actual & 0x0006) == (desired & 0x0006));
  Serial.println(ok ? F(" OK") : F(" FAIL"));
  return ok;
}

// =============================================================================
// READ MFG STATUS (runtime, via subcommand 0x0057)
// =============================================================================
uint16_t readMfgStatus() {
  sendSubcommand(SUB_MFG_STATUS);
  delay(5);
  return readSubcommandResult();
}

void printMfgStatus(uint16_t s) {
  Serial.print(F("    MFG: 0x")); Serial.print(s, HEX);
  Serial.print((s & 0x0002) ? F(" [FET_EN]") : F(" [FET_DIS!]"));
  Serial.print((s & 0x0004) ? F(" [SLP_DIS]") : F(" [SLP_EN!]"));
  uint8_t ft = (s >> 5) & 0x03;
  if (ft) { Serial.print(F(" [FT=")); Serial.print(ft); Serial.print(F("]")); }
  if (s & 0x0010) Serial.print(F(" [PCHG]"));
  Serial.println();
}

// =============================================================================
// READ CP STATUS
// =============================================================================
void readCPStatus() {
  sendSubcommand(SUB_CP_STATUS);
  delay(5);
  uint16_t r = readSubcommandResult();
  Serial.print(F("    CP: 0x")); Serial.print(r, HEX);
  if (r & 0x01) Serial.print(F(" CP1"));
  if (r & 0x02) Serial.print(F(" CP2"));
  // Upper byte contains pump drive status
  uint8_t hi = (r >> 8) & 0xFF;
  Serial.print(F(" drv:0x")); Serial.print(hi, HEX);
  Serial.println();
}

// =============================================================================
// FET ENABLE
// =============================================================================
void enableFETs() {
  sendSubcommand(FET_ENABLE);
  delay(100);
  sendSubcommand(ALL_FETS_ON);
  delay(500);

  uint8_t fStat = readDirectCommand(FET_STATUS) & 0xFF;
  Serial.print(F("    FET: 0x")); Serial.println(fStat, HEX);

  if (!(fStat & 0x04)) {
    Serial.println(F("    Retry..."));
    clearSafetyFaults();
    delay(50);
    sendSubcommand(FET_ENABLE);
    delay(100);
    sendSubcommand(ALL_FETS_ON);
    delay(500);
    fStat = readDirectCommand(FET_STATUS) & 0xFF;
    Serial.print(F("    FET retry: 0x")); Serial.println(fStat, HEX);
  }
}

// =============================================================================
// CORE I2C FUNCTIONS
// =============================================================================

void clearSafetyFaults() {
  sendSubcommand(CLR_SAFETY_A); delay(5);
  sendSubcommand(CLR_SAFETY_B); delay(5);
  sendSubcommand(CLR_SAFETY_C); delay(5);
}

uint16_t readDirectCommand(uint8_t reg) {
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)BQ_ADDR, (uint8_t)2);
  uint16_t low  = Wire.read();
  uint16_t high = Wire.read();
  return (high << 8) | low;
}

bool isBusValid(uint16_t val) { return (val != 0xFFFF); }

void sendSubcommand(uint16_t sub) {
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E);
  Wire.write(sub & 0xFF);
  Wire.write((sub >> 8) & 0xFF);
  Wire.endTransmission();
}

uint16_t readSubcommandResult() {
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x40);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)BQ_ADDR, (uint8_t)2);
  uint16_t low  = Wire.read();
  uint16_t high = Wire.read();
  return (high << 8) | low;
}

bool enterConfigUpdate() {
  sendSubcommand(SET_CFGUPDATE);
  delay(20);
  unsigned long timeout = millis();
  while (!(readDirectCommand(BATTERY_STATUS) & 0x0001)) {
    if (millis() - timeout > 1000) return false;
    delay(20);
  }
  return true;
}

void exitConfigUpdate() {
  sendSubcommand(EXIT_CFGUPDATE);
}

void writeDataMemory(uint16_t address, uint32_t data, uint8_t length) {
  uint8_t bytes[4];
  uint8_t addrL = address & 0xFF;
  uint8_t addrH = (address >> 8) & 0xFF;
  for (int i = 0; i < length; i++) bytes[i] = (data >> (i * 8)) & 0xFF;

  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E); Wire.write(addrL); Wire.write(addrH);
  Wire.endTransmission();

  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x40);
  for (int i = 0; i < length; i++) Wire.write(bytes[i]);
  Wire.endTransmission();

  uint8_t sum = addrL + addrH;
  for (int i = 0; i < length; i++) sum += bytes[i];
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x60);
  Wire.write((uint8_t)~sum);
  Wire.write((uint8_t)(length + 4));
  Wire.endTransmission();
  delay(5);
}

uint16_t readDataMemory(uint16_t address, uint8_t length) {
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E);
  Wire.write(address & 0xFF);
  Wire.write((address >> 8) & 0xFF);
  Wire.endTransmission();
  delay(2);

  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x40);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)BQ_ADDR, length);

  uint16_t result = 0;
  for (int i = 0; i < length; i++) {
    result |= ((uint16_t)Wire.read() << (i * 8));
  }
  return result;
}

void verifyWrite(uint16_t address, uint16_t expected, uint8_t length, const __FlashStringHelper* label) {
  uint16_t actual = readDataMemory(address, length);
  Serial.print(F("  ")); Serial.print(label);
  Serial.print(F(": exp=0x")); Serial.print(expected, HEX);
  Serial.print(F(" got=0x")); Serial.print(actual, HEX);
  Serial.println((actual == expected) ? F("  OK") : F("  FAIL <---"));
}

void sendUnsealKeys() {
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E); Wire.write(0x14); Wire.write(0x04);
  Wire.endTransmission();
  Wire.beginTransmission(BQ_ADDR);
  Wire.write(0x3E); Wire.write(0x72); Wire.write(0x36);
  Wire.endTransmission();
  delay(10);
}

void readPFDetails() {
  uint8_t pfA = readDirectCommand(PF_STATUS_A) & 0xFF;
  uint8_t pfB = readDirectCommand(PF_STATUS_B) & 0xFF;
  uint8_t pfC = readDirectCommand(PF_STATUS_C) & 0xFF;
  uint8_t pfD = readDirectCommand(PF_STATUS_D) & 0xFF;
  Serial.print(F("  PF A:0x")); Serial.print(pfA, HEX);
  Serial.print(F(" B:0x")); Serial.print(pfB, HEX);
  Serial.print(F(" C:0x")); Serial.print(pfC, HEX);
  Serial.print(F(" D:0x")); Serial.println(pfD, HEX);
  if (pfA & 0x01) Serial.println(F("  -> COV_PF"));
  if (pfA & 0x02) Serial.println(F("  -> CUV_PF"));
  if (pfA & 0x10) Serial.println(F("  -> OTC_PF"));
  if (pfA & 0x20) Serial.println(F("  -> OTD_PF"));
  if (pfD & 0x01) Serial.println(F("  -> TOSF"));
  if (pfD & 0x04) Serial.println(F("  -> VIMR"));
}

// =============================================================================
// READ CURRENT (from CC2 register)
// The BQ76942 continuously measures current through the sense resistor.
// CC2 register (0x3A) is a signed 16-bit value.
// With 1 mOhm sense resistor: 1 LSB ≈ 8.44 mA
// Positive = charging, Negative = discharging
// =============================================================================
int16_t readCurrent() {
  uint16_t raw = readDirectCommand(CC2_CURRENT);
  if (!isBusValid(raw)) return 0;

  int16_t rawSigned = (int16_t)raw;

  // Convert to mA: raw * 8.44mA/LSB for 1 mOhm
  // Using integer math: raw * 8440 / 1000 = raw * 844 / 100
  int32_t currentMa = (int32_t)rawSigned * 844L / 100L;

  // Clamp to int16_t range
  if (currentMa > 32767) currentMa = 32767;
  if (currentMa < -32768) currentMa = -32768;

  return (int16_t)currentMa;
}

// =============================================================================
// INIT COULOMB COUNTER
// Called once at startup or when counter needs re-sync.
// Seeds the remaining capacity from OCV-based SOC estimate.
// =============================================================================
void initCoulombCounter(uint16_t minCellMv) {
  g_fullCapacityUah = (int32_t)DESIGN_CAPACITY_MAH * 1000L;  // Convert mAh to uAh
  uint8_t ocvSoc = calculateSOC_OCV(minCellMv);
  g_remainingCapacityUah = g_fullCapacityUah * ocvSoc / 100;
  g_lastLoopTimeMs = millis();
  g_coulombInitialized = true;

  Serial.print(F("    Coulomb init: OCV_SOC=")); Serial.print(ocvSoc);
  Serial.print(F("% remaining=")); Serial.print(g_remainingCapacityUah / 1000L);
  Serial.println(F("mAh"));
}

// =============================================================================
// UPDATE COULOMB SOC
// Integrates measured current over time to track charge flowing in/out.
// Uses voltage-based SOC for correction when current is near zero (rest).
//
// How it works:
//   1. Each loop: remaining_uAh += current_mA * dt_ms / 3600
//      (positive current = charging = adds capacity)
//   2. When current is near zero for several seconds, the pack is "at rest"
//      and OCV-based SOC is accurate. Gradually blend toward OCV estimate
//      to correct for coulomb counting drift.
//   3. Clamp between 0% and 100%.
//
// This is significantly more accurate than voltage-only because:
//   - Under load, voltage sags but coulomb counting still tracks correctly
//   - During charging, voltage rises before SOC does - coulomb counting
//     reflects actual charge added
//   - OCV correction at rest prevents long-term drift
// =============================================================================
uint8_t updateCoulombSOC(int16_t currentMa, uint16_t dtMs, uint16_t minCellMv) {
  // Initialize on first call
  if (!g_coulombInitialized) {
    initCoulombCounter(minCellMv);
  }

  // Integrate current: delta_uAh = current_mA * dt_ms * 1000 / 3600000
  // Simplify: delta_uAh = current_mA * dt_ms / 3600
  // Use int32_t to avoid overflow
  int32_t deltaUah = (int32_t)currentMa * (int32_t)dtMs / 3600L;
  g_remainingCapacityUah += deltaUah;

  // --- OCV correction when at rest ---
  // If current is very small (< 50mA), pack is at rest and OCV is reliable.
  // Gradually blend toward OCV-based SOC to correct coulomb counting drift.
  // Blending rate: ~1% correction per cycle when at rest.
  int16_t absCurrent = currentMa;
  if (absCurrent < 0) absCurrent = -absCurrent;

  if (absCurrent < 50) {
    uint8_t ocvSoc = calculateSOC_OCV(minCellMv);
    int32_t ocvCapacityUah = g_fullCapacityUah * ocvSoc / 100;

    // Blend: move 2% toward OCV estimate each cycle at rest
    // This corrects drift without jumping suddenly
    int32_t error = ocvCapacityUah - g_remainingCapacityUah;
    g_remainingCapacityUah += error / 50;  // 2% correction
  }

  // --- Endpoint clamping ---
  // If voltage hits full or empty, force-sync
  if (minCellMv >= CELL_FULL_MV) {
    g_remainingCapacityUah = g_fullCapacityUah;
  }
  if (minCellMv <= CELL_EMPTY_MV) {
    g_remainingCapacityUah = 0;
  }

  // Clamp to valid range
  if (g_remainingCapacityUah > g_fullCapacityUah) {
    g_remainingCapacityUah = g_fullCapacityUah;
  }
  if (g_remainingCapacityUah < 0) {
    g_remainingCapacityUah = 0;
  }

  // Calculate SOC percentage
  uint8_t soc = (uint8_t)(g_remainingCapacityUah * 100L / g_fullCapacityUah);
  if (soc > 100) soc = 100;

  return soc;
}

// =============================================================================
// SOC from OCV (Open Circuit Voltage)
// Piecewise linear approximation of the Li-ion OCV curve.
// Used as the initial seed for coulomb counting and for drift correction
// when the pack is at rest (no load).
// =============================================================================
uint8_t calculateSOC_OCV(uint16_t cellMv) {
  if (cellMv >= CELL_FULL_MV) return 100;
  if (cellMv <= CELL_EMPTY_MV) return 0;

  if (cellMv >= 4100) {
    return 90 + (uint16_t)(cellMv - 4100) * 10 / 100;
  } else if (cellMv >= 3900) {
    return 65 + (uint16_t)(cellMv - 3900) * 25 / 200;
  } else if (cellMv >= 3700) {
    return 40 + (uint16_t)(cellMv - 3700) * 25 / 200;
  } else if (cellMv >= 3500) {
    return 15 + (uint16_t)(cellMv - 3500) * 25 / 200;
  } else if (cellMv >= 3300) {
    return 5 + (uint16_t)(cellMv - 3300) * 10 / 200;
  } else {
    return (uint16_t)(cellMv - CELL_EMPTY_MV) * 5 / 300;
  }
}

// =============================================================================
// SOH CALCULATION (Cell balance + capacity tracking)
// Uses cell voltage imbalance as primary indicator.
// =============================================================================
uint8_t calculateSOH(uint16_t vc1, uint16_t vc2, uint16_t vc3, uint16_t vc4) {
  uint16_t minV = vc1;
  uint16_t maxV = vc1;

  if (vc2 < minV) minV = vc2;
  if (vc3 < minV) minV = vc3;
  if (vc4 < minV) minV = vc4;

  if (vc2 > maxV) maxV = vc2;
  if (vc3 > maxV) maxV = vc3;
  if (vc4 > maxV) maxV = vc4;

  uint16_t spread = maxV - minV;

  if (spread <= HEALTHY_SPREAD_MV) {
    return 100;
  } else if (spread >= BAD_SPREAD_MV) {
    if (spread >= 400) return 0;
    return 50 - (uint16_t)(spread - BAD_SPREAD_MV) * 50 / (400 - BAD_SPREAD_MV);
  } else {
    return 100 - (uint16_t)(spread - HEALTHY_SPREAD_MV) * 50 / (BAD_SPREAD_MV - HEALTHY_SPREAD_MV);
  }
}
