/*******************************************************************************
  BLE UART Module Source File

  File Name:
    uart_ble.c

  Summary:
    UART2 command reception from a BLE module on PIC32MX274F256B.

  Description:
    Receives plain-text commands ("start", "stop") from a BLE module over
    UART2 at 115200 baud. Uses a circular queue to decouple the hardware RX
    interrupt from the main loop so no bytes are lost between loop iterations.

    Characters are NOT echoed back ? BLE central devices do not expect echo.

    When a complete newline-terminated command is assembled it is passed
    directly to Command_Dispatch() in command.c, which owns all start/stop
    logic and sends the acknowledgement response back over UART2.

    -------------------------------------------------------------------------
    HARDWARE:
      Peripheral : UART2
      Baud rate  : 115200  (set in MCC Harmony, verified via plib_uart1.h)
      Connected  : BLE module
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    CONFIGURABLE SIZES (edit here if needed):
      BLE_RX_QUEUE_SIZE   - Circular queue depth (bytes). Increase if bytes
                            are being dropped between main loop iterations.
      BLE_RX_BUFFER_SIZE  - Max command length in characters (including null).
                            Must be > the longest command string + 1.
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    MODULE DEPENDENCIES:
      command.h    - Command_Dispatch() for routing completed commands
      definitions.h- UART2_* PLIB functions from MCC Harmony
    -------------------------------------------------------------------------
*******************************************************************************/

#include <string.h>         // memset(), strlen(), strncpy()
#include "uart_ble.h"
#include "command.h"        // Command_Dispatch()
#include "definitions.h"    // UART2_* PLIB functions


// *****************************************************************************
// Section: Configuration
// *****************************************************************************

/*
 * BLE_RX_BUFFER_SIZE
 *
 * Maximum number of characters accepted in a single command (including the
 * null terminator). Commands longer than this are truncated ? the excess
 * characters are dropped and the truncated string is dispatched on newline.
 *
 * Current commands are 5 chars max ("start\0" = 6), so 32 is very generous.
 * Increase this if you add longer commands in command.c.
 */
#define BLE_RX_BUFFER_SIZE      32U

/*
 * BLE_RX_QUEUE_SIZE
 *
 * Depth of the circular queue between the RX interrupt and the main loop.
 * Each slot holds one received byte. If the main loop is slow and this fills
 * up, incoming bytes are silently dropped.
 *
 * 16 bytes is sufficient at 115200 baud given the main loop runs at ~MHz.
 * Increase if you observe dropped characters.
 */
#define BLE_RX_QUEUE_SIZE       16U


// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

/*
 * bleByte
 *
 * Single-byte landing buffer passed to UART2_Read(). The UART2 PLIB writes
 * the received byte here and fires UART2_RX_Callback(). Do not read this
 * directly ? use the circular queue instead.
 */
static char bleByte;

/*
 * Circular Queue (bleQueue, bleQueueHead, bleQueueTail)
 *
 * Decouples the RX interrupt from the main loop.
 *   bleQueueHead - written by UART2_RX_Callback() (interrupt context)
 *   bleQueueTail - read by UART_BLE_Process()     (main loop context)
 *
 * The queue is full when (head + 1) % SIZE == tail.
 * The queue is empty when head == tail.
 *
 * Both head and tail are volatile because they are shared between interrupt
 * and main-loop contexts.
 */
static volatile char    bleQueue[BLE_RX_QUEUE_SIZE];
static volatile uint8_t bleQueueHead = 0U;
static volatile uint8_t bleQueueTail = 0U;

/*
 * bleRxBuffer / bleRxIndex
 *
 * Accumulates received characters until a newline is received, at which
 * point the null-terminated string is dispatched via Command_Dispatch().
 * bleRxIndex tracks the next write position in the buffer.
 */
static char    bleRxBuffer[BLE_RX_BUFFER_SIZE];
static uint8_t bleRxIndex = 0U;

/*
 * bleTxBuffer
 *
 * Internal buffer used by UART_BLE_Send(). Copied from the caller's string
 * so the caller does not need to keep its string valid during background TX.
 * Max usable payload: sizeof(bleTxBuffer) - 1 characters.
 *
 * TO INCREASE MAX SEND LENGTH: increase the array size here.
 */
static char bleTxBuffer[32];


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * UART_BLE_Init
 * See uart_ble.h for full description.
 */
void UART_BLE_Init(void)
{
    // Register our callback with the UART2 PLIB.
    // UART2_RX_Callback will be called each time one byte is received.
    UART2_ReadCallbackRegister(UART2_RX_Callback, 0);

    // Wait for any in-progress read to finish (should not be busy at startup,
    // but guard here for safety)
    while (UART2_ReadIsBusy());

    // Arm the first 1-byte read. The callback re-arms itself on each call,
    // so this only needs to be done once here at initialisation.
    UART2_Read(&bleByte, 1);
}

/*
 * UART2_RX_Callback
 * See uart_ble.h for full description.
 * Called in interrupt context ? keep this as short as possible.
 */
void UART2_RX_Callback(uintptr_t context)
{
    // Calculate where the next head position would be
    uint8_t nextHead = (bleQueueHead + 1U) % BLE_RX_QUEUE_SIZE;

    if (nextHead != bleQueueTail)
    {
        // Queue has space ? push the received byte in
        bleQueue[bleQueueHead] = bleByte;
        bleQueueHead = nextHead;
    }
    // else: queue is full, byte is silently dropped.
    // Increase BLE_RX_QUEUE_SIZE above if this becomes a problem.

    // Re-arm for the next incoming byte.
    // bleByte will be overwritten when the next byte arrives.
    UART2_Read(&bleByte, 1);
}

/*
 * UART_BLE_Process
 * See uart_ble.h for full description.
 * Call from the main loop on every iteration.
 */
void UART_BLE_Process(void)
{
    // Drain all bytes currently available in the queue
    while (bleQueueTail != bleQueueHead)
    {
        // Read one byte from the queue and advance the tail
        char c = bleQueue[bleQueueTail];
        bleQueueTail = (bleQueueTail + 1U) % BLE_RX_QUEUE_SIZE;

        // Echo the character back, matching debug channel behaviour.
        // Non-blocking: skip if TX is busy to avoid stalling the main loop.
        /*if (!UART2_WriteIsBusy())
        {
            UART2_Write(&c, 1);
        }*/

        if (c == '\r' || c == '\n')
        {
            // Newline received ? command is complete.
            // Null-terminate the accumulated buffer.
            bleRxBuffer[bleRxIndex] = '\0';

            // Only dispatch if something was actually received (ignore blank lines)
            if (bleRxIndex > 0U)
            {
                // Hand the completed command to the central dispatcher.
                // command.c will execute the action and send the response
                // back over UART2 via UART_BLE_Send().
                Command_Dispatch(bleRxBuffer, CMD_SOURCE_UART1_BLE);
            }

            // Reset the buffer ready for the next command
            memset(bleRxBuffer, 0, sizeof(bleRxBuffer));
            bleRxIndex = 0U;
        }
        else
        {
            // Regular character ? accumulate into the command buffer.
            // Guard against overflow: if the buffer is full, extra characters
            // are silently dropped. The command will be unrecognised and
            // discarded by Command_Dispatch() anyway.
            if (bleRxIndex < BLE_RX_BUFFER_SIZE - 1U)
            {
                bleRxBuffer[bleRxIndex++] = c;
            }
        }
    }
}

/*
 * UART_BLE_Send
 * See uart_ble.h for full description.
 */
void UART_BLE_Send(const char *str)
{
    // Wait for any previous transmission to complete before starting a new one.
    // This prevents the TX buffer being overwritten mid-send.
    while (UART2_WriteIsBusy());

    // Copy into the internal TX buffer so the caller's string does not need
    // to remain valid during the background TX interrupt.
    // strncpy guarantees no overrun; the last byte is force-set to '\0'.
    strncpy(bleTxBuffer, str, sizeof(bleTxBuffer) - 1U);
    bleTxBuffer[sizeof(bleTxBuffer) - 1U] = '\0';

    // Initiate the transmission. UART2_Write() starts the TX interrupt chain;
    // the PLIB handles the rest in the background.
    UART2_Write(bleTxBuffer, strlen(bleTxBuffer));
}

/*******************************************************************************
 End of File
*******************************************************************************/