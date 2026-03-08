/*******************************************************************************
  Command Dispatcher Header

  File Name:
    command.h

  Summary:
    Shared start/stop command handling for all communication sources.

  Description:
    This is the ONLY place where start/stop logic lives. Every communication
    module (UART2 debug, UART1 BLE, and future USB CDC) calls
    Command_Dispatch() when it has a complete command string. The dispatcher
    decides what to do and routes the response back to the correct peripheral.

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND SOURCE (e.g. USB CDC):
      1. Add a new entry to CMD_Source_t below (e.g. CMD_SOURCE_USB_CDC)
      2. Add a case for it inside Command_Dispatch() in command.c
      3. Point that case at the send function for the new peripheral
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND (e.g. "status"):
      1. Add an else-if block inside Command_Dispatch() in command.c
      2. No changes needed in this header file
    -------------------------------------------------------------------------
*******************************************************************************/

#ifndef COMMAND_H
#define COMMAND_H

#include <stdbool.h>
#include <stdint.h>


// *****************************************************************************
// Section: Types
// *****************************************************************************

/*
 * CMD_Source_t
 *
 * Identifies which communication peripheral sent a command. The dispatcher
 * uses this to select the correct send function so the acknowledgement
 * response always goes back to the same peripheral the command came from.
 *
 * Current sources:
 *   CMD_SOURCE_UART2_DEBUG  - PC debug terminal on UART2
 *   CMD_SOURCE_UART1_BLE    - BLE module on UART1 at 115200 baud
 *   CMD_SOURCE_USB_CDC      - USB CDC virtual COM port (reserved, not yet wired up)
 *
 * TO ADD A NEW SOURCE:
 *   Add a new enum entry here, then handle it in command.c
 */
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
 * Command_Dispatch
 *
 * The single entry point for all command processing. Call this from any
 * communication module (uart_debug.c, uart_ble.c, future usb_cdc.c) once
 * a complete, null-terminated command string has been assembled.
 *
 * What it does:
 *   1. Selects the correct response send function based on 'source'
 *   2. Compares 'cmd' against all known commands (case-sensitive)
 *   3. Executes the matching action (ADC, LED, etc.)
 *   4. Sends the acknowledgement back over the originating peripheral only
 *
 * Parameters:
 *   cmd    - Null-terminated command string (e.g. "start", "stop")
 *            Caller is responsible for stripping the newline before calling.
 *            Must not be NULL.
 *   source - Which peripheral this command arrived on (see CMD_Source_t)
 *
 * Supported commands (all case-sensitive, no whitespace):
 *   "start"  ->  LED on, ADC sampling begins,  responds "\r\nok_start\r\n"
 *   "stop"   ->  LED off, ADC sampling stops,  responds "\r\nok_stop\r\n"
 *
 * Unknown or empty commands are silently discarded ? no response is sent.
 *
 * TO ADD A NEW COMMAND:
 *   Add an else-if block in Command_Dispatch() in command.c only.
 *   No changes needed here.
 */
void Command_Dispatch(const char *cmd, CMD_Source_t source);


#endif /* COMMAND_H */

/*******************************************************************************
 End of File
*******************************************************************************/
