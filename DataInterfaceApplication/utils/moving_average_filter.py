"""
Moving Average Filter - Smooths data by averaging over a window
"""

class MovingAverageFilter:
    #Initialize with window size 20
    def __init__(self, window_size=20):
        self.window_size = window_size

    #Apply filter to data, returns filtered list of data
    def apply(self, force_data):
        """
        Apply moving average filter to a list/deque of force values.
        Returns a filtered list.
        """
        data = list(force_data)
        return self._moving_average(data, self.window_size)

    #Moving average implementation — clamps window at edges instead of shrinking
    def _moving_average(self, data, window_size):
        if len(data) == 0:
            return []

        smoothed = []
        half = window_size // 2
        last_valid_start = len(data) - window_size

        for i in range(len(data)):
            #Clamp the window start so it never shrinks at edges
            #At the beginning: window stays anchored at index 0
            #At the end: window stays anchored so it always contains window_size samples
            start = max(0, min(i - half, last_valid_start))
            end = start + window_size

            #If data is shorter than window size, just use all data
            if end > len(data):
                start = 0
                end = len(data)

            window = data[start:end]
            smoothed.append(sum(window) / len(window))

        return smoothed

    #Set window size
    def set_window_size(self, window_size):
        self.window_size = window_size
    
    #Get window size
    def get_window_size(self):
        return self.window_size