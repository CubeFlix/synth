import numpy as np
from numpy.fft import fft, fftfreq
import matplotlib.pyplot as plt
from scipy.io import wavfile

rate, samples = wavfile.read("test.wav")
total_samples = len(samples)

NOTES = [pow(2, (i - 69) / 12) * 440 for i in range(300)]
THRESHOLD = 5e+7

# rate = 44100
# duration = 50
# time = np.arange(0, rate * duration) / rate
# samples_a = np.sin(2 * np.pi * 440 * time)
# samples_b = np.sin(2 * np.pi * 880 * time)
# samples = samples_a + samples_b

# def fft_over_time():
#     fft_width = 441
#     image = np.zeros((int(rate * duration / fft_width), fft_width))
# 
#     # image properties: fft width of 100, frequency range of 0-100 (fft output divided by 10)
#     for current_stride in range(int(rate * duration / fft_width)):
#         fft_out = np.abs(fft(samples[current_stride * fft_width : current_stride * fft_width + fft_width]))
#         image[current_stride] = (fft_out)
# 
#     print(fft_out)
# 
#     plt.imshow(image.T)
#     plt.show()

def get_notes_on_frame(frame_fft, freq_index_to_note):
    notes = []
    for i, v in enumerate(frame_fft):
        if (v - 5e-7) < THRESHOLD:
            continue
        print(v)
        if freq_index_to_note[i] not in notes:
            notes.append(freq_index_to_note[i])

    return notes        

def calculate_freq_index_to_note(freqs):
    freq_index_to_note = []
    for freq in freqs:
        best_note = None
        best_dist = None
        for note, note_freq in enumerate(NOTES):
            dist = abs(note_freq - freq)
            if best_dist == None:
                best_note = note
                best_dist = dist
                continue
            if dist < best_dist:
                best_dist = dist
                best_note = note
        
        freq_index_to_note.append(best_note)

    return freq_index_to_note

def fft_over_time():
    fft_width = 44100//10
    image = np.zeros((int(total_samples / fft_width), int(fft_width/2))) # we divide width by 2 since fft gives a mirrored image
    for current_stride in range(int(total_samples / fft_width)):
        fft_out = np.abs(fft(samples[current_stride * fft_width : current_stride * fft_width + fft_width]))
        image[current_stride] = fft_out[int(fft_width/2):]

    freqs = fftfreq(fft_width, 1./rate)
    plt.imshow(image.T, extent=[0, total_samples / rate, freqs[0], freqs[int(fft_width/2)-1]], aspect=.001)
    plt.show()
    print("a")
    freq_index_to_note = calculate_freq_index_to_note(freqs)
    for frame in image:
        # cut off the high freqs and process
        print(get_notes_on_frame(frame[:len(frame) // 4], freq_index_to_note))

def fft_freqs():
    Y = abs(fft(samples))
    X = fftfreq(len(Y), d=1./rate)
    plt.plot(X, Y)
    plt.show()

fft_over_time()