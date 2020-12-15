import PySimpleGUI as sg
import speech_recognition as sr 
import os 
from pydub import AudioSegment
from pydub.silence import split_on_silence
from pydub.playback import play
from argparse import ArgumentParser
import os.path
from threading import Thread
import threading

import pathlib as pl

file_list_column = [
    [
        sg.Text("Audio File"),
        sg.In(size=(25, 1), enable_events=True, key="-SOURCE-"),
        sg.FileBrowse(),
    ],
    [
        sg.Text("Chunk Folder"),
        sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"),
        sg.FolderBrowse(),
    ],
    [
        sg.Listbox(
            values=[], enable_events=True, size=(40, 20), key="-FILE LIST-"
        )
    ],
]

image_viewer_column = [
    [sg.Multiline(size=(50, 10), key='-TSOLUTION-')],
]

layout = [
    [
        sg.Column(file_list_column),
        sg.VSeperator(),
        sg.Column(image_viewer_column),
    ]
]

r = sr.Recognizer()

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        print(type(self._target))
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return


def split_in_chunks(path, folder_name):
    """
    Splitting the large audio file into chunks
    """
    # open the audio file using pydub
    sound = AudioSegment.from_wav(path)  
    chunks = split_on_silence(sound,
        min_silence_len=500,
        silence_thresh=sound.dBFS-14,
        keep_silence=True,
    )
    # create a directory to store the audio chunks
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    
    start = 0
    # process each chunk 
    for i, audio_chunk in enumerate(chunks, start=1):
        start_in_ms = start
        second_in_ms = 1000
        minute_in_ms = 60 * second_in_ms
        hour_in_ms = 60 * minute_in_ms
        h = str(int(start_in_ms / hour_in_ms)).zfill(2)
        start_in_ms = start_in_ms % hour_in_ms
        m = str(int(start_in_ms / minute_in_ms)).zfill(2)
        start_in_ms = start_in_ms % minute_in_ms
        s = str(int(start_in_ms / second_in_ms)).zfill(2)
        start_in_ms = start_in_ms % second_in_ms
        ms = str(start_in_ms).zfill(3)

        chunk_filename = os.path.join(folder_name, f"chunk_{h}-{m}-{s}-{ms}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        start += len(audio_chunk)


def transcribe_chunk(filename):
    with sr.AudioFile(filename) as source:
        audio_listened = r.record(source)
        # try converting it to text
        try:
            text = r.recognize_google(audio_listened, language="sv_SV")
        except sr.UnknownValueError as e:
            return "Error"
        else:
            text = f"{text.capitalize()}. "
            return text


if __name__ == "__main__":
    window = sg.Window("Transcription Tool", layout)

    source_file = pl.Path()
    folder = ""
    player = Thread()
    transcriber = Thread()

    while True:
        event, values = window.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        #  Folder name was filled in, make a list of files in the folder

        if event == "-SOURCE-":
            folder = "audio-chunks"
            source_file = pl.Path(values["-SOURCE-"])
            split_in_chunks(source_file, folder)
            try:
                # Get list of files in folder
                file_list = os.listdir(folder)
                file_list.sort()
            except:
                file_list = []

            fnames = [
                f
                for f in file_list
                if os.path.isfile(os.path.join(folder, f))
                and f.lower().endswith((".wav"))
            ]
            window["-FILE LIST-"].update(fnames)
    
        if event == "-FOLDER-":
            folder = values["-FOLDER-"]
            try:
                # Get list of files in folder
                file_list = os.listdir(folder)
                file_list.sort()
            except:
                file_list = []

            fnames = [
                f
                for f in file_list
                if os.path.isfile(os.path.join(folder, f))
                and f.lower().endswith((".wav"))
            ]
            window["-FILE LIST-"].update(fnames)

        elif event == "-FILE LIST-":  # A file was chosen from the listbox
            if not (player.is_alive() or transcriber.is_alive()):
                try:
                    filename = os.path.join(folder, values["-FILE LIST-"][0])
                    sound = AudioSegment.from_wav(filename)
                    if len(sound)/1000 > 20:
                        window["-TSOLUTION-"].update("File too long")
                    else:
                        player = Thread(target=play, args=(sound,))
                        player.start()
                        # play(sound)
                        transcriber = ThreadWithReturnValue(target=transcribe_chunk, args=(filename,))
                        transcriber.start()
                        # text = transcribe_chunk(filename)
                        text = transcriber.join()
                        window["-TSOLUTION-"].update(text)
                except:
                    pass

    window.close()
