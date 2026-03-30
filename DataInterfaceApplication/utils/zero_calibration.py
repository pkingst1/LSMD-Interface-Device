"""
Zero Calibration - Computes zero offset from sampled force data
Discards intial samples, applies signal processing filters,
then averages remaining samples to determine DC offset.
Offset is then subtracted from all subsequent readings.
"""

class ZeroCalibration:
    def __init__(self):
        #Samples to discard
        self.discard_samples = 3600

        #Number of samples to use for averaging
        self.sample_count = 1200

        #Total samples needed
        self.total_samples = self.discard_samples + self.sample_count

        #Computed zero offset value
        self.zero_offset = 0.0

        #Flag indicating whether calibration is performed
        self.is_calibrated = False

    #Compute zero offset from collected raw samples
    def compute_zero_offset(self, raw_samples, filters=None):
        if len(raw_samples) < self.total_samples:
                    return 0.0
        
        #Discard intial samples, keep sample count samples
        trimmed = raw_samples[self.discard_samples:self.discard_samples + self.sample_count]

        #Apply filter chain
        filtered = list(trimmed)
        if filters:
            for f in filters:
                filtered = f.apply(filtered)

        #Computer DC offset as average of filtered samples
        self.zero_offset = sum(filtered) / len(filtered)
        self.is_calibrated = True

        return self.zero_offset

    
    #Apply zero offset to single force value
    def apply_correction(self, raw_value):
        if not self.is_calibrated:
            return raw_value
        
        return raw_value - self.zero_offset

    #Apply zero offset to list of force values
    def apply_correction_list(self, raw_values):
        if not self.is_calibrated:
            return list(raw_values)
        
        return [v - self.zero_offset for v in raw_values]

    #Reset calibration state
    def reset(self):
        self.zero_offset = 0.0
        self.is_calibrated = False
    
    #Get current zero offset value
    def get_zero_offset(self):
        return self.zero_offset