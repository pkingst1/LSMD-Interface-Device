/*******************************************************************************
  Command Dispatcher Header

  File Name:
    command.h

  Summary:
    Shared start/stop command handling and all I2C output for all sources.

  Description:
    This is the ONLY place where start/stop logic and I2C output live.
    Every communication module (UART2 debug, UART1 BLE, and future USB CDC)
    calls Command_Dispatch() when it has a complete command string.

    Command_Init() must be called once at startup to register the ADC result
    callback that drives the 30-second second-device read interval.

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND SOURCE (e.g. USB CDC):
      1. Add a new entry to CMD_Source_t below
      2. Add a case for it inside Command_Dispatch() in command.c
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND (e.g. "status"):
      Add an else-if block inside Command_Dispatch() in command.c only.
      No changes needed in this header.
    -------------------------------------------------------------------------
*******************************************************************************/

#ifndef COMMAND_H
#define COMMAND_H

#include <stdbool.h>
#include <stdint.h>


// *****************************************************************************
// Section: Types
// *****************************************************************************

typedef enum
{
    CMD_SOURCE_UART2_DEBUG = 0,     // PC debug terminal on UART2
    CMD_SOURCE_UART1_BLE,           // BLE module on UART1 (115200 baud)
    CMD_SOURCE_USB_CDC              // USB CDC virtual COM port (future use)
} CMD_Source_t;


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * Command_Init
 *
 * Initialises the command module. Must be called once during system startup,
 * after SYS_Initialize() and after ADC_RegisterResultCallback() is available,
 * before the main loop begins.
 *
 * What it does:
 *   - Resets the 30-second I2C device 2 tick counter
 *   - Registers Command_OnADCResult with ADC_RegisterResultCallback() so
 *     this module is notified each time a new ADC average is ready
 */
void Command_Init(void);

/*
 * Command_Dispatch
 *
 * The single entry point for all command processing. Call this from any
 * communication module once a complete, null-terminated command string
 * has been assembled.
 *
 * Parameters:
 *   cmd    - Null-terminated command string (e.g. "start", "stop").
 *            Caller must strip the newline before calling. Must not be NULL.
 *   source - Which peripheral this command arrived on (see CMD_Source_t)
 *
 * Supported commands (case-sensitive, no whitespace):
 *   "start"  ->  LED on,  ADC sampling begins, ADC value sent over I2C
 *   "stop"   ->  LED off, ADC sampling stops,  ADC value sent over I2C
 *
 * Unknown or empty commands are silently discarded.
 */
void Command_Dispatch(const char *cmd, CMD_Source_t source);


#endif /* COMMAND_H */

/*******************************************************************************
 End of File
*******************************************************************************/
