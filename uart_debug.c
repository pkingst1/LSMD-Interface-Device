/*******************************************************************************
  Main Source File

  Company:
    Microchip Technology Inc.

  File Name:
    main.c

  Summary:
    UART command handling with ADC sampling on PIC32MX274F256B

  Description:
    Initialises all peripherals and enters the main loop. ADC sampling and
    averaging are handled by adc.c. UART command reception and dispatch are
    handled by uart_debug.c.
*******************************************************************************/

#include <stddef.h>       // NULL
#include <stdbool.h>      // true, false
#include <stdlib.h>       // EXIT_FAILURE
#include "definitions.h"  // All Harmony peripheral drivers
#include "adc.h"
#include "uart_debug.h"


// *****************************************************************************
// Section: Main Entry Point
// *****************************************************************************

int main(void)
{
    // Initialize all peripherals (clocks, GPIO, UART2, ADC, Timer 3, EVIC)
    SYS_Initialize(NULL);

    // Configure the LED pin as output, starting on
    LED_OutputEnable();
    LED_Set();

    // Register ADC callback and enable ADC
    // Timer 3 is started by ADC_Module_Start() when "start" is received
    ADC_CallbackRegister(ADC_Callback, 0);
    ADC_Enable();

    // Register the UART RX callback and arm the first read
    UART_Debug_Init();

    // --- Main Loop ---
    while (true)
    {
        SYS_Tasks();

        // Drain the RX queue and process any complete commands
        UART_Debug_Process();

        // Calculate and transmit ADC average when enough samples are ready
        ADC_Process();
    }

    return (EXIT_FAILURE);
}

/*******************************************************************************
 End of File
*******************************************************************************/
