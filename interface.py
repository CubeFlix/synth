import tkinter
import tkinter.messagebox
import rtmidi
import pyaudio
import numpy as np
import threading
from dataclasses import dataclass
import math

SAMPLE_RATE = 44100
TIMEOUT = 30

@dataclass
class Note:
    pitch: int
    velocity: int
    is_new: bool
    should_remove: bool

def calculate_pitch_et(pitch, et):
    return pow(2, (pitch - 69) / et) * 440

class SynthInterface:
    def __init__(self, title="Kevin's Synth"):
        self.title = title
        self.port = None
        self.volume = 100
        self.hertz = 0
        self.et = 12
        self.running = False

    def get_midi_inputs(self):
        return [self.midi.getPortName(i) for i in range(self.midi.getPortCount())]

    def init(self):
        self.midi = rtmidi.RtMidiIn()
        self.root = tkinter.Tk()
        self.root.title(self.title)
        self.root.resizable(False, False)

        self.frame_left = tkinter.Frame(self.root)
        self.frame_right = tkinter.Frame(self.root)

        self.midi_inputs_listbox_label = tkinter.Label(self.frame_left, text="Select a MIDI input:")
        self.midi_inputs_listbox_label.pack()
        self.midi_inputs_listbox = tkinter.Listbox(self.frame_left)
        self.midi_inputs_listbox.pack()
        self.midi_inputs_select_button = tkinter.Button(self.frame_left, text="Select", command=self.select_midi_input)
        self.midi_inputs_select_button.pack()
        self.midi_inputs_update_button = tkinter.Button(self.frame_left, text="Update", command=self.update_midi_inputs)
        self.midi_inputs_update_button.pack()
        self.midi_status_label_var = tkinter.StringVar(self.root, "No MIDI input selected.")
        self.midi_status_label = tkinter.Label(self.frame_left, textvariable=self.midi_status_label_var)
        self.midi_status_label.pack()

        self.volume_label_var = tkinter.StringVar(self.root, "Volume: 100%")
        self.volume_label = tkinter.Label(self.frame_right, textvariable=self.volume_label_var)
        self.volume_label.pack()
        self.volume_slider = tkinter.Scale(self.frame_right, from_=0, to_=100, orient=tkinter.HORIZONTAL, command=self.update_volume)
        self.volume_slider.pack()
        self.volume_slider.set(100)
        self.tuning_label_var = tkinter.StringVar(self.root, "Tuning system: 12-et")
        self.tuning_label = tkinter.Label(self.frame_right, textvariable=self.tuning_label_var)
        self.tuning_label.pack()
        self.tuning_slider = tkinter.Scale(self.frame_right, from_=1, to_=64, orient=tkinter.HORIZONTAL, command=self.update_et)
        self.tuning_slider.pack()
        self.tuning_slider.set(12)
        self.hertz_label_var = tkinter.StringVar(self.root, "Re-tune: 0hz")
        self.hertz_label = tkinter.Label(self.frame_right, textvariable=self.hertz_label_var)
        self.hertz_label.pack()
        self.hertz_slider = tkinter.Scale(self.frame_right, from_=-100, to_=100, orient=tkinter.HORIZONTAL, command=self.update_hertz)
        self.hertz_slider.pack()
        self.hertz_slider.set(0)
        self.reset_settings_button = tkinter.Button(self.frame_right, text="Reset Settings", command=self.reset_settings)
        self.reset_settings_button.pack()
        self.start_synth_button = tkinter.Button(self.frame_right, text="Start Synth", command=self.start_synth)
        self.start_synth_button.pack()
        self.stop_synth_button = tkinter.Button(self.frame_right, text="Stop Synth", command=self.stop_synth)
        self.stop_synth_button.pack()
        self.synth_status_label_var = tkinter.StringVar(self.root, "Synth stopped.")
        self.synth_status_label = tkinter.Label(self.frame_right, textvariable=self.synth_status_label_var)
        self.synth_status_label.pack()

        self.frame_left.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)
        self.frame_right.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)

        self.update_midi_inputs()
    
    def run(self):
        self.root.mainloop()
        self.stop_synth()

    def update_volume(self, _):
        self.volume = self.volume_slider.get()
        self.volume_label_var.set(f"Volume: {self.volume}%")

    def update_et(self, _):
        self.et = self.tuning_slider.get()
        self.tuning_label_var.set(f"Tuning system: {self.et}-et")
    
    def update_hertz(self, _):
        self.hertz = self.hertz_slider.get()
        self.hertz_label_var.set(f"Re-tune: {self.hertz}hz")
    
    def reset_settings(self):
        self.volume_slider.set(100)
        self.update_volume(None)
        self.tuning_slider.set(12)
        self.update_et(None)
        self.hertz_slider.set(0)
        self.update_hertz(None)

    def select_midi_input(self):
        selected = self.midi_inputs_listbox.curselection()
        if not selected:
            tkinter.messagebox.showerror(self.title, "Please select a MIDI input in the list above.")
            return
        self.port = selected[0]
        self.midi_status_label_var.set(f"Selected MIDI port: {self.port} ({self.midi_inputs_listbox.get(self.port)})")

    def update_midi_inputs(self):
        old_status = self.midi_status_label_var.get()
        self.midi_status_label_var.set("Updating MIDI inputs...")
        self.midi_inputs_listbox.delete(0, tkinter.END)
        for i, name in enumerate(self.get_midi_inputs()):
            self.midi_inputs_listbox.insert(i+1, name)
        self.midi_status_label_var.set(old_status)

    def start_synth(self):
        if self.port == None:
            tkinter.messagebox.showerror(self.title, "Please select a MIDI input first.")
            return
        
        # Init sound.
        self.synth_status_label_var.set("Initializing sound...")
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=SAMPLE_RATE,
                        output=True)
        
        # Init MIDI.
        self.synth_status_label_var.set("Initializing MIDI...")
        self.midi.openPort(self.port)

        # Init sound generation vars.
        self.synth_status_label_var.set("Initializing...")
        self.num_frames_count = 0
        self.current_notes = []
        self.base = np.arange(int(SAMPLE_RATE * TIMEOUT / 1000))
        self.buffer = np.zeros(int(SAMPLE_RATE * TIMEOUT / 1000))
        self.calculate_pitch = calculate_pitch_et
        self.attack_smoothing = self.base / len(self.base)
        self.decay_smoothing = (TIMEOUT / 1000 - self.base / (SAMPLE_RATE)) / (TIMEOUT / 1000)
        
        self.running = True
        
        # Start the sound generation loop.
        self.synth_status_label_var.set("Starting sound play thread...")
        threading.Thread(target=lambda: self.sound_play_thread()).start()

        # Start the MIDI loop.
        self.synth_status_label_var.set("Starting MIDI input thread...")
        threading.Thread(target=lambda: self.midi_input_thread()).start()

        self.synth_status_label_var.set("Synth started.")

    def sound_play_thread(self):
        while self.running:
            # Zero the buffer and calculate the sounds.
            self.buffer -= self.buffer
            for note in self.current_notes[:]:
                pitch = self.calculate_pitch(note.pitch, self.et) + self.hertz
                sound = note.velocity / 400 * (np.sin(2 * np.pi * (self.base + self.num_frames_count * int(SAMPLE_RATE * TIMEOUT / 1000)) * pitch / SAMPLE_RATE)) * (self.volume / 100)
                if note.is_new:
                    # Apply attack smoothing.
                    sound *= self.attack_smoothing
                    note.is_new = False
                if note.should_remove:
                    # Apply decay smoothing and delete the note.
                    # # We calculate the greatest number of cycles we can have so we end at a 0.
                    # max_samples_to_zero = math.floor(pitch * TIMEOUT/1000) / pitch * SAMPLE_RATE
                    # offset = (self.num_frames_count * int(SAMPLE_RATE * TIMEOUT / 1000)) % (int(1/pitch * SAMPLE_RATE))
                    # sound[int(max_samples_to_zero - offset):] = 0.0 
                    # print(sound[-100:])
                    sound *= self.decay_smoothing
                    del self.current_notes[self.find_note_by_number(note.pitch)]
                self.buffer += sound
            self.num_frames_count += 1

            # Write the sound to the output buffer.
            self.stream.write(self.buffer.astype(np.float32).tobytes())

    def find_note_by_number(self, num):
        for i, note in enumerate(self.current_notes):
            if note.pitch == num:
                return i

    def midi_input_thread(self):
        while self.running:
            message = self.midi.getMessage(0)
            if not message:
                continue

            # Process the message.
            if message.isNoteOn():
                note = Note(message.getNoteNumber(), message.getVelocity(), True, False)
                self.current_notes.append(note)
            elif message.isNoteOff():
                self.current_notes[self.find_note_by_number(message.getNoteNumber())].should_remove = True
            if len(self.current_notes) == 0:
                self.num_frames_count = 0

    def stop_synth(self):
        if self.running == False:
            return
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        self.midi.closePort()
        self.midi.cancelCallback()
        self.synth_status_label_var.set("Synth stopped.")

if __name__ == '__main__':
    s = SynthInterface()
    s.init()
    s.run()