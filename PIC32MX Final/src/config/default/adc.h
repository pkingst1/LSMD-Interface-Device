/*******************************************************************************
  ADC Module Header

  File Name:
    adc.h

  Summary:
    Public interface for ADC sampling and averaging on PIC32MX274F256B.

  Description:
    Provides callback registration, start/stop control, and the main-loop
    processing function for ADC sample accumulation and UART transmission.

    ADC_RegisterResultCallback() allows another module (e.g. command.c) to
    be notified each time a new average is ready, without adc.c needing any
    knowledge of what that module does with the value. This keeps adc.c
    free of any I2C, LCD, or other output dependencies.
*******************************************************************************/

#ifndef ADC_MODULE_H
#define ADC_MODULE_H

#include <stdint.h>
#include <stdbool.h>
#include "definitions.h"


// *****************************************************************************
// Section: Types
// *****************************************************************************

/*
 * ADC_ResultCallback_t
 *
 * Function pointer type for the result-ready callback.
 * The callback receives the new 32-bit averaged ADC value as its argument.
 *
 * The callback is called from ADC_Process() in the main loop context,
 * NOT from an interrupt, so it is safe to call I2C or UART functions
 * from inside it.
 */
typedef void (*ADC_ResultCallback_t)(uint32_t average);


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * ADC_Module_Start
 *
 * Resets accumulators, activates sampling, and starts Timer 3.
 * Call this when the "start" command is received.
 */
void ADC_Module_Start(void);

/*
 * ADC_Module_Stop
 *
 * Deactivates sampling, stops Timer 3, and resets all accumulators.
 * Call this when the "stop" command is received.
 */
void ADC_Module_Stop(void);

/*
 * ADC_GetLastAverage
 *
 * Returns the most recent calculated ADC average.
 * Updated by ADC_Process() each time a new average is ready.
 * Returns 0 if no average has been calculated yet since startup.
 */
uint32_t ADC_GetLastAverage(void);

/*
 * ADC_RegisterResultCallback
 *
 * Registers a function to be called from ADC_Process() each time a new
 * averaged result is ready. Only one callback can be registered at a time;
 * calling this again replaces the previous registration.
 *
 * Pass NULL to deregister.
 *
 * The callback runs in main loop context so it is safe to call I2C, UART,
 * or any other non-interrupt-context function from inside it.
 *
 * Parameters:
 *   cb - Function pointer matching ADC_ResultCallback_t, or NULL
 */
void ADC_RegisterResultCallback(ADC_ResultCallback_t cb);

/*
 * ADC_Callback
 *
 * Hardware interrupt callback. Register this with ADC_CallbackRegister().
 * Accumulates samples and sets dataReady when ADC_SAMPLE_COUNT is reached.
 */
void ADC_Callback(uintptr_t context);

/*
 * ADC_Process
 *
 * Call from the main loop. When dataReady is true, calculates the average,
 * stores it (readable via ADC_GetLastAverage()), transmits it over both
 * UARTs, then calls the registered result callback (if any).
 */
void ADC_Process(void);


#endif /* ADC_MODULE_H */

/*******************************************************************************
 End of File
*******************************************************************************/