"""
Butterworth Filter - Low-pass filter for signal smoothing
"""

import numpy as np

class ButterworthFilter:
    def __init__(self, cutoff=20.0, sample_rate=1200.0):
        self.cutoff = cutoff
        self.sample_rate = sample_rate

    #Design 4th order Butterworth cascading two 2nd order biquad filters
    def _design_butterworth_filter(self):
        #Normalize cutoff to nyquist, pre-warp for bilinear transform
        nyquist = self.sample_rate / 2.0
        normalized_cutoff = self.cutoff / nyquist
        prewarped_cutoff = 2.0 * np.tan(np.pi * normalized_cutoff / 2.0)

        #Q values for two pole pairs 4th order Butterworth
        pole_pair_q_values =  [
          (1.0 / (2.0 * np.cos(3 * np.pi / 8))),
            (1.0 / (2.0 * np.cos(1 * np.pi / 8))),
        ]
        
        #Apply bilinear transform to each 2nd order section
        biquad_sections = []
        for q_factor in pole_pair_q_values:
            gain = prewarped_cutoff / 2.0
            gain_squared = gain * gain

            numerator_b0 = gain_squared / (1.0 + gain / q_factor + gain_squared)
            numerator_b1 = 2.0 * numerator_b0
            numerator_b2 = numerator_b0

            denominator_a1 = 2.0 * (gain_squared - 1.0) / (1.0 + gain / q_factor + gain_squared)
            denominator_a2 = (1.0 - gain / q_factor + gain_squared) / (1.0 + gain / q_factor + gain_squared)

            biquad_sections.append((
                np.array([numerator_b0, numerator_b1, numerator_b2]),      #Numerator coefficients
                np.array([1.0, denominator_a1, denominator_a2])            #Denominator coefficients
            ))

        return biquad_sections

    #Direct form II, infinite impulse response (IIR) filter implementation
    def _apply_forward(self, numerator_coefficients, denominator_coefficients, input_signal):
        output_signal = np.zeros(len(input_signal))
        for sample_index in range(len(input_signal)):
            output_signal[sample_index] = numerator_coefficients[0] * input_signal[sample_index]
            if sample_index >= 1:
                output_signal[sample_index] += (numerator_coefficients[1] * input_signal[sample_index-1]
                                              - denominator_coefficients[1] * output_signal[sample_index-1])
            if sample_index >= 2:
                output_signal[sample_index] += (numerator_coefficients[2] * input_signal[sample_index-2]
                                              - denominator_coefficients[2] * output_signal[sample_index-2])
        return output_signal

    #Forward backward filtering for zero phase distortion
    def _apply_section_forward_backward(self, numerator_coefficients, denominator_coefficients, input_signal):
        forward_pass = self._apply_forward(numerator_coefficients, denominator_coefficients, input_signal)
        backward_pass = self._apply_forward(numerator_coefficients, denominator_coefficients, forward_pass[::-1])
        return backward_pass[::-1]

    #Cascade both biquad sections in series
    def apply(self, force_data):
        if len(force_data) == 0:
            return list(force_data)

        filtered_signal = np.array(list(force_data), dtype=float)
        biquad_sections = self._design_butterworth_filter()

        for numerator_coefficients, denominator_coefficients in biquad_sections:
            filtered_signal = self._apply_section_forward_backward(numerator_coefficients, denominator_coefficients, filtered_signal)

        return filtered_signal.tolist()

    #Setters
    def set_cutoff(self, cutoff):
        self.cutoff = cutoff

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate