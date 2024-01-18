import math
import os
import select
import subprocess
import argparse
import sys
from tempfile import TemporaryDirectory
from threading import Thread, Event
from typing import List
from pathlib import Path
from time import sleep
import requests
import unicodedata

SLEEP_INTERVAL = 0.1
SPEED_INCREMENT = 20
DEFAULT_SPEED_WPM = 200
TXT_CHUNK_SPLIT_CHAR = "."

def split_pdf_two_columns(pdf_path: Path, tmp_dir_path: Path) -> Path:
    """Use krop to split a PDF into two columns."""
    split_pdf_path = tmp_dir_path / "split_pdf.pdf"
    
    # Construct the krop command
    krop_command = [
        "krop",
        "--grid=2x1",
        str(pdf_path),
        "--go",
        "--output",
        str(split_pdf_path)
    ]

    # Run the krop command using subprocess.run
    subprocess.run(krop_command, check=True)

    return split_pdf_path

def fix_text_for_TTS(tmp_txt: Path) -> None:
    with open(tmp_txt, "r+") as txt_file:
        txt = txt_file.read()
        # Fixes ligatures like "ﬁ" which are not read properly by TTS
        fixed_txt = unicodedata.normalize("NFKD", txt)
        txt_file.seek(0)
        txt_file.write(fixed_txt)

def pdf_to_text(pdf_file: Path, first_page: int, tmp_dir: Path) -> Path:
    tmp_txt = tmp_dir / "pdf.txt"
    subprocess.run(["pdftotext", "-f", 
                    str(first_page), str(pdf_file), str(tmp_txt)], check=True)
    
    fix_text_for_TTS(tmp_txt)
    return tmp_txt

def txt_to_wav_espeak(txt_path: Path, speed: int) -> Path:
    tmp_wav = txt_path.with_suffix(".wav")
    subprocess.run(["espeak", 
                    "-f", str(txt_path), 
                    "-w", str(tmp_wav), 
                    "-s", str(speed),
                    "-v", "mb-en1"], # use mbrola voices
                    check=True)
    return tmp_wav


def wpm_speed_to_length_scale(wpm_speed: int) -> float:
    return DEFAULT_SPEED_WPM / wpm_speed

def txt_to_wav_mimic3(txt_path: Path, speed_wpm: int) -> Path:
    """Use mimic3 engine running through docker webserver.
    See for installation:
    https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#docker-image
    See for API docs:
    https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#web-server
    """
    tmp_wav = txt_path.with_suffix(f".s_{speed_wpm}.wav")
    if os.path.exists(tmp_wav):
        return tmp_wav

    text = ""
    with open(txt_path, "r") as txt_file:
        text = txt_file.read()

    url = "http://localhost:59125/api/tts"
    params = {
        'text': text,
        'voice': 'en_UK/apope_low',
        'noiseScale': 0.667,
        'noiseW': 0.8,
        'lengthScale': wpm_speed_to_length_scale(speed_wpm),
        'ssml': False,
        'audioTarget': 'client'
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        with open(tmp_wav, 'wb') as f:
            f.write(response.content)
        # print(f"Audio file saved to {tmp_wav}")
    else:
        print(f"Mimic3 TTS request failed: {response}")
    return tmp_wav


def play_wav(wav_path: Path, stop_playing: Event) -> Thread:
    def play():
        proc = None
        with open(os.devnull, "w") as null_file:
            proc = subprocess.Popen(["aplay", str(wav_path)], stdout=null_file, stderr=null_file)
        while not stop_playing.is_set() and proc.poll() is None:
            sleep(SLEEP_INTERVAL)
        proc.terminate()
        assert stop_playing.is_set() or proc.returncode == 0

    thread = Thread(target=play)
    thread.start()
    return thread

def text_cut_chunks(txt: str, chunk_size: int) -> List[str]:
    words = txt.split(TXT_CHUNK_SPLIT_CHAR)
    chunk_lists = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    return [TXT_CHUNK_SPLIT_CHAR.join(l) for l in chunk_lists]

def file_make_chunks(tmp_dir: Path, txt_path: Path, chunk_size: int) -> List[Path]:
    with open(txt_path, "r") as txt_file:
        txt_str = txt_file.read()
        chunks = text_cut_chunks(txt_str, chunk_size)
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            chunk_path = tmp_dir / f"chunk{i}.txt"
            chunk_paths.append(chunk_path)
            with open(chunk_path, "w+") as chunk_file:
                chunk_file.write(chunk)
                chunk_file.flush()
    return chunk_paths

def print_txt_file(path: Path):
    with open(path, "r") as file:
        print()
        txt = file.read().replace("\n", "\n\t")
        txt = f"\t{txt}"
        print(txt)
        print()

def get_cmd():
    read_ready, _, _ = select.select([sys.stdin], [], [], SLEEP_INTERVAL)
    if read_ready:
        return sys.stdin.readline().strip()
    else:
        return ""
    
def print_prompt(chunk_i: int, chunk_paths: List[Path]):
    chunk_path = chunk_paths[chunk_i]
    print(f"\nChunk {chunk_i+1}/{len(chunk_paths)}: ")
    print_txt_file(chunk_path)
    print("""Commands: [t]oggle pause/play, [n]ext chunk, [p]revious chunk, 
          [i]ncrease speed, [d]ecrease speed, [q]uit""")
    print("> ", end='')
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Listen to PDF files using text-to-speech")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--first_page", default=1, type=int, help="First page number")
    parser.add_argument("--speed", default=DEFAULT_SPEED_WPM, type=int, help="Speech speed (words per minute)")
    parser.add_argument("--chunk_size", default=5, type=int, help="Text chunks size")
    parser.add_argument("--engine", choices=["espeak", "mimic3"], default="mimic3",
                        help="Engine used for TTS")
    parser.add_argument("--two_columns", action='store_true', help="Assumes pdf has two columns")

    args = parser.parse_args()

    with TemporaryDirectory(prefix="pdf2speech_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        pdf_path = Path(args.filename)
        pdf_txt_path = None
        if args.two_columns:
            pdf_two_cols = split_pdf_two_columns(pdf_path, tmp_dir_path)
            first_page = 2*args.first_page - 1 
            pdf_txt_path = pdf_to_text(pdf_two_cols, first_page, tmp_dir_path)
        else:
            pdf_txt_path = pdf_to_text(pdf_path, args.first_page, tmp_dir_path)
        chunk_paths = file_make_chunks(tmp_dir_path, pdf_txt_path, args.chunk_size)

        curr_speed = args.speed
        chunk_i = 0
        is_playing = True
        while chunk_i < len(chunk_paths):
            while not is_playing:
                cmd = input("To continue playing, enter [t] > ")
                if cmd == "t":
                    is_playing = True

            chunk_path = chunk_paths[chunk_i]
            if args.engine == "espeak":
                tmp_wav = txt_to_wav_espeak(chunk_path, curr_speed)
            elif args.engine == "mimic3":
                tmp_wav = txt_to_wav_mimic3(chunk_path, curr_speed)
                next_chunk_i = chunk_i + 1
                if next_chunk_i < len(chunk_paths):
                    next_chunk = chunk_paths[next_chunk_i]
                    # prefetch the next chunk with current speed
                    pf_thread = Thread(target=txt_to_wav_mimic3, args=(next_chunk, curr_speed))
                    pf_thread.start()
            stop_playing = Event()
            thread = play_wav(tmp_wav, stop_playing)
            prev_chunk_i = chunk_i
            print_prompt(chunk_i, chunk_paths)
            while thread.is_alive():
                cmd = get_cmd()
                if cmd == "n":
                    stop_playing.set()
                    chunk_i += 1
                elif cmd == "p":
                    stop_playing.set()
                    if chunk_i > 0:
                        chunk_i -= 1
                elif cmd == "i":
                    curr_speed += SPEED_INCREMENT
                    print(f"Next chunk speed = {curr_speed} words/min")
                elif cmd == "d":
                    curr_speed -= SPEED_INCREMENT
                    print(f"Next chunk speed = {curr_speed} words/min")
                elif cmd == "q":
                    stop_playing.set()
                    chunk_i = len(chunk_paths) + 1
                elif cmd == "t":
                    stop_playing.set()
                    is_playing = False
                elif cmd == "":
                    pass
                else:
                    print(f"Unkown command: {cmd}")
            stop_playing.set()
            if prev_chunk_i == chunk_i and is_playing:
                chunk_i += 1


if __name__ == "__main__":
    main()
