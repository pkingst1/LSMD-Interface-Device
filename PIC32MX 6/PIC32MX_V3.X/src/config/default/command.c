/*******************************************************************************
  Command Dispatcher Source File
*******************************************************************************/

#include <string.h>
#include "command.h"
#include "adc.h"
#include "i2c_slave_comms.h"
#include "uart_debug.h"
#include "uart_ble.h"
#include "definitions.h"

// *****************************************************************************
// Section: Configuration
// *****************************************************************************

#define DEVICE2_TICKS_PER_READ  30U

// *****************************************************************************
// Section: Private Variables
// *****************************************************************************

static uint32_t device2TickCount = 0U;

// *****************************************************************************
// Section: Private Functions
// *****************************************************************************

static void Command_OnADCResult(uint32_t average)
{
    if (!I2C_SlaveComms_IsBusy())
    {
        I2C_SlaveComms_Send((uint16_t)average);
    }

    device2TickCount++;
    if (device2TickCount >= DEVICE2_TICKS_PER_READ)
    {
        device2TickCount = 0U;
        // Future: I2C_Device2_Read();
    }
}

// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

void Command_Init(void)
{
    device2TickCount = 0U;
    ADC_RegisterResultCallback(Command_OnADCResult);
}

void Command_Dispatch(const char *cmd, CMD_Source_t source)
{
    //UART_Debug_Send("dispatch called\r\n");  // ? add this
    //UART_Debug_Send(cmd);                    // ? add this
    //UART_Debug_Send("\r\n");                 // ? and this
    if (cmd == NULL) { return; }

    void (*sendFn)(const char *) = NULL;

    switch (source)
    {
        case CMD_SOURCE_UART2_DEBUG:
            sendFn = UART_Debug_Send;
            break;
        case CMD_SOURCE_UART1_BLE:
            sendFn = UART_BLE_Send;
            break;
        default:
            return;
    }

    if (sendFn == NULL) { return; }

    if (strcmp(cmd, "start") == 0)
    {
        // 1. Respond to UART first (Non-blocking)
        sendFn("\r\nok_start\r\n");

        // 2. Hardware Control
        ADC_Module_Start();

        // 3. Send CURRENT ADC Average over I2C
        if (!I2C_SlaveComms_IsBusy()) 
        {
            // This will send the 16-bit ADC value in Big-Endian format
            I2C_SlaveComms_Send((uint16_t)ADC_GetLastAverage());
            //I2C_SlaveComms_Send((uint16_t)'A');
        }

    }
    else if (strcmp(cmd, "stop") == 0)
    {
        sendFn("\r\nok_stop\r\n");

        LED_Clear();
        //Control_3V3V_Clear();
        //Control_10V_Clear();
        ADC_Module_Stop();

        // 4. Send FINAL ADC Average over I2C
        if (!I2C_SlaveComms_IsBusy()) 
        {
            I2C_SlaveComms_Send((uint16_t)ADC_GetLastAverage());
        }
    }
}