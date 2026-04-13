/*******************************************************************************
  I2C Communications Module Header

  File Name:
    i2c_slave_comms.h

  Summary:
    Public interface for all I2C1 master communications.

  Description:
    Declares functions for two devices sharing the I2C1 bus:

    SECTION 1 - Slave PIC (0x10):
      I2C_SlaveComms_Send()   - sends ADC value on start/stop commands
      I2C_SlaveComms_IsBusy() - bus busy check, used before device 2 reads

    SECTION 2 - Device 2 (address TBD):
      I2C_Device2_Read()      - initiates a read, called every 30 s from
                                command.c via the ADC result callback
*******************************************************************************/

#ifndef I2C_SLAVE_COMMS_H
#define I2C_SLAVE_COMMS_H

#include <stdint.h>
#include <stdbool.h>


// *****************************************************************************
// Section 1: Slave PIC (0x10)
// *****************************************************************************

/*
 * I2C_SlaveComms_Send
 *
 * Sends a 16-bit ADC value to the slave PIC at address 0x10.
 * Transaction: START | 0x10 | HIGH_BYTE | LOW_BYTE | STOP
 * Waits for any in-progress transfer to finish before sending.
 *
 * Parameters:
 *   adcValue - 16-bit value to transmit (range 0-1023 for 10-bit ADC)
 */
void I2C_SlaveComms_Send(uint16_t adcValue);

/*
 * I2C_SlaveComms_IsBusy
 *
 * Returns true if the I2C1 bus is currently busy, false if free.
 * Called by command.c before initiating a device 2 read to avoid conflicts.
 */
bool I2C_SlaveComms_IsBusy(void);


// *****************************************************************************
// Section 2: Device 2 (address TBD)
// *****************************************************************************

/*
 * I2C_Device2_Read
 *
 * Initiates a read from the second I2C device.
 * Called from command.c every 30 seconds when the bus is confirmed free.
 *
 * The transaction pattern (simple read, register-based, etc.) is selected
 * by uncommenting the correct pattern inside i2c_slave_comms.c.
 *
 * TODO: Complete the implementation in i2c_slave_comms.c once the IC is known.
 */
void I2C_Device2_Read(void);


#endif /* I2C_SLAVE_COMMS_H */

/*******************************************************************************
 End of File
*******************************************************************************/
