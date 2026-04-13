/*******************************************************************************
  Main Source File

  Company:
    Microchip Technology Inc.

  File Name:
    main.c

  Summary:
    ADC sampling with UART output on PIC32MX274F256B

  Description:
    Samples the ADC at ~1200Hz via Timer 3. The ADC interrupt does minimal
    work ? it only accumulates samples and sets a flag when ready. The main
    loop handles the averaging and UART transmission when the flag is set,
    keeping the interrupt as short as possible. The LED turns on at startup
    to confirm the code is running. Send "START" to begin sampling and
    "STOP" to halt it.
*******************************************************************************/

#include <stdio.h>        // sprintf
#include <stddef.h>       // NULL
#include <stdbool.h>      // true, false
#include <stdlib.h>       // EXIT_FAILURE
#include <string.h>       // strlen, strcmp
#include "definitions.h"  // All Harmony peripheral drivers (UART, ADC, GPIO, etc.)


// *****************************************************************************
// Section: Configuration
// *****************************************************************************

// Number of ADC samples to collect before calculating and sending an average.
// Timer 3 triggers the ADC at ~1200Hz, so 1200 samples = ~1 second of data.
// Change this value to adjust how many samples are averaged each cycle.
#define ADC_SAMPLE_COUNT    1200


// *****************************************************************************
// Section: Global Variables
// *****************************************************************************

// Running total of raw ADC readings ? accumulated across ADC_SAMPLE_COUNT calls
volatile uint32_t adcSum      = 0;

// Number of ADC samples collected so far in the current averaging window
volatile uint32_t sampleCount = 0;

// Flag set by ADC_Callback when enough samples are ready to process
volatile bool dataReady = false;

// Flag set by UART_RX_Callback when a valid START command is received.
// ADC sampling will not begin until this is true.
volatile bool adcEnabled = false;

// Transmit buffer for UART ? declared globally so it remains valid in memory
// while the TX interrupt is sending it in the background
static char txBuffer[64];

// Receive buffer for incoming UART commands ? holds characters as they arrive
// until a full command string is assembled
static char rxBuffer[16];

// Single byte buffer used by the UART RX interrupt to receive one byte at a
// time. Declared globally so both the initial UART2_Read call in main and
// the UART_RX_Callback share the exact same memory address.
static char rxByte = 0;

// Tracks how many characters have been received into rxBuffer so far
static uint8_t rxIndex = 0;


// *****************************************************************************
// Section: Processing Functions
// *****************************************************************************

// Calculate_ADC_Average
//
// Called from the main loop when dataReady is true.
// Snapshots and resets the shared accumulators, calculates the average,
// formats it, and transmits it over UART2.
void Calculate_ADC_Average(void)
{
    // Snapshot and reset shared variables immediately to minimize the window
    // where the ADC interrupt could modify them mid-calculation
    uint32_t currentSum   = adcSum;
    uint32_t currentCount = sampleCount;
    adcSum      = 0;
    sampleCount = 0;
    dataReady   = false;

    // Guard against divide-by-zero
    if (currentCount == 0) return;

    // Calculate the integer average of all collected samples
    uint32_t average = currentSum / currentCount;

    // Wait for any previous UART transmission to finish
    while (UART2_WriteIsBusy());

    // Format just the average value followed by a newline
    sprintf(txBuffer, "%u\r\n", (unsigned int)average);

    // Transmit ? the TX interrupt handles sending in the background
    UART2_Write(txBuffer, strlen(txBuffer));
}


// *****************************************************************************
// Section: Interrupt Callbacks
// *****************************************************************************

// UART_RX_Callback
//
// Called automatically by the UART2 RX interrupt each time a byte is received.
// Assembles bytes into rxBuffer and checks for known commands after each byte.
// Sends confirmation string directly from the callback ? confirmed working on
// this hardware from the loopback test.
//
// Commands:
//   "START" ? enables ADC sampling, sends "OK_START\r\n"
//   "STOP"  ? disables ADC sampling, sends "OK_STOP\r\n"
void UART_RX_Callback(uintptr_t context)
{
    // Filter out non-printable bytes ? handles UTF-8 BOM and control characters
    if (rxByte >= 0x20 && rxByte <= 0x7E)
    {
        if (rxIndex < sizeof(rxBuffer) - 1)
        {
            // Add byte to buffer and null terminate for strcmp
            rxBuffer[rxIndex++] = rxByte;
            rxBuffer[rxIndex]   = '\0';

            // Check for "START"
            if (strcmp(rxBuffer, "START") == 0)
            {
                adcEnabled  = true;
                rxIndex     = 0;
                rxBuffer[0] = '\0';
                while (UART2_WriteIsBusy());
                UART2_Write("OK_START\r\n", 10);
            }
            // Check for "STOP"
            else if (strcmp(rxBuffer, "STOP") == 0)
            {
                adcEnabled  = false;
                adcSum      = 0;
                sampleCount = 0;
                dataReady   = false;
                rxIndex     = 0;
                rxBuffer[0] = '\0';
                while (UART2_WriteIsBusy());
                UART2_Write("OK_STOP\r\n", 9);
            }
            // Buffer full with no match ? reset
            else if (rxIndex >= sizeof(rxBuffer) - 1)
            {
                rxIndex     = 0;
                rxBuffer[0] = '\0';
            }
        }
    }

    // Re-arm the RX interrupt for the next byte
    UART2_Read(&rxByte, 1);
}

// ADC_Callback
//
// Called automatically by the hardware every time the ADC completes a conversion.
// Timer 3 triggers conversions at ~1200Hz, so this runs ~1200 times per second.
//
// Kept intentionally minimal:
//   1. Clear the ADC interrupt flag
//   2. Accumulate the sample
//   3. Set dataReady when enough samples are collected
void ADC_Callback(uintptr_t context)
{
    // Clear the ADC interrupt flag ? required to allow the next conversion to trigger
    EVIC_SourceStatusClear(INT_SOURCE_ADC);

    // Do nothing until a START command has been received
    if (!adcEnabled) return;

    // Accumulate the sample
    adcSum += ADC_ResultGet(ADC_RESULT_BUFFER_0);
    sampleCount++;

    // Signal the main loop when enough samples are ready
    if (sampleCount >= ADC_SAMPLE_COUNT)
    {
        dataReady = true;
    }
}


// *****************************************************************************
// Section: Main Entry Point
// *****************************************************************************

int main(void)
{
    // Initialize all peripherals (clocks, GPIO, UART2, ADC, Timer 3, EVIC)
    SYS_Initialize(NULL);

    // Turn the LED on to confirm the board is alive
    LED_OutputEnable();
    LED_Toggle();

    // Send a startup message so the PC knows the board is ready to receive
    // commands ? confirmed working from loopback test
    UART2_Write("READY\r\n", 7);

    // Register RX callback and arm the RX interrupt for the first byte
    UART2_ReadCallbackRegister(UART_RX_Callback, 0);
    UART2_Read(&rxByte, 1);

    // Register ADC callback, enable ADC, start Timer 3
    ADC_CallbackRegister(ADC_Callback, 0);
    ADC_Enable();
    TMR3_Start();

    // --- Main Loop ---
    while (true)
    {
        SYS_Tasks();

        // Process ADC average when enough samples are ready
        if (dataReady)
        {
            Calculate_ADC_Average();
        }
    }

    return (EXIT_FAILURE);
}

/*******************************************************************************
 End of File
*******************************************************************************/