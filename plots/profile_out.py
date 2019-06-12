#!/usr/bin/env python3

import matplotlib.pyplot as plt
from matplotlib import cm

win = [10, 20, 30, 40, 50, 60, 70]

filt1 = [8.620, 39.797, 91.884, 166.525, 264.098, 397.831, 503.851]
tot1 = [41.631, 79.902, 131.073, 206.537, 304.067, 440.481, 542.067]

filt2 = [9.903, 48.342, 102.289, 183.240, 278.696, 372.581, 499.786]
tot2 = [45.814, 90.438, 143.266, 223.356, 318.200, 410.445, 537.984]

filt3 = [13.092, 47.237, 97.560, 180.128, 258.039, 366.517, 483.018]
tot3 = [42.465, 87.669, 137.842, 218.666, 296.935, 404.366, 520.000]

plt.plot(win, filt1, color=cm.plasma(0), label='$t_{filter}, \sigma_{col} = 10$')
plt.plot(win, tot1, '--', color=cm.plasma(0), label='$t_{total}, \sigma_{col} = 10$')

plt.plot(win, filt2, color=cm.plasma(0.5), label='$t_{filter}, \sigma_{col} = 20$')
plt.plot(win, tot2, '--', color=cm.plasma(0.5), label='$t_{total}, \sigma_{col} = 20$')

plt.plot(win, filt3, color=cm.plasma(0.9), label='$t_{filter}, \sigma_{col} = 30$')
plt.plot(win, tot3, '--', color=cm.plasma(0.9), label='$t_{total}, \sigma_{col} = 30$')


plt.legend(loc=0)

plt.xlabel('Window size [px]')
plt.ylabel('Time [s]')

plt.savefig('runtime.pdf', bbox_inches='tight')
plt.show()
