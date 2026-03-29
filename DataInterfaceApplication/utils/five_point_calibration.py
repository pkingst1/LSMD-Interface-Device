"""
Five Point Calibration - Captures and stores ADC readings at known Newton values
Collects 1100 raw ADC samples per point, discards first 100 samples,
applies filters, then averages to get reading.
Stores five (Newton, averaged ADC reading) pairs for later interpolation
"""

class FivePointCalibration:
    def __init__(self):
        #Samples to discard (transient settling)
        self.discard_samples = 3600
 
        #Number of samples to use for averaging
        self.sample_count = 1200
 
        #Total samples needed per capture point
        self.total_samples = self.discard_samples + self.sample_count
 
        #Storage for captured calibration points: list of (newton_value, adc_average) tuples
        self.calibration_points = []
 
        #Number of points required for full calibration
        self.num_points = 5
 
        #Flag indicating whether all 5 points have been captured
        self.is_calibrated = False
 
    #Compute averaged ADC value from collected raw samples for one calibration point
    #Same algorithm as zero calibration: discard initial, filter, average
    def compute_point_average(self, raw_samples, filters=None):
        if len(raw_samples) < self.total_samples:
            return None
 
        #Discard initial transient samples, keep sample_count samples
        trimmed = raw_samples[self.discard_samples:self.discard_samples + self.sample_count]
 
        #Apply filter chain (Notch → Butterworth → Moving Average)
        filtered = list(trimmed)
        if filters:
            for f in filters:
                filtered = f.apply(filtered)
 
        #Average filtered samples to get stable ADC reading
        adc_average = sum(filtered) / len(filtered)
        return adc_average
 
    #Store a captured calibration point (newton_value entered by user, adc_average computed)
    def add_point(self, newton_value, adc_average):
        self.calibration_points.append((newton_value, adc_average))
 
        #Check if all points captured
        if len(self.calibration_points) >= self.num_points:
            self.is_calibrated = True
 
    #Get number of points captured so far
    def get_captured_count(self):
        return len(self.calibration_points)
 
    #Get all captured calibration points
    def get_calibration_points(self):
        return list(self.calibration_points)
 
    #Reset calibration state for a fresh run
    def reset(self):
        self.calibration_points = []
        self.is_calibrated = False