/*******************************************************************************
  ADC Module Header

  File Name:
    adc.h

  Summary:
    Public interface for ADC sampling and averaging on PIC32MX274F256B.

  Description:
    Provides callback registration, start/stop control, and the main-loop
    processing function for ADC sample accumulation and UART transmission.
*******************************************************************************/

#ifndef ADC_MODULE_H
#define ADC_MODULE_H

#include <stdint.h>
#include <stdbool.h>
#include "definitions.h"

// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

// ADC_Module_Start
//
// Resets accumulators, activates sampling, and starts Timer 3.
// Call this when the "start" command is received.
void ADC_Module_Start(void);

// ADC_Module_Stop
//
// Deactivates sampling, stops Timer 3, and resets all accumulators.
// Call this when the "stop" command is received.
void ADC_Module_Stop(void);

// ADC_Callback
//
// Hardware interrupt callback. Register this with ADC_CallbackRegister().
// Accumulates samples and sets dataReady when ADC_SAMPLE_COUNT is reached.
void ADC_Callback(uintptr_t context);

// ADC_Process
//
// Call from the main loop. When dataReady is true, calculates the average
// of accumulated samples and transmits it via UART_Debug_Send().
void ADC_Process(void);

#endif /* ADC_MODULE_H */

/*******************************************************************************
 End of File
*******************************************************************************/