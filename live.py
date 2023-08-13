import rtmidi
import sys
import pyaudio
import numpy as np
import threading
from dataclasses import dataclass

SAMPLE_RATE = 44100
PORT = 0
TIMEOUT = 100

print("-- hello tim this is kevins little synthesizer --")

@dataclass
class Note:
    pitch: int
    velocity: int

print("initializing audio...")
audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                output=True)

print("initializing midi...")
midi = rtmidi.RtMidiIn()
if not midi.getPortCount():
    print("no midi inputs detected, exiting")
    sys.exit()

print(f"you have {midi.getPortCount()} ports connected to your computer!")
for i in range(midi.getPortCount()):
    print(f"[{i}]: {midi.getPortName(i)}")
selected_port = ''
while not selected_port.isnumeric():
    selected_port = input("please select a device! input the number of the device you want to use above: ")

PORT = int(selected_port)

print(f"opening midi port {PORT}: {midi.getPortName(PORT)}...")
midi.openPort(PORT)

num_frames_count = 0

current_notes = []
base = np.arange(int(SAMPLE_RATE * TIMEOUT / 1000))
buffer = np.zeros(int(SAMPLE_RATE * TIMEOUT / 1000))

def calculate_pitch_12et(pitch):
    return pow(2, (pitch - 69) / 12) * 440
def calculate_pitch_24et(pitch):
    return pow(2, (pitch - 69) / 24) * 440

calculate_pitch = calculate_pitch_24et

def sound_play_thread():
    global current_notes, stream, buffer, num_frames_count

    try:
        while True:
            buffer -= buffer
            for note in current_notes:
                pitch = calculate_pitch(note.pitch)
                buffer += note.velocity / 1000 * (np.sin(2 * np.pi * (base + num_frames_count * int(SAMPLE_RATE * TIMEOUT / 1000)) * pitch / SAMPLE_RATE))
            num_frames_count += 1
            # play the sounds
            stream.write(buffer.astype(np.float32).tobytes())

    except KeyboardInterrupt:
        print("ctrl-c, exiting")

print("initializing sound play thread...")
threading.Thread(target=sound_play_thread).start()

def find_note_by_number(num):
    global current_notes
    for i, note in enumerate(current_notes):
        if note.pitch == num:
            return i

print("initializing midi input thread...")
try:
    print("ready!! (press ctrl-c or close the window to exit)")
    while True:
        message = midi.getMessage(0)
        if not message:
            continue

        # process the message
        if message.isNoteOn():
            note = Note(message.getNoteNumber(), message.getVelocity())
            current_notes.append(note)
        elif message.isNoteOff():
            del current_notes[find_note_by_number(message.getNoteNumber())]
        if len(current_notes) == 0:
            num_frames_count = 0

except KeyboardInterrupt:
    print("ctrl-c, exiting")

stream.stop_stream()
stream.close()
audio.terminate()
