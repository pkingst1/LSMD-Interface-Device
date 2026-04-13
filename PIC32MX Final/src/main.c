/*******************************************************************************
  Main Source File

  File Name:
    main.c

  Summary:
    System entry point and main loop for PIC32MX274F256B ADC/UART application.

  Description:
    Initialises all peripherals then enters the main loop. The main loop is
    intentionally kept thin - each module owns its own state and exposes a
    single Process() function that is called here on every iteration.

    -------------------------------------------------------------------------
    PERIPHERAL OVERVIEW:
      UART2  - Debug terminal (PC). Commands: "start", "stop". Echo enabled.
      UART1  - BLE module (115200 baud). Same commands. No echo.
      ADC    - Triggered by Timer 3 at ~1200 Hz. Averages samples (~1 s).
      Timer3 - Started/stopped by ADC_Module_Start() / ADC_Module_Stop().
      LED    - On while sampling is active, off when stopped.
      I2C1   - Master. Two devices on the same bus (both managed in command.c):
                 0x10  - Slave PIC. Receives ADC value on start/stop.
                 TBD   - Second IC. Read every 30 seconds.
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    COMMAND FLOW:
      Any UART receives "start" or "stop"
        -> uart_debug.c / uart_ble.c assembles the string
        -> Command_Dispatch() in command.c executes the action
        -> ADC value sent to slave PIC (0x10) via I2C1
        -> Response sent back over the same UART the command came from

      Every ~30 ADC averages (~30 s):
        -> ADC_Process() fires Command_OnADCResult() callback
        -> command.c reads the second I2C device
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    HANDS-OFF FILES (MCC Harmony generated - do not edit):
      initialization.c, definitions.h, device.h, toolchain_specifics.h,
      xc32_monitor.c, interrupts.c, interrupts.h, exceptions.c,
      plib_uart1.c/h, plib_uart2.c/h, plib_adc.c/h, plib_tmr3.c/h,
      plib_gpio.c/h, plib_evic.c/h, plib_clk.c/h, plib_i2c1_master.c/h
    -------------------------------------------------------------------------
*******************************************************************************/

#include <stddef.h>         // NULL
#include <stdbool.h>        // true, false
#include <stdlib.h>         // EXIT_FAILURE
#include "definitions.h"    // All MCC Harmony peripheral drivers (hands-off)
#include "adc.h"            // ADC_CallbackRegister(), ADC_Enable(), ADC_Process()
#include "uart_debug.h"     // UART_Debug_Init(), UART_Debug_Process()
#include "uart_ble.h"       // UART_BLE_Init(), UART_BLE_Process()
#include "command.h"        // Command_Init(), Command_Dispatch(), CMD_Source_t


// *****************************************************************************
// Section: Main Entry Point
// *****************************************************************************

int main(void)
{
    // -----------------------------------------------------------------------
    // System Initialisation
    // Initialises all MCC Harmony peripherals (Clock, GPIO, UARTs, Timer3,
    // ADC, I2C1, EVIC, Interrupts). Must remain first.
    // -----------------------------------------------------------------------
    SYS_Initialize(NULL);

    // -----------------------------------------------------------------------
    // LED Setup
    // -----------------------------------------------------------------------
    LED_OutputEnable();
    LED_Set();

    // -----------------------------------------------------------------------
    // ADC Setup
    // -----------------------------------------------------------------------
    ADC_CallbackRegister(ADC_Callback, 0);
    ADC_Enable();

    // -----------------------------------------------------------------------
    // UART2 Debug Terminal Setup
    // -----------------------------------------------------------------------
    UART_Debug_Init();

    // -----------------------------------------------------------------------
    // UART1 BLE Module Setup
    // -----------------------------------------------------------------------
    UART_BLE_Init();

    // -----------------------------------------------------------------------
    // Command Module Setup
    // Registers the ADC result callback so command.c receives a notification
    // each time a new average is ready (~1 s) to drive the 30-second
    // second-device I2C read interval.
    // Must be called after ADC setup so the callback registration succeeds.
    // -----------------------------------------------------------------------
    Command_Init();
    
    Control_3V3V_Set();
    Control_10V_Set();
    volatile uint32_t coldSettle = 1000000;  // much longer on first boot
    while(coldSettle--);

    // -----------------------------------------------------------------------
    // Main Loop
    // -----------------------------------------------------------------------
    while (true)
    {
        SYS_Tasks();



        // Drain the UART2 RX queue and dispatch any complete commands.
        UART_Debug_Process();

        // Drain the UART1 RX queue and dispatch any complete commands.
        UART_BLE_Process();

        // Calculate ADC average when ready, send over UARTs, and fire
        // the Command_OnADCResult callback for I2C tick counting.
        ADC_Process();
    }

    return (EXIT_FAILURE);
}

/*******************************************************************************
 End of File
*******************************************************************************/