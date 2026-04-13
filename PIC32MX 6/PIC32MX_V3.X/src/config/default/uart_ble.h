/*******************************************************************************
  BLE UART Module Header

  File Name:
    uart_ble.h

  Summary:
    Public interface for BLE module command reception on UART2.

  Description:
    Provides the initialisation, RX callback, main-loop processing function,
    and transmit helper for the BLE module connected on UART2 at 115200 baud.

    This module is intentionally structured to mirror uart_debug.h so that
    adding or modifying either channel is straightforward. The key difference
    is that received characters are NOT echoed back on this channel ? BLE
    central devices do not expect character echo.

    Command processing is NOT handled here. When a complete command is
    assembled, it is passed to Command_Dispatch() in command.c, which owns
    all start/stop logic and routes responses back to the correct peripheral.

    -------------------------------------------------------------------------
    HARDWARE:
      Peripheral : UART2
      Baud rate  : 115200
      Device     : BLE module (exact module configurable via UART2 MCC settings)
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO CHANGE THE BAUD RATE:
      Reconfigure UART2 in MCC Harmony and regenerate plib_uart1.c/.h.
      No changes needed in this file or uart_ble.c.
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO CHANGE THE QUEUE OR BUFFER SIZES:
      Edit BLE_RX_QUEUE_SIZE and BLE_RX_BUFFER_SIZE in uart_ble.c.
      No changes needed in this header.
    -------------------------------------------------------------------------
*******************************************************************************/

#ifndef UART_BLE_H
#define UART_BLE_H

#include <stdint.h>
#include "definitions.h"


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * UART_BLE_Init
 *
 * Registers the UART2 RX interrupt callback and arms the first 1-byte read.
 * Must be called once during startup, after SYS_Initialize(), before the
 * main loop begins.
 *
 * Internally calls:
 *   UART2_ReadCallbackRegister() - registers UART2_RX_Callback
 *   UART2_Read()                 - arms the first byte reception
 */
void UART_BLE_Init(void);

/*
 * UART2_RX_Callback
 *
 * Hardware interrupt callback fired by the UART2 PLIB each time a byte is
 * received. This function is registered automatically by UART_BLE_Init() ?
 * do not call it directly.
 *
 * What it does:
 *   1. Pushes the received byte into the circular queue (if space exists)
 *   2. Re-arms UART2_Read() for the next incoming byte
 *
 * If the queue is full the incoming byte is silently dropped. Increase
 * BLE_RX_QUEUE_SIZE in uart_ble.c if this becomes a problem.
 */
void UART2_RX_Callback(uintptr_t context);

/*
 * UART_BLE_Process
 *
 * Call this on every iteration of the main loop (alongside
 * UART_Debug_Process() and ADC_Process()).
 *
 * What it does:
 *   1. Drains all available bytes from the circular RX queue
 *   2. Accumulates characters into a command buffer
 *   3. On receiving '\r' or '\n', null-terminates the buffer and calls
 *      Command_Dispatch(buffer, CMD_SOURCE_UART2_BLE)
 *   4. Resets the buffer ready for the next command
 *
 * Characters are NOT echoed ? BLE central devices do not expect echo.
 */
void UART_BLE_Process(void);

/*
 * UART_BLE_Send
 *
 * Sends a null-terminated string over UART2 to the BLE module.
 * Blocks until any in-progress UART2 transmission completes, then
 * copies the string into the internal TX buffer and initiates the send.
 *
 * Called by Command_Dispatch() in command.c to send acknowledgements.
 * Can also be called directly from other modules if needed.
 *
 * Parameters:
 *   str - Null-terminated string to transmit. Must not be NULL.
 *         Maximum length is 31 characters (TX buffer is 32 bytes including
 *         the null terminator). Longer strings are silently truncated.
 *
 * TO CHANGE THE MAX TX LENGTH:
 *   Edit the bleTxBuffer size in uart_ble.c.
 */
void UART_BLE_Send(const char *str);


#endif /* UART_BLE_H */

/*******************************************************************************
 End of File
*******************************************************************************/