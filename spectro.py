import numpy as np
from numpy.fft import fft, fftfreq
from scipy.io import wavfile
import pygame

class Spectrogram:
    def __init__(self, file):
        self.file = file
        self.zoom_x = 1
        self.zoom_y = 5
        self.offset_x = 0
        self.offset_y = 0
        self.fft_width = 1024
        self.rate, self.samples = wavfile.read(file)
        self.total_samples = len(self.samples)

        pygame.init()
        pygame.display.set_caption("Spectrogram")
        self.dims = [800, 500]
        self.screen = pygame.display.set_mode(self.dims)
        self.image = pygame.surfarray.pixels3d(self.screen)

        self.calc_fft()
        self.render()

        self.running = False

    def calc_fft(self):
        self.data = np.zeros((int(self.total_samples / self.fft_width), int(self.fft_width/2))) # we divide width by 2 since fft gives a mirrored image
        for current_stride in range(int(self.total_samples / self.fft_width)):
            fft_out = np.abs(fft(self.samples[current_stride * self.fft_width : current_stride * self.fft_width + self.fft_width]))
            self.data[current_stride] = fft_out[int(self.fft_width/2):]
        self.freqs = fftfreq(self.fft_width, 1./self.rate)

        self.max_val = max(self.data.flatten())
        self.data = np.flip(self.data, 1)

        # Convert the data into color values.
        for i in range(len(self.data)):
            for j in range(len(self.data[0])):
                self.data[i][j] = int(self.data[i][j] / self.max_val * 256)
                if self.data[i][j] > 255:
                    self.data[i][j] = 255

    def render(self):
        self.screen.fill((0, 0, 0))
        scaling_factor_y = 1. / self.dims[1] * len(self.data[0])
        scaling_factor_x = 1. / self.dims[0] * len(self.data)
        for i in range(self.dims[0]):
            for j in range(self.dims[1]):
                ind_y = int((j / self.zoom_y + self.offset_y) * scaling_factor_y)
                ind_x = int((i / self.zoom_x + self.offset_x) * scaling_factor_x)
                if ind_y >= len(self.data[0]):
                    continue
                if ind_x >= len(self.data):
                    return
                val = self.data[ind_x][ind_y]
                self.image[i][self.dims[1] - j - 1] = [0, val, val]

    def run(self):
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEWHEEL:
                    if pygame.key.get_pressed()[pygame.K_LCTRL]:
                        if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                            self.zoom_y += event.y / 3
                            if self.zoom_y <= 0.1:
                                self.zoom_y = 0.1
                            self.render()
                        else:
                            self.zoom_x += event.y / 50
                            if self.zoom_x <= 0.1:
                                self.zoom_x = 0.1
                            self.render()
                    else:
                        if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                            self.offset_y += event.y * 2
                            if self.offset_y < 0:
                                self.offset_y = 0
                            self.render()
                        else:
                            self.offset_x += event.y * 2
                            if self.offset_x < 0:
                                self.offset_x = 0
                            self.render()

            pygame.display.flip()

if __name__ == '__main__':
    app = Spectrogram("Recording (2).wav")
    app.run()