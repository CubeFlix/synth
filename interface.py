import tkinter
import tkinter.messagebox
from tkinter import ttk, filedialog
import rtmidi
import pyaudio
import numpy as np
import threading
from dataclasses import dataclass
import os
import wave
import tempfile
import shutil

SAMPLE_RATE = 44100
TIMEOUT = 30
ICON = 'synth.ico'
import sys
if getattr(sys, 'frozen', False):
    ICON = os.path.join(sys._MEIPASS, ICON)

@dataclass
class Note:
    pitch: int
    velocity: int
    is_new: bool
    should_remove: bool

def calculate_pitch_et(pitch, et):
    return pow(2, (pitch - 69) / et) * 440

class SynthInterface:
    def __init__(self, title="KSYNTH"):
        self.title = title
        self.running = False
        self.record = None

        # Settings.
        self.port = None
        self.volume = 100
        self.hertz = 0
        self.et = 12
        self.should_attack_decay_smoothing = True

    def get_midi_inputs(self):
        return [self.midi.getPortName(i) for i in range(self.midi.getPortCount())]

    def init(self):
        self.midi = rtmidi.RtMidiIn()
        self.root = tkinter.Tk()
        self.root.title(self.title)
        self.root.resizable(False, False)
        self.root.iconbitmap(ICON)
        def on_close_window():
            self.stop_synth()
            self.stop_record()
            self.root.destroy()
            os._exit(0)
        self.root.protocol("WM_DELETE_WINDOW", on_close_window)

        self.menubar = tkinter.Menu(self.root)
        self.menubar.add_command(label='Info', command=self.show_info_window)
        self.root.config(menu=self.menubar)

        self.frame_left = tkinter.Frame(self.root)
        self.frame_center = tkinter.Frame(self.root)
        self.frame_right = tkinter.Frame(self.root)
        self.frame_debug = tkinter.Frame(self.root)

        self.midi_inputs_listbox_label = tkinter.Label(self.frame_left, text="Select a MIDI input:")
        self.midi_inputs_listbox_label.pack()
        self.midi_inputs_listbox = tkinter.Listbox(self.frame_left)
        self.midi_inputs_listbox.pack()
        self.midi_inputs_select_button = ttk.Button(self.frame_left, text="Select", command=self.select_midi_input)
        self.midi_inputs_select_button.pack()
        self.midi_inputs_update_button = ttk.Button(self.frame_left, text="Update", command=self.update_midi_inputs)
        self.midi_inputs_update_button.pack()
        self.midi_status_label_var = tkinter.StringVar(self.root, "No MIDI input selected.")
        self.midi_status_label = tkinter.Label(self.frame_left, textvariable=self.midi_status_label_var)
        self.midi_status_label.pack()

        self.tuning_label_var = tkinter.StringVar(self.root, "Tuning system: 12-et")
        self.tuning_label = tkinter.Label(self.frame_center, textvariable=self.tuning_label_var)
        self.tuning_label.pack()
        self.tuning_slider = tkinter.Scale(self.frame_center, from_=1, to_=64, orient=tkinter.HORIZONTAL, command=self.update_et)
        self.tuning_slider.pack()
        self.tuning_slider.set(12)
        self.hertz_label_var = tkinter.StringVar(self.root, "Re-tune: 0hz")
        self.hertz_label = tkinter.Label(self.frame_center, textvariable=self.hertz_label_var)
        self.hertz_label.pack()
        self.hertz_slider = tkinter.Scale(self.frame_center, from_=-100, to_=100, orient=tkinter.HORIZONTAL, command=self.update_hertz)
        self.hertz_slider.pack()
        self.hertz_slider.set(0)
        self.volume_label_var = tkinter.StringVar(self.root, "Volume: 100%")
        self.volume_label = tkinter.Label(self.frame_center, textvariable=self.volume_label_var)
        self.volume_label.pack()
        self.volume_slider = tkinter.Scale(self.frame_center, from_=0, to_=100, orient=tkinter.HORIZONTAL, command=self.update_volume)
        self.volume_slider.pack()
        self.volume_slider.set(100)
        
        self.should_attack_decay_smoothing_checkbox = ttk.Checkbutton(self.frame_right, text="Apply attack/decay smoothing", onvalue=True, offvalue=False, command=self.update_should_attack_decay_smoothing)
        self.should_attack_decay_smoothing_checkbox.pack()
        self.should_attack_decay_smoothing_checkbox.state(['selected'])
        self.wave_type_label = tkinter.Label(self.frame_right, text="Wave type:")
        self.wave_type_label.pack()
        self.wave_type = tkinter.StringVar(self.root)
        self.wave_type_sine_radiobutton = ttk.Radiobutton(self.frame_right, text="Sine wave", variable=self.wave_type, value="sine")
        self.wave_type_sine_radiobutton.pack()
        self.wave_type_square_radiobutton = ttk.Radiobutton(self.frame_right, text="Square wave", variable=self.wave_type, value="square")
        self.wave_type_square_radiobutton.pack()
        self.wave_type.set("sine")
        self.wave_type_sine_radiobutton.invoke()
        self.reset_settings_button = ttk.Button(self.frame_right, text="Reset Settings", command=self.reset_settings)
        self.reset_settings_button.pack()
        self.start_synth_button = ttk.Button(self.frame_right, text="Start Synth", command=self.start_synth)
        self.start_synth_button.pack()
        self.stop_synth_button = ttk.Button(self.frame_right, text="Stop Synth", command=self.stop_synth)
        self.stop_synth_button.pack()
        self.stop_synth_button.state(['disabled'])
        self.synth_status_label_var = tkinter.StringVar(self.root, "Synth stopped.")
        self.synth_status_label = tkinter.Label(self.frame_right, textvariable=self.synth_status_label_var)
        self.synth_status_label.pack()
        self.start_record_button = ttk.Button(self.frame_right, text="Record", command=self.start_record)
        self.start_record_button.pack()
        self.stop_record_button = ttk.Button(self.frame_right, text="Stop", command=self.stop_record)
        self.stop_record_button.pack()
        self.stop_record_button.state(['disabled'])
        self.record_status_label_var = tkinter.StringVar(self.root, "Not recording.")
        self.record_status_label = tkinter.Label(self.frame_right, textvariable=self.record_status_label_var)
        self.record_status_label.pack()
        
        self.synth_debug_label_var_1 = tkinter.StringVar(self.root, f"Sample rate: {SAMPLE_RATE}")
        self.synth_debug_label_1 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_1)
        self.synth_debug_label_1.pack()
        self.synth_debug_label_var_2 = tkinter.StringVar(self.root, f"Timeout duration: {TIMEOUT}")
        self.synth_debug_label_2 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_2)
        self.synth_debug_label_2.pack()
        self.synth_debug_label_var_3 = tkinter.StringVar(self.root, "Num notes: [synth inactive]")
        self.synth_debug_label_3 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_3)
        self.synth_debug_label_3.pack()
        self.synth_debug_label_var_4 = tkinter.StringVar(self.root, "Num frames: [synth inactive]")
        self.synth_debug_label_4 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_4)
        self.synth_debug_label_4.pack()
        self.synth_debug_label_var_5 = tkinter.StringVar(self.root, f"Output format: 32-bit float")
        self.synth_debug_label_5 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_5)
        self.synth_debug_label_5.pack()
        self.synth_debug_label_var_5 = tkinter.StringVar(self.root, f"Record format: 32-bit int")
        self.synth_debug_label_5 = tkinter.Label(self.frame_debug, textvariable=self.synth_debug_label_var_5)
        self.synth_debug_label_5.pack()

        self.frame_left.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)
        self.frame_center.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)
        self.frame_right.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)
        self.frame_debug.pack(expand=True, fill=tkinter.BOTH, side=tkinter.LEFT)

        self.update_midi_inputs()
    
    def run(self):
        self.root.mainloop()

    def show_info_window(self):
        self.info_window = tkinter.Tk()
        self.info_window.title(self.title)
        self.info_window.resizable(False, False)
        self.info_window.iconbitmap(ICON)
        def callback(url):
            import webbrowser
            webbrowser.open_new_tab(url)
        info_window_label_1 = tkinter.Label(self.info_window, text="KSYNTH - A simple sine/square MIDI synthesizer with alternate tuning systems.")
        info_window_label_1.pack()
        info_window_label_2 = tkinter.Label(self.info_window, text="Built by Kevin Chen (cubeflix) with Python.")
        info_window_label_2.pack()
        info_window_label_3 = tkinter.Label(self.info_window, text="https://github.com/cubeflix", fg="blue", cursor="hand2")
        info_window_label_3.pack()
        info_window_label_3.bind("<Button-1>", lambda _: callback("https://github.com/cubeflix"))
        info_window_label_4 = tkinter.Label(self.info_window, text="kevin.signal@gmail.com", fg="blue", cursor="hand2")
        info_window_label_4.pack()
        info_window_label_4.bind("<Button-1>", lambda _: callback("mailto:kevin.signal@gmail.com"))    
    
    def update_volume(self, _):
        self.volume = self.volume_slider.get()
        self.volume_label_var.set(f"Volume: {self.volume}%")

    def update_et(self, _):
        self.et = self.tuning_slider.get()
        self.tuning_label_var.set(f"Tuning system: {self.et}-et")
    
    def update_hertz(self, _):
        self.hertz = self.hertz_slider.get()
        self.hertz_label_var.set(f"Re-tune: {self.hertz}hz")

    def update_should_attack_decay_smoothing(self):
        self.should_attack_decay_smoothing = 'selected' in self.should_attack_decay_smoothing_checkbox.state()
    
    def reset_settings(self):
        self.volume_slider.set(100)
        self.update_volume(None)
        self.tuning_slider.set(12)
        self.update_et(None)
        self.hertz_slider.set(0)
        self.update_hertz(None)
        self.should_attack_decay_smoothing_checkbox.state(['selected'])
        self.update_should_attack_decay_smoothing()

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
        self.decay_smoothing = (TIMEOUT / 1000 - self.base / SAMPLE_RATE) / (TIMEOUT / 1000)

        self.running = True
        
        # Start the sound generation loop.
        self.synth_status_label_var.set("Starting sound play thread...")
        threading.Thread(target=lambda: self.sound_play_thread()).start()

        # Start the MIDI loop.
        self.synth_status_label_var.set("Starting MIDI input thread...")
        threading.Thread(target=lambda: self.midi_input_thread()).start()

        self.synth_status_label_var.set("Synth started.")
        self.synth_debug_label_var_3.set(f"Num notes: {len(self.current_notes)}")
        self.synth_debug_label_var_4.set(f"Num frames: {self.num_frames_count}")
        self.start_synth_button.state(['disabled'])
        self.stop_synth_button['state'] = tkinter.NORMAL

    def sound_play_thread(self):
        self.sound_thread_running = True
        while self.running:
            # Zero the buffer and calculate the sounds.
            self.buffer -= self.buffer
            for note in self.current_notes[:]:
                pitch = self.calculate_pitch(note.pitch, self.et) + self.hertz
                sound = np.sin(2 * np.pi * (self.base + self.num_frames_count * int(SAMPLE_RATE * TIMEOUT / 1000)) * pitch / SAMPLE_RATE)
                if self.wave_type.get() == 'square':
                    sound = np.sign(sound)
                sound = note.velocity / 400 * sound * (self.volume / 100)
                if note.is_new:
                    # Apply attack smoothing.
                    if self.should_attack_decay_smoothing:
                        sound *= self.attack_smoothing
                    note.is_new = False
                if note.should_remove:
                    # Apply decay smoothing and delete the note.
                    if self.should_attack_decay_smoothing:
                        sound *= self.decay_smoothing
                    del self.current_notes[self.find_note_by_number(note.pitch)]
                self.buffer += sound

            self.num_frames_count += 1
            if len(self.current_notes) == 0:
                self.num_frames_count = 0

            # Write the sound to the output buffer.
            data = self.buffer.astype(np.float32).tobytes()
            self.stream.write(data)
            if self.record:
                self.record.writeframes((self.buffer / 1.414 * 2147483647).astype(np.int32).tobytes())
            
            self.synth_debug_label_var_3.set(f"Num notes: {len(self.current_notes)}")
            self.synth_debug_label_var_4.set(f"Num frames: {self.num_frames_count}")
        
        self.synth_debug_label_var_3.set("Num notes: [synth inactive]")
        self.synth_debug_label_var_4.set("Num frames: [synth inactive]")

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
        self.start_synth_button['state'] = tkinter.NORMAL
        self.stop_synth_button.state(['disabled'])

    def start_record(self):
        if not self.running:
            tkinter.messagebox.showerror(self.title, "Please start the synth to record.")
            return
        
        file = tempfile.NamedTemporaryFile('wb', delete=False)
        wf = wave.open(file, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt32))
        wf.setframerate(SAMPLE_RATE)
        self.record = wf
        self.record_file = file
        
        self.record_status_label_var.set("Recording...")
        self.start_record_button.state(['disabled'])
        self.stop_record_button['state'] = tkinter.NORMAL

    def stop_record(self):
        if not self.record:
            return
        
        wf = self.record
        self.record = None
        wf.close()
        self.record_file.close()

        self.record_status_label_var.set("Not recording.")
        self.stop_record_button.state(['disabled'])
        self.start_record_button['state'] = tkinter.NORMAL

        filetypes = (('Waveform Audio File', '*.wav'), ('All Files', '*.*'))
        file = filedialog.asksaveasfilename(confirmoverwrite=True, filetypes=filetypes, defaultextension='wav')
        if not file:
            return
        shutil.copyfile(self.record_file.name, file)
        os.remove(self.record_file.name)

if __name__ == '__main__':
    s = SynthInterface()
    s.init()
    s.run()