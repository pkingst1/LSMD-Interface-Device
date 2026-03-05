"""
Notch Filter - Attenuates specific frequency bands
"""

import numpy as np

class NotchFilter:
    #Initialize with frequency to attenuate, bandwidth and sample rate
    def __init__(self, frequency=60.0, bandwidth=5.0, sample_rate=1200.0):
        self.notch_frequency = frequency
        self.notch_bandwidth = bandwidth
        self.sample_rate = sample_rate

    #Compute filter coefficients
    def _design_notch_filter(self, frequency):
        w0 = 2 * np.pi * frequency / self.sample_rate
        bw = 2 * np.pi * self.notch_bandwidth / self.sample_rate
        r = 1 - (bw / 2)
        cos_w0 = np.cos(w0)

        b = np.array([1.0, -2.0 * cos_w0, 1.0])
        a = np.array([1.0, -2.0 * r * cos_w0, r * r])

        return b, a

    #Apply IIR filter in one direction
    def _apply_forward(self, b, a, data):
        output = np.zeros(len(data))
        for i in range(len(data)):
            output[i] = b[0] * data[i]
            if i >= 1:
                output[i] += b[1] * data[i-1] - a[1] * output[i-1]
            if i >= 2:
                output[i] += b[2] * data[i-2] - a[2] * output[i-2]
        return output

    #Forward backward filtering for zero phase distortion
    def _apply_forward_backward(self, b, a, data):
        forward = self._apply_forward(b, a, data)
        backward = self._apply_forward(b, a, forward[::-1])
        return backward[::-1]

    #Apply filter to a list/deque of force values, returns filtered list
    def apply(self, force_data):
        data = np.array(list(force_data), dtype=float)
        
        target_frequencies = [60.0] #change as required, initially was 50, 60, 100, 120, 150, 180

        for freq in target_frequencies:
            b, a = self._design_notch_filter(freq)
            data = self._apply_forward_backward(b, a, data)
        
        return data.tolist()

    def set_notch_freq(self, freq):
        self.notch_frequency = freq

    def set_bandwidth(self, bandwidth):
        self.notch_bandwidth = bandwidth

    def set_sample_rate(self, rate):
        self.sample_rate = rate