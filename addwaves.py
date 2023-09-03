import matplotlib.pyplot as plt
import numpy as np

time = np.arange(0, 1, 0.001)
samples2 = np.sin(time * np.pi * 2 * 20) + np.sin(time * np.pi * 2 * 15) + np.sin(time * np.pi * 2 * 10)
timesplit = time[:len(time)//7]
timesplit = np.append(timesplit, [timesplit, timesplit, timesplit, timesplit, timesplit, timesplit])
samples3 = np.sin(timesplit * np.pi * 2 * 20) + np.sin(timesplit * np.pi * 2 * 15) + np.sin(timesplit * np.pi * 2 * 10)
_, (ax1, ax2) = plt.subplots(2)
ax1.plot(samples2)
ax2.plot(samples3)
plt.show()