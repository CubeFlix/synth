# Simple pygame program

import numpy as np
from numpy.fft import fft, fftfreq
from scipy.io import wavfile

# Import and initialize the pygame library
import pygame
pygame.init()
DIMENSIONS = [800, 500]

# Set up the drawing window
screen = pygame.display.set_mode(DIMENSIONS)

selection_a = None
selection_b = None
selection_state = 0 # 0 means no selection, 1 means one point, 2 means both selected

def calc_rect_from_points(a, b):
    if a[0] > b[0]:
        left = b[0]
        width = a[0] - b[0]
    else:
        left = a[0]
        width = b[0] - a[0]

    if a[1] > b[1]:
        top = b[1]
        height = a[1] - b[1]
    else:
        top = a[1]
        height = b[1] - a[1]

    return pygame.rect.Rect(left, top, width, height)

zoom = 1
offset = (0, 0)

def calc_data():
    rate, samples = wavfile.read("rec1.wav")
    total_samples = len(samples)

    fft_width = 1000
    image = np.zeros((int(total_samples / fft_width), int(fft_width/2))) # we divide width by 2 since fft gives a mirrored image
    for current_stride in range(int(total_samples / fft_width)):
        fft_out = np.abs(fft(samples[current_stride * fft_width : current_stride * fft_width + fft_width]))
        image[current_stride] = fft_out[int(fft_width/2):]

    freqs = fftfreq(fft_width, 1./rate)
    return (image, freqs)

data, freq_map = calc_data()

# Cut the data
max_val = max(data.flatten())

data = (data.T[len(data[0])//12 * 11:]).T

print(data.shape)

image = pygame.surfarray.pixels3d(screen)

def render():
    # max_val = 1e+9
    for i in range(DIMENSIONS[0]):
        for j in range(DIMENSIONS[1]):
            ind_y = int(j / DIMENSIONS[1] * len(data[0]))
            ind_x = int(i / DIMENSIONS[0] * len(data))
            val = data[ind_x][ind_y]
            col = int(val / max_val * 256)
            if col > 255:
                col = 255
            image[i][j] = [0, col, col]

render()

# Run until the user asks to quit
running = True
while running:

    # Did the user click the window close button?
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            selection_a = event.pos
            selection_state = 1
        if event.type == pygame.MOUSEBUTTONUP:
            selection_b = event.pos
            selection_state = 2

    


    # Fill the background with white

    # render(screen)
    

    # Draw selection box
    if selection_state == 1:
        (mx, my) = pygame.mouse.get_pos()
        pygame.draw.rect(screen, (255, 255, 255), calc_rect_from_points((mx, my), selection_a))
    if selection_state == 2:
        pygame.draw.rect(screen, (255, 255, 255), calc_rect_from_points(selection_a, selection_b))

    # Flip the display
    pygame.display.flip()

# Done! Time to quit.
pygame.quit()