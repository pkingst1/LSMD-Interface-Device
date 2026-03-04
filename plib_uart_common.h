/*******************************************************************************
  UART Communications Module Header

  File Name:
    uart_debug.h

  Summary:
    Public interface for UART2 command reception and processing.

  Description:
    Provides callback registration and the main-loop processing function
    for receiving and acting on text commands over UART2.
*******************************************************************************/

#ifndef UART_COMMS_H
#define UART_COMMS_H

#include <stdint.h>
#include "definitions.h"

// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

// UART_Debug_Init
//
// Registers the RX callback and arms the first UART2 read.
// Call once during system initialisation, after SYS_Initialize().
void UART_Debug_Init(void);

// UART2_RX_Callback
//
// Hardware interrupt callback. Register via UART_Debug_Init().
// Pushes each received byte into the circular queue and re-arms the read.
void UART2_RX_Callback(uintptr_t context);

// UART_Debug_Process
//
// Call from the main loop on every iteration.
// Drains the RX queue, echoes characters, and dispatches complete commands.
void UART_Debug_Process(void);

// UART_Debug_Send
//
// Sends a null-terminated string over UART2 using the shared TX buffer.
// Waits for any in-progress transmission to finish before sending.
// Call this from other modules (e.g. adc.c) to transmit data.
void UART_Debug_Send(const char *str);

#endif /* UART_COMMS_H */

/*******************************************************************************
 End of File
*******************************************************************************/