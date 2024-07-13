'''
Freeform Rigging and Animation Tools
Copyright (C) 2020  Micah Zahm

Freeform Rigging and Animation Tools is free software: you can redistribute it 
and/or modify it under the terms of the GNU General Public License as published 
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Freeform Rigging and Animation Tools is distributed in the hope that it will 
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Freeform Rigging and Animation Tools.  
If not, see <https://www.gnu.org/licenses/>.
'''

#def butter_bandpass(lowcut, highcut, fs, order=3):
#    nyq = 0.5 * fs
#    low = lowcut / nyq
#    high = highcut / nyq

#    b, a = butter(order, [low, high], btype='band')
#    return b, a


#def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
#    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
#    y = lfilter(b, a, data)
#    return y

def lowpass(data, N, Wn):
    '''
    Perform a butterwork lowpass filter on the input keyframe_data, order, frequency

    Args:
        data (list<float>): List of floats that define a curve
        N (int): The order for the filter
        Wn (float): The frequency for the filter, from 0 to 1

    Returns:
        list<float>. Filtered curve with 'jitter' removed
    '''
    # internal import for optional python module.  Prevents errors for users without the module installed
    from scipy.signal import butter, lfilter

    b, a = butter(N, Wn, btype='lowpass', output='ba')
    y = lfilter(b, a, data)

    return y