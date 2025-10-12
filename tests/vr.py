import soxr
import numpy as np
import matplotlib.pyplot as plt


def make_tone(freq, sr, duration):
    # make reference tone
    length = int(sr * duration)
    sig = np.sin(2 * np.pi * freq / sr * np.arange(length))
    sig = sig * np.hanning(length)
    
    return np.stack([sig, np.zeros_like(sig)], axis=-1)

'''
rs = soxr.ResampleStream(1, 20, 1, vr=True)
print(rs.delay())

rs.set_io_ratio(10, 1)

resampled = rs.resample_chunk(np.zeros(1000).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = resampled.copy()

resampled = rs.resample_chunk(np.ones(1000).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

rs.set_io_ratio(1, 1)
# rs.clear()

resampled = rs.resample_chunk(np.zeros(1000).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(np.ones(1000).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

rs.set_io_ratio(10, 1)

resampled = rs.resample_chunk(np.zeros(1000).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(np.ones(1000).astype(np.float32), last=True)
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])


print(cat.shape)
plt.plot(cat)
plt.show()
'''


rs = soxr.ResampleStream(10, 1, 2, vr=True)
print(rs.delay())

rs.set_io_ratio(5, 1)

resampled = rs.resample_chunk(np.zeros((0, 2)).astype(np.float32))
resampled = rs.resample_chunk(np.zeros((10, 2)).astype(np.float32))
resampled = rs.resample_chunk(np.zeros((0, 2)).astype(np.float32))

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = resampled.copy()

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

rs.set_io_ratio(10, 1)
# rs.clear()

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

rs.set_io_ratio(5, 1)

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32))
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])

resampled = rs.resample_chunk(make_tone(30, 5000, 0.5).astype(np.float32), last=True)
print(resampled.shape)
print(rs.delay())
cat = np.concatenate([cat, resampled])


print(f'{cat.shape = }')
plt.plot(cat)
plt.show()
