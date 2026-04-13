/*******************************************************************************
  ADC Module Source File

  File Name:
    adc.c

  Summary:
    ADC sampling, accumulation, and averaging on PIC32MX274F256B.

  Description:
    Timer 3 triggers ADC conversions at ~1200 Hz. Once ADC_SAMPLE_COUNT
    samples have been accumulated the average is calculated, transmitted
    over both UARTs, and passed to the registered result callback.

    This module has no knowledge of I2C, LCD, or any other output channel.
    All such behaviour is handled by the callback registered via
    ADC_RegisterResultCallback() - currently wired to command.c.
*******************************************************************************/

#include <stdio.h>          // sprintf
#include "adc.h"
#include "uart_debug.h"
#include "uart_ble.h"
#include "definitions.h"


// *****************************************************************************
// Section: Configuration
// *****************************************************************************

// Number of ADC samples to collect before calculating and sending an average.
// Timer 3 triggers the ADC at ~1200 Hz, so 1200 samples = ~1 second of data.
#define ADC_SAMPLE_COUNT    1

// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

static volatile uint32_t adcSum         = 0;
static volatile uint32_t sampleCount    = 0;
static volatile bool     dataReady      = false;
static volatile bool     samplingActive = false;

// Most recent calculated average. Read externally via ADC_GetLastAverage().
static volatile uint32_t lastAverage    = 0;

// Registered result-ready callback. NULL if none registered.
static ADC_ResultCallback_t resultCallback = NULL;


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

void ADC_Module_Start(void)
{
    adcSum         = 0;
    sampleCount    = 0;
    dataReady      = false;
    samplingActive = true;
    TMR3_Start();
}

void ADC_Module_Stop(void)
{
    samplingActive = false;
    TMR3_Stop();
    adcSum      = 0;
    sampleCount = 0;
    dataReady   = false;
}

uint32_t ADC_GetLastAverage(void)
{
    return lastAverage;
}

void ADC_RegisterResultCallback(ADC_ResultCallback_t cb)
{
    resultCallback = cb;
}

void ADC_Callback(uintptr_t context)
{
    EVIC_SourceStatusClear(INT_SOURCE_ADC);

    if (!samplingActive) return;

    adcSum += ADC_ResultGet(ADC_RESULT_BUFFER_0);
    sampleCount++;

    if (sampleCount >= ADC_SAMPLE_COUNT)
    {
        dataReady = true;
    }
}

void ADC_Process(void)
{
    if (!dataReady) return;
    uint32_t currentSum   = adcSum;
    uint32_t currentCount = sampleCount;
    adcSum      = 0;
    sampleCount = 0;
    dataReady   = false;
    if (currentCount == 0) return;
    lastAverage = currentSum / currentCount;
    // Transmit the value over both UARTs
    char buf[32];
    sprintf(buf, "%u\r\n", (unsigned int)lastAverage);
    UART_Debug_Send(buf);
    UART_BLE_Send(buf);
    // Notify the registered callback (e.g. command.c) that a new average
    // is ready. adc.c does not know or care what the callback does.
    if (resultCallback != NULL)
    {
        resultCallback(lastAverage);
    }
}


/*******************************************************************************
 End of File
*******************************************************************************/