/*******************************************************************************
  /*******************************************************************************
  UART Debug Module Source File

  File Name:
    uart_debug.c

  Summary:
    UART2 command reception and processing on PIC32MX274F256B.

  Description:
    Receives plain-text commands ("start", "stop") from a PC debug terminal
    connected on UART2. Uses a circular queue to decouple the hardware RX
    interrupt from the main loop so no bytes are lost between loop iterations.

    Each received character is echoed back so the terminal (e.g. PuTTY) shows
    what is being typed.

    When a complete newline-terminated command is assembled it is passed to
    Command_Dispatch() in command.c, which owns all start/stop logic and sends
    the acknowledgement response back over UART2.

    -------------------------------------------------------------------------
    HARDWARE:
      Peripheral : UART2
      Baud rate  : 115200  (U2BRG = 77 at 36 MHz peripheral clock, BRGH = 1)
      Connected  : PC via USB-UART bridge or direct serial
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    CONFIGURABLE SIZES (edit here if needed):
      RX_QUEUE_SIZE   - Circular queue depth (bytes). Increase if characters
                        are being dropped between main loop iterations.
      RX_BUFFER_SIZE  - Max command length in characters (including null).
                        Must be > the longest command string + 1.
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    MODULE DEPENDENCIES:
      command.h    - Command_Dispatch() for routing completed commands
      definitions.h- UART2_* PLIB functions from MCC Harmony (hands-off)
    -------------------------------------------------------------------------
*******************************************************************************/

#include <string.h>         // memset(), strlen(), strncpy()
#include "uart_debug.h"
#include "command.h"        // Command_Dispatch()


// *****************************************************************************
// Section: Configuration
// *****************************************************************************

/*
 * RX_BUFFER_SIZE
 *
 * Maximum number of characters accepted in a single command (including the
 * null terminator). Commands longer than this are truncated ? the excess
 * characters are dropped and the truncated string is dispatched on newline.
 *
 * Current commands are 5 chars max ("start\0" = 6), so 32 is very generous.
 * Increase this if you add longer commands in command.c.
 */
#define RX_BUFFER_SIZE      32U

/*
 * RX_QUEUE_SIZE
 *
 * Depth of the circular queue between the RX interrupt and the main loop.
 * Each slot holds one received byte. If the main loop is slow and this fills
 * up, incoming bytes are silently dropped.
 *
 * 16 bytes is sufficient at 115200 baud given the main loop runs at ~MHz.
 * Increase if you observe dropped characters during fast typing.
 */
#define RX_QUEUE_SIZE       16U


// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

/*
 * rxByte
 *
 * Single-byte landing buffer passed to UART2_Read(). The UART2 PLIB writes
 * the received byte here and fires UART2_RX_Callback(). Do not read this
 * directly ? use the circular queue instead.
 */
static char rxByte;

/*
 * Circular Queue (rxQueue, rxQueueHead, rxQueueTail)
 *
 * Decouples the RX interrupt from the main loop.
 *   rxQueueHead - written by UART2_RX_Callback() (interrupt context)
 *   rxQueueTail - read by UART_Debug_Process()   (main loop context)
 *
 * The queue is full when (head + 1) % SIZE == tail.
 * The queue is empty when head == tail.
 *
 * Both head and tail are volatile because they are shared between interrupt
 * and main-loop contexts.
 */
static volatile char    rxQueue[RX_QUEUE_SIZE];
static volatile uint8_t rxQueueHead = 0U;
static volatile uint8_t rxQueueTail = 0U;

/*
 * rxBuffer / rxIndex
 *
 * Accumulates received characters until a newline is received, at which
 * point the null-terminated string is dispatched via Command_Dispatch().
 * rxIndex tracks the next write position in the buffer.
 */
static char    rxBuffer[RX_BUFFER_SIZE];
static uint8_t rxIndex = 0U;

/*
 * txBuffer
 *
 * Internal buffer used by UART_Debug_Send(). Copied from the caller's string
 * so the caller does not need to keep its string valid during background TX.
 * Max usable payload: sizeof(txBuffer) - 1 characters.
 *
 * TO INCREASE MAX SEND LENGTH: increase the array size here.
 */
static char txBuffer[32];


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * UART_Debug_Send
 * See uart_debug.h for full description.
 */
void UART_Debug_Send(const char *str)
{
    // Wait for any previous transmission to complete before starting a new one.
    // This prevents the TX buffer being overwritten mid-send.
    while (UART2_WriteIsBusy());

    // Copy into the internal TX buffer so the caller's string does not need
    // to remain valid during the background TX interrupt.
    // strncpy guarantees no overrun; the last byte is force-set to '\0'.
    strncpy(txBuffer, str, sizeof(txBuffer) - 1U);
    txBuffer[sizeof(txBuffer) - 1U] = '\0';

    // Initiate the transmission. UART2_Write() starts the TX interrupt chain;
    // the PLIB handles the rest in the background.
    UART2_Write(txBuffer, strlen(txBuffer));
}

/*
 * UART_Debug_Init
 * See uart_debug.h for full description.
 */
void UART_Debug_Init(void)
{
    // Register our callback with the UART2 PLIB.
    // UART2_RX_Callback will be called each time one byte is received.
    UART2_ReadCallbackRegister(UART2_RX_Callback, 0);

    // Wait for any in-progress read to finish (should not be busy at startup,
    // but guard here for safety)
    while (UART2_ReadIsBusy());

    // Arm the first 1-byte read. The callback re-arms itself on each call,
    // so this only needs to be done once here at initialisation.
    UART2_Read(&rxByte, 1);
}

/*
 * UART2_RX_Callback
 * See uart_debug.h for full description.
 * Called in interrupt context ? keep this as short as possible.
 */
void UART2_RX_Callback(uintptr_t context)
{
    // Calculate where the next head position would be
    uint8_t nextHead = (rxQueueHead + 1U) % RX_QUEUE_SIZE;

    if (nextHead != rxQueueTail)
    {
        // Queue has space ? push the received byte in
        rxQueue[rxQueueHead] = rxByte;
        rxQueueHead = nextHead;
    }
    // else: queue is full, byte is silently dropped.
    // Increase RX_QUEUE_SIZE above if this becomes a problem.

    // Re-arm for the next incoming byte.
    // rxByte will be overwritten when the next byte arrives.
    UART2_Read(&rxByte, 1);
}

/*
 * UART_Debug_Process
 * See uart_debug.h for full description.
 * Call from the main loop on every iteration.
 */
void UART_Debug_Process(void)
{
    // Drain all bytes currently available in the queue
    while (rxQueueTail != rxQueueHead)
    {
        // Read one byte from the queue and advance the tail
        char c = rxQueue[rxQueueTail];
        rxQueueTail = (rxQueueTail + 1U) % RX_QUEUE_SIZE;

        // Echo the character back so the terminal shows what is being typed.
        // This is specific to the debug channel ? uart_ble.c does not echo.
        while (UART2_WriteIsBusy());
        UART2_Write(&c, 1);

        if (c == '\r' || c == '\n')
        {
            // Newline received ? command is complete.
            // Null-terminate the accumulated buffer.
            rxBuffer[rxIndex] = '\0';

            // Only dispatch if something was actually typed (ignore blank lines)
            if (rxIndex > 0U)
            {
                // Hand the completed command to the central dispatcher.
                // command.c will execute the action and send the response
                // back over UART2 via UART_Debug_Send().
                Command_Dispatch(rxBuffer, CMD_SOURCE_UART2_DEBUG);
            }

            // Reset the buffer ready for the next command
            memset(rxBuffer, 0, sizeof(rxBuffer));
            rxIndex = 0U;
        }
        else
        {
            // Regular character ? accumulate into the command buffer.
            // Guard against overflow: if the buffer is full, extra characters
            // are silently dropped. The command will be unrecognised and
            // discarded by Command_Dispatch() anyway.
            if (rxIndex < RX_BUFFER_SIZE - 1U)
            {
                rxBuffer[rxIndex++] = c;
            }
        }
    }
}

/*******************************************************************************
 End of File
*******************************************************************************/