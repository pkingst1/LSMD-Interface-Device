/*******************************************************************************
  ADC Module Source File

  File Name:
    adc.c

  Summary:
    ADC sampling, accumulation, and averaging on PIC32MX274F256B.

  Description:
    Timer 3 triggers ADC conversions at ~1200Hz. Once ADC_SAMPLE_COUNT
    samples have been accumulated the average is calculated and transmitted
    over UART2. Start/stop control is exposed via ADC_Module_Start() and
    ADC_Module_Stop() so the UART command handler can drive sampling without
    needing direct access to internal state.
*******************************************************************************/

#include <stdio.h>       // sprintf
#include "adc.h"
#include "uart_debug.h"
#include "definitions.h"

// *****************************************************************************
// Section: Configuration
// *****************************************************************************

// Number of ADC samples to collect before calculating and sending an average.
// Timer 3 triggers the ADC at ~1200Hz, so 1200 samples = ~1 second of data.
#define ADC_SAMPLE_COUNT    1


// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

// Running total of raw ADC readings accumulated across ADC_SAMPLE_COUNT calls
static volatile uint32_t adcSum      = 0;

// Number of ADC samples collected so far in the current averaging window
static volatile uint32_t sampleCount = 0;

// Flag set by ADC_Callback when enough samples are ready to process
static volatile bool dataReady = false;

// Flag indicating whether ADC sampling is currently active
static volatile bool samplingActive = false;


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

    // Snapshot and reset shared variables to minimise the window where the
    // ADC interrupt could modify them mid-calculation
    uint32_t currentSum   = adcSum;
    uint32_t currentCount = sampleCount;
    adcSum      = 0;
    sampleCount = 0;
    dataReady   = false;

    if (currentCount == 0) return;

    uint32_t average = currentSum / currentCount;

    char buf[32];
    sprintf(buf, "%u\r\n", (unsigned int)average);
    UART_Debug_Send(buf);
}

/*******************************************************************************
 End of File
*******************************************************************************/
