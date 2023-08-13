from mido import MidiFile

# 

def num_to_str(pitch):
    notes = [["C"],["C#","Db"],["D"],["D#","Eb"],["E"],["F"],["F#","Gb"],["G"],["G#","Ab"],["A"],["A#","Bb"],["B"]]
    return notes[(pitch) % 12][0]

class Note:
    def __init__(self, pitch: int, velocity: int, duration: float, start: float):
        self.pitch = pitch
        self.velocity = velocity
        self.duration = duration
        self.start = start

    def __repr__(self):
        return f'note: {self.pitch} ({num_to_str(self.pitch)}) {self.velocity} d:{self.duration} s:{self.start}'
    
    def __str__(self):
        return self.__repr__()

def convert_to_notes(midi_file: str, track: int) -> tuple:
    f = MidiFile(midi_file)
    t = f.tracks[track]

    notes = []
    current_time = 0
    current_notes = []

    print(t[:10])

    for message in t:
        if message.type != 'note_on' and message.type != 'note_off':
            continue

        current_time += message.time

        if message.type == 'note_on':
            current_notes.append(Note(message.note, message.velocity, None, current_time)) # we wait till the note ends to put in the duration
        if message.type == 'note_off':
            # search for the note in the currently playing notes
            for i, note in enumerate(current_notes):
                if note.pitch == message.note:
                    # we found the correct note
                    current_notes[i].duration = current_time - note.start
                    notes.append(current_notes[i])
                    del current_notes[i]
                    break

    return notes

def get_tempo(midi_file: str) -> int:
    f = MidiFile(midi_file)
    t = f.tracks[0]

    for message in t:
        if message.type == 'set_tempo':
            return message.tempo
        
    return 500000