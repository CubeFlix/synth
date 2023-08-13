import time
import numpy as np
import pyaudio
import midi

SAMPLE_RATE = 44100
FILE = "overworld.mid"
DURATION = 20

p = pyaudio.PyAudio()

def generate_sine(volume: float, sample_rate: int, duration: float, freq: float) -> np.array:
    return volume * (np.sin(2 * np.pi * np.arange(sample_rate * duration) * freq / sample_rate)).astype(np.float32)

def generate_square(volume: float, sample_rate: int, duration: float, freq: float) -> np.array:
    return volume * (np.sign(np.sin(2 * np.pi * np.arange(sample_rate * duration) * freq / sample_rate))).astype(np.float32)

def add_sample(master: np.array, sample_rate: int, start: float, sample: np.array):
    if int(sample_rate * start) >= len(master) or (int(sample_rate * start) + len(sample)) >= len(master):
        return
    master[int(sample_rate * start):int(sample_rate * start) + len(sample)] += sample

# generate samples, note conversion to float32 array
samples = generate_square(0, SAMPLE_RATE, DURATION, 440)
# convert midi into notes
notes = midi.convert_to_notes(FILE, 1)
notes += midi.convert_to_notes(FILE, 2)
tempo = midi.get_tempo(FILE)

tempo_div = tempo / 120 / 1e+6
print(tempo_div)
for note in notes:
    duration = note.duration * tempo_div
    start = note.start * tempo_div
    if int(SAMPLE_RATE * start) >= int(SAMPLE_RATE * DURATION) or (int(SAMPLE_RATE * (start + duration)) >= int(SAMPLE_RATE * DURATION)):
        continue
    freq = pow(2, (note.pitch - 69) / 24) * 440
    sample = generate_square(note.velocity / 240, SAMPLE_RATE, duration, freq)
    add_sample(samples, SAMPLE_RATE, start, sample)
    print(f"added sample at {start} for {duration} freq {freq} ({midi.num_to_str(note.pitch)})")
# cs = generate_sine(0.1, SAMPLE_RATE, 2, 554.37)
# e = generate_sine(0.1, SAMPLE_RATE, 1, 659.25)
# aoct = generate_sine(0.1, SAMPLE_RATE, 1, 880.00)
# 
# add_samples(samples, SAMPLE_RATE, 1.0, cs)
# add_samples(samples, SAMPLE_RATE, 2.0, e)
# add_samples(samples, SAMPLE_RATE, 2.0, aoct)

# per @yahweh comment explicitly convert to bytes sequence
output_bytes = samples.tobytes()

# for paFloat32 sample values must be in range [-1.0, 1.0]
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                output=True)

# play. May repeat with different volume values (if done interactively)
start_time = time.time()
stream.write(output_bytes)
print("Played sound for {:.2f} seconds".format(time.time() - start_time))

stream.stop_stream()
stream.close()

p.terminate()