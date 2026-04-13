/*******************************************************************************
  LCD Module Header

  File Name:
    lcd.h

  Summary:
    Public interface for the 1602IIC LCD display driven over I2C1.

  Description:
    Provides initialisation and display functions for a 16x2 HD44780-compatible
    LCD fitted with a PCF8574-based I2C backpack at address 0x27.

    The module uses the I2C1 master PLIB (I2C1_Write / I2C1_IsBusy) generated
    by MCC Harmony.

    -------------------------------------------------------------------------
    NON-BLOCKING DESIGN - IMPORTANT:
    LCD writes are spread across main loop iterations via LCD_Process().
    Neither LCD_Display_ADC() nor LCD_Process() block the main loop for more
    than one I2C transaction (~90 us at 100 kHz standard mode) per call.
    This keeps the UART RX queues draining normally on every loop iteration
    so PuTTY never sees a stall or dropped characters.

    LCD_Init() IS blocking - it is called once before the main loop starts,
    so stalling there is safe.
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    HARDWARE:
      Peripheral : I2C1
      Device     : 1602IIC (HD44780 + PCF8574 backpack)
      I2C address: 0x27
      Display    : 16 columns x 2 rows
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    PCF8574 -> HD44780 BIT MAPPING (standard 1602IIC wiring):
      P7 P6 P5 P4  P3  P2  P1  P0
      D7 D6 D5 D4  BL  EN  RW  RS
    -------------------------------------------------------------------------

    -------------------------------------------------------------------------
    TO CHANGE THE I2C ADDRESS:
      Edit LCD_I2C_ADDR in lcd.c. No changes needed in this header.
    -------------------------------------------------------------------------
*******************************************************************************/

#ifndef LCD_H
#define LCD_H

#include <stdint.h>
#include <stdbool.h>


// *****************************************************************************
// Section: Public Functions
// *****************************************************************************

/*
 * LCD_Init
 *
 * Initialises the HD44780 controller via the PCF8574 I2C backpack using the
 * standard 4-bit initialisation sequence specified in the HD44780 datasheet.
 *
 * BLOCKING. Call once during system startup, after SYS_Initialize() and
 * before the main loop begins. Safe to block here because the main loop has
 * not started yet.
 *
 * On return the display is:
 *   - Cleared and cursor at home (row 0, col 0)
 *   - 4-bit interface, 2 lines, 5x8 font
 *   - Display on, cursor off, blink off
 *   - Backlight on
 */
void LCD_Init(void);

/*
 * LCD_Display_ADC
 *
 * Queues a new ADC value to be written to the LCD.
 * Does NOT perform any I2C transactions itself - the actual writes happen
 * incrementally inside LCD_Process() on subsequent main loop iterations.
 *
 * NON-BLOCKING. Safe to call from ADC_Process().
 *
 * Parameters:
 *   value - Raw ADC reading to display (uint32_t, expected range 0-1023)
 */
void LCD_Display_ADC(uint32_t value);

/*
 * LCD_Process
 *
 * Call from the main loop on every iteration, alongside UART_Debug_Process()
 * and UART_BLE_Process().
 *
 * Advances the LCD write state machine by one I2C transaction per call.
 * Each call blocks for at most the duration of one I2C transaction
 * (~90 us at 100 kHz standard mode, ~22 us at 400 kHz fast mode).
 * Does nothing if there is no pending update or the I2C bus is still busy.
 *
 * NON-BLOCKING per main loop iteration.
 */
void LCD_Process(void);


#endif /* LCD_H */

/*******************************************************************************
 End of File
*******************************************************************************/
