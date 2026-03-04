/*******************************************************************************
  UART Communications Module Source File

  File Name:
    uart_debug.c

  Summary:
    UART2 command reception and processing on PIC32MX274F256B.

  Description:
    A circular queue decouples the RX interrupt callback from the main loop.
    Each received character is echoed back. On newline, the accumulated
    command string is compared against known commands and the appropriate
    action is taken via the ADC module's public interface.

    Supported commands:
      "start" - begins ADC sampling, responds "ok_start"
      "stop"  - stops ADC sampling, responds "ok_stop"
*******************************************************************************/

#include <string.h>   // strcmp, memset, strlen, strncpy
#include "uart_debug.h"
#include "adc.h"

// *****************************************************************************
// Section: Configuration
// *****************************************************************************

// Maximum number of characters to accept in a single command
#define RX_BUFFER_SIZE      32

// Size of the circular queue that decouples the RX callback from the main loop
#define RX_QUEUE_SIZE       16


// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

// Single byte landing buffer used by the UART2 RX interrupt
static char rxByte;

// Circular queue - the RX callback writes here, the main loop reads from here
static volatile char    rxQueue[RX_QUEUE_SIZE];
static volatile uint8_t rxQueueHead = 0;   // Callback writes to head
static volatile uint8_t rxQueueTail = 0;   // Main loop reads from tail

// Buffer to accumulate a full command string
static char rxBuffer[RX_BUFFER_SIZE];
static uint8_t rxIndex = 0;

// Transmit buffer for command responses
static char txBuffer[32];


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

void UART_Debug_Send(const char *str)
{
    while (UART2_WriteIsBusy());
    // Copy into txBuffer so the caller's string doesn't need to remain valid
    // during the background TX interrupt
    strncpy(txBuffer, str, sizeof(txBuffer) - 1);
    txBuffer[sizeof(txBuffer) - 1] = '\0';
    UART2_Write(txBuffer, strlen(txBuffer));
}

void UART_Debug_Init(void)
{
    UART2_ReadCallbackRegister(UART2_RX_Callback, 0);
    while (UART2_ReadIsBusy());
    UART2_Read(&rxByte, 1);
}

void UART2_RX_Callback(uintptr_t context)
{
    // Push byte into the queue if there is space
    uint8_t nextHead = (rxQueueHead + 1) % RX_QUEUE_SIZE;
    if (nextHead != rxQueueTail)
    {
        rxQueue[rxQueueHead] = rxByte;
        rxQueueHead = nextHead;
    }

    // Re-arm for the next incoming byte
    UART2_Read(&rxByte, 1);
}

void UART_Debug_Process(void)
{
    while (rxQueueTail != rxQueueHead)
    {
        char c = rxQueue[rxQueueTail];
        rxQueueTail = (rxQueueTail + 1) % RX_QUEUE_SIZE;

        // Echo the character back so PuTTY shows what you type
        while (UART2_WriteIsBusy());
        UART2_Write(&c, 1);

        // Newline or carriage return signals end of command
        if (c == '\r' || c == '\n')
        {
            rxBuffer[rxIndex] = '\0';  // Null-terminate the string

            if (strcmp(rxBuffer, "start") == 0)
            {
                LED_Set();
                ADC_Module_Start();
                UART_Debug_Send("\r\nok_start\r\n");
            }
            else if (strcmp(rxBuffer, "stop") == 0)
            {
                LED_Clear();
                ADC_Module_Stop();
                UART_Debug_Send("\r\nok_stop\r\n");
            }

            // Reset the buffer for the next command
            memset(rxBuffer, 0, sizeof(rxBuffer));
            rxIndex = 0;
        }
        else
        {
            // Accumulate the character, guard against overflow
            if (rxIndex < RX_BUFFER_SIZE - 1)
            {
                rxBuffer[rxIndex++] = c;
            }
        }
    }
}

/*******************************************************************************
 End of File
*******************************************************************************/
