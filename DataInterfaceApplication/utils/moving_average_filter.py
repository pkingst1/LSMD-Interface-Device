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

    #Moving average implementation
    def _moving_average(self, data, window_size):
        smoothed = []
        half = window_size // 2
        for i in range(len(data)):
            start = max(0, i - half)
            end = min(len(data), i + half + 1)
            window = data[start:end]
            smoothed.append(sum(window) / len(window))
        return smoothed

    #Set window size
    def set_window_size(self, window_size):
        self.window_size = window_size
    
    #Get window size
    def get_window_size(self):
        return self.window_size