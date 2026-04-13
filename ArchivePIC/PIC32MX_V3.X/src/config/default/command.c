/*******************************************************************************
  Command Dispatcher Source File

  File Name:
    command.c

  Summary:
    Shared start/stop command handling for all communication sources.

  Description:
    Command_Dispatch() is the single point of truth for all command logic.
    No other file should call ADC_Module_Start(), ADC_Module_Stop(), LED_Set(),
    or LED_Clear() directly in response to a received command ? all of that
    goes through here so behaviour is always consistent regardless of source.

    -------------------------------------------------------------------------
    MODULE DEPENDENCIES (files this module calls into):
      adc.h        - ADC_Module_Start(), ADC_Module_Stop()
      uart_debug.h - UART_Debug_Send()   (response back to UART2 terminal)
      uart_ble.h   - UART_BLE_Send()     (response back to UART1 BLE module)
      definitions.h- LED_Set(), LED_Clear() (GPIO macros from MCC Harmony)
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND SOURCE (e.g. USB CDC):
      1. Add the source to CMD_Source_t in command.h
      2. #include the new module's header below
      3. Add a case to the switch statement in Command_Dispatch() that sets
         sendFn to the new module's send function
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO ADD A NEW COMMAND (e.g. "status"):
      Add a new else-if block in the command parsing section below.
      Follow the same pattern as "start" and "stop".
    -------------------------------------------------------------------------
*******************************************************************************/

#include <string.h>         // strcmp()
#include "command.h"
#include "adc.h"            // ADC_Module_Start(), ADC_Module_Stop()
#include "uart_debug.h"     // UART_Debug_Send() - response to UART2 terminal
#include "uart_ble.h"       // UART_BLE_Send()   - response to UART1 BLE module
#include "definitions.h"    // LED_Set(), LED_Clear() GPIO macros


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

void Command_Dispatch(const char *cmd, CMD_Source_t source)
{
    // Guard: never process a NULL pointer
    if (cmd == NULL) { return; }

    // ------------------------------------------------------------------
    // Step 1: Select the response function for the originating source.
    //
    // sendFn is a function pointer set to whichever send function matches
    // the peripheral the command came in on. This means the acknowledgement
    // always goes back out over the same channel the command arrived on.
    //
    // TO ADD A NEW SOURCE:
    //   Add a new case here pointing sendFn at the new module's send function.
    //   e.g. case CMD_SOURCE_USB_CDC: sendFn = USB_CDC_Send; break;
    // ------------------------------------------------------------------
    void (*sendFn)(const char *) = NULL;

    switch (source)
    {
        case CMD_SOURCE_UART2_DEBUG:
            // Command came from the PC debug terminal on UART2
            sendFn = UART_Debug_Send;
            break;

        case CMD_SOURCE_UART1_BLE:
            // Command came from the BLE module on UART1 (115200 baud)
            sendFn = UART_BLE_Send;
            break;

        case CMD_SOURCE_USB_CDC:
            // USB CDC not yet implemented.
            // When ready: #include "usb_cdc.h" above and set sendFn here.
            // e.g. sendFn = USB_CDC_Send;
            sendFn = NULL;
            break;

        default:
            // Unknown source ? do nothing
            return;
    }

    // ------------------------------------------------------------------
    // Step 2: Match the command string and execute the action.
    //
    // All comparisons are case-sensitive and expect no leading/trailing
    // whitespace ? the caller (uart_debug.c / uart_ble.c) strips the newline
    // before calling here.
    //
    // TO ADD A NEW COMMAND:
    //   Copy the else-if pattern below. Call whatever functions you need,
    //   then call sendFn() with the acknowledgement string.
    // ------------------------------------------------------------------

    if (strcmp(cmd, "start") == 0)
    {
        // --- "start" command ---
        // Turn the LED on to show sampling is active
        LED_Set();
        // Start ADC accumulation (also starts Timer 3)
        ADC_Module_Start();
        // Acknowledge back to whichever source sent the command
        if (sendFn != NULL) { sendFn("\r\nok_start\r\n"); }
    }
    else if (strcmp(cmd, "stop") == 0)
    {
        // --- "stop" command ---
        // Turn the LED off to show sampling has stopped
        LED_Clear();
        // Stop ADC accumulation (also stops Timer 3)
        ADC_Module_Stop();
        // Acknowledge back to whichever source sent the command
        if (sendFn != NULL) { sendFn("\r\nok_stop\r\n"); }
    }

    // ------------------------------------------------------------------
    // Add further commands here using the same else-if pattern.
    // Unknown commands fall through silently with no response sent.
    // ------------------------------------------------------------------
}

/*******************************************************************************
 End of File
*******************************************************************************/