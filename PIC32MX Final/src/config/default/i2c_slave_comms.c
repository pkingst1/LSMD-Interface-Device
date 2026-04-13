/*******************************************************************************
  I2C Communications Module Source File

  File Name:
    i2c_slave_comms.c

  Summary:
    I2C1 master communications for two devices on the same bus.

  Description:
    This file contains two sections:

    SECTION 1 - Slave PIC (0x10):
      Sends a 16-bit ADC value to the slave PIC.
      Transaction: START | 0x10 | HIGH_BYTE | LOW_BYTE | STOP
      Called from command.c on "start" and "stop" commands.

    SECTION 2 - Device 2 (address TBD):
      Placeholder for a second I2C device on the same bus.
      Read every 30 seconds, triggered by command.c via the ADC result
      callback. Address, transaction type, and result handling are marked
      TODO for completion once the IC is known.
*******************************************************************************/

#include "i2c_slave_comms.h"
#include "definitions.h"


// *****************************************************************************
// Section 1: Slave PIC (0x10)
// *****************************************************************************

#define I2C_SLAVE_ADDRESS      0x10U

// CRITICAL: Must be size 2 to hold High and Low bytes
static uint8_t txBuf[2];

// Master Code (PIC32)
void I2C_SlaveComms_Send(uint16_t adcValue) {
    while (I2C1_IsBusy());
    // Convert to Newtons (Match your slave's 0-500 N range)
    uint16_t force = (uint16_t) (adcValue);
    // HIGH BYTE: Extract bits 8-15
    // This goes into the first slot of the buffer
    txBuf[0] = (uint8_t)(force >> 8); 
    // LOW BYTE: Extract bits 0-7
    // This goes into the second slot
    txBuf[1] = (uint8_t)(force & 0xFF);
    
    // Use Write - This sends START | 0x20 | High | Low | STOP
    I2C1_Write(0x10, txBuf, 2); 
}

bool I2C_SlaveComms_IsBusy(void)
{
    return I2C1_IsBusy();
}


// *****************************************************************************
// Section 2: Device 2 (address TBD)
// *****************************************************************************

/*
 * I2C_DEVICE2_ADDR
 * TODO: Replace 0x00 with the correct 7-bit address of the second IC.
 */
#define I2C_DEVICE2_ADDR        0x00U   // TODO: set correct address

/*
 * I2C_DEVICE2_RX_BUF_SIZE
 * TODO: Set to the number of bytes the IC returns per read (e.g. 1 or 2).
 */
#define I2C_DEVICE2_RX_BUF_SIZE 2U      // TODO: set correct byte count

/*
 * rxBuf
 * Receive buffer for the device 2 read result. Module-level so it stays
 * valid during the background I2C interrupt transfer after I2C1_Read() returns.
 */
static uint8_t rxBuf[I2C_DEVICE2_RX_BUF_SIZE];

/*
 * I2C_Device2_Read
 *
 * Initiates the I2C read transaction for device 2.
 * Called from command.c every 30 seconds when the bus is free.
 *
 * TODO: Uncomment ONE of the patterns below that matches your IC and
 *       delete the others. Then add result handling in command.c after
 *       the read completes (poll I2C_SlaveComms_IsBusy() if needed).
 */
void I2C_Device2_Read(void)
{
    // --- Pattern A: Simple read (no register address needed) ---
    // I2C1_Read(I2C_DEVICE2_ADDR, rxBuf, I2C_DEVICE2_RX_BUF_SIZE);

    // --- Pattern B: Register-based read (write register, then read) ---
    // static uint8_t regAddr = 0x00U;  // TODO: set correct register address
    // I2C1_Write(I2C_DEVICE2_ADDR, &regAddr, 1U);
    // while (I2C1_IsBusy());
    // I2C1_Read(I2C_DEVICE2_ADDR, rxBuf, I2C_DEVICE2_RX_BUF_SIZE);

    // --- Pattern C: Single byte read ---
    // I2C1_Read(I2C_DEVICE2_ADDR, rxBuf, 1U);

    // -----------------------------------------------------------------------
    // TODO: Once the read completes (I2C1_IsBusy() false), rxBuf[] holds
    // the result. Example for a 16-bit big-endian value:
    //   while (I2C1_IsBusy());
    //   uint16_t result = ((uint16_t)rxBuf[0] << 8U) | rxBuf[1];
    // Add your result handling in command.c after calling this function.
    // -----------------------------------------------------------------------
}

/*******************************************************************************
 End of File
*******************************************************************************/