"""
Piecewise Linear Calibration - ADC to Newton conversion using linear interpolation
----------------------------------------------------------------------------------
Takes calibration points (ADC, Newton) captured during 5-point calibration and
builds a sorted lookup table. For any raw ADC input, finds the two bracketing
calibration points and linearly interpolates between them.
 
Designed for the Omega LC703-300 load cell:
    - Linearity: ±0.10% FSO (±1.33N at 300 lb capacity)
    - Hysteresis: ±0.10% FSO (±1.33N)
    - Repeatability: ±0.05% FSO (±0.67N)
 
Piecewise linear is appropriate here because the linearity error is smooth and
small (±1.33N), and the hysteresis floor (±1.33N) is the same magnitude —
a fancier interpolation curve cannot resolve errors below the hysteresis limit.
 
With 5 calibration points at 0/25/50/75/100% of range, piecewise linear captures
nearly all correctable nonlinearity. Residual interpolation error between points
is a fraction of the linearity spec.
 
Usage:
    cal = PiecewiseLinearCalibration()
    cal.load_points([(0.0, 102.3), (25.0, 307.8), (50.0, 512.1), (75.0, 718.5), (100.0, 921.0)])
    corrected = cal.adc_to_newtons(410.0)
    corrected_list = cal.adc_to_newtons_list([410.0, 510.2, 615.8])
 
Interpolation formula between two bracketing points:
    F = N_low + (ADC_raw - ADC_low) * (N_high - N_low) / (ADC_high - ADC_low)
 
For ADC values outside the calibration range, extrapolation uses the slope
of the nearest segment (first or last pair of calibration points).
"""

import json
import os
from datetime import date
 
class PiecewiseLinearCalibration:
    def __init__(self):
        #Sorted lookup table: list of (adc_value, newton_value) sorted by ADC ascending
        #Built from calibration points when load_points() is called
        self.lookup_table = []
 
        #Flag indicating whether calibration data has been loaded
        self.is_calibrated = False

        self.calibration_date = None
 
    #Load calibration points and build the sorted lookup table
    #Points are (newton_value, adc_value) tuples from the 5-point capture process
    def load_points(self, calibration_points):
        if len(calibration_points) < 2:
            return
 
        #Convert (newton, adc) pairs to (adc, newton) sorted by ADC ascending
        self.lookup_table = sorted(
            [(adc, newton) for newton, adc in calibration_points],
            key=lambda pair: pair[0]
        )
        self.is_calibrated = True
 
    #Convert a single raw ADC value to calibrated Newtons
    #Finds the two bracketing calibration points and linearly interpolates
    def adc_to_newtons(self, adc_raw):
        if not self.is_calibrated or len(self.lookup_table) < 2:
            return adc_raw
 
        table = self.lookup_table
 
        #Find the two bracketing calibration points
        adc_low, newton_low, adc_high, newton_high = self._find_bracket(adc_raw)
 
        #Guard against identical ADC values at two calibration points
        if adc_high == adc_low:
            return newton_low
 
        #Linear interpolation (or extrapolation if outside calibration range)
        slope = (newton_high - newton_low) / (adc_high - adc_low)
        corrected_newtons = newton_low + (adc_raw - adc_low) * slope
        return corrected_newtons
 
    #Convert a list of raw ADC values to calibrated Newtons
    def adc_to_newtons_list(self, adc_values):
        return [self.adc_to_newtons(adc) for adc in adc_values]
 
    #Find the two calibration points that bracket the given ADC value
    #Returns (adc_low, newton_low, adc_high, newton_high)
    def _find_bracket(self, adc_raw):
        table = self.lookup_table
 
        #Below lowest calibration point — extrapolate from first segment
        if adc_raw <= table[0][0]:
            adc_low, newton_low = table[0]
            adc_high, newton_high = table[1]
            return adc_low, newton_low, adc_high, newton_high
 
        #Above highest calibration point — extrapolate from last segment
        if adc_raw >= table[-1][0]:
            adc_low, newton_low = table[-2]
            adc_high, newton_high = table[-1]
            return adc_low, newton_low, adc_high, newton_high
 
        #Walk the table to find the bracketing segment
        for i in range(len(table) - 1):
            if table[i][0] <= adc_raw <= table[i + 1][0]:
                adc_low, newton_low = table[i]
                adc_high, newton_high = table[i + 1]
                return adc_low, newton_low, adc_high, newton_high
 
        #Fallback — should never reach here with valid sorted table
        adc_low, newton_low = table[-2]
        adc_high, newton_high = table[-1]
        return adc_low, newton_low, adc_high, newton_high
 
    #Get calibration points for display in results card
    #Returns list of dicts with newton_entered and adc_captured
    def get_display_points(self):
        if not self.is_calibrated:
            return []
        #lookup_table is (adc, newton) sorted by adc — return as (newton, adc) for display
        return [{'newton_entered': newton, 'adc_captured': adc} for adc, newton in self.lookup_table]
 
    #Get the sorted lookup table (for persistence/debugging)
    def get_lookup_table(self):
        return list(self.lookup_table)
 
    #Reset calibration state
    def reset(self):
        self.lookup_table = []
        self.is_calibrated = False

    #Save lookup table and calibration date to JSON
    def save_to_file(self, file_path):
        data = {
            "lookup_table": self.lookup_table,
            "calibration_date": date.today().isoformat()  #eg "2026-04-01"
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    #Load lookup table from JSON, restores calibrated state
    def load_from_file(self, file_path):
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.lookup_table = [tuple(pair) for pair in data["lookup_table"]]
            self.is_calibrated = len(self.lookup_table) >= 2

            #Parse date if present — may be absent in older calibration files
            date_str = data.get("calibration_date", "")
            if date_str:
                self.calibration_date = date.fromisoformat(date_str)
            else:
                self.calibration_date = None

            return self.is_calibrated
        except Exception:
            return False