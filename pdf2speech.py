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

SLEEP_INTERVAL = 0.1
SPEED_INCREMENT = 20

def pdf_to_text(pdf_file: str, first_page: int, tmp_dir: Path) -> Path:
    tmp_txt = tmp_dir / "pdf.txt"
    subprocess.run(["pdftotext", "-f", 
                    str(first_page), pdf_file, str(tmp_txt)], check=True)
    return tmp_txt

def txt_to_wav(txt_path: Path, speed: int) -> Path:
    tmp_wav = txt_path.with_suffix(".wav")
    subprocess.run(["espeak", 
                    "-f", str(txt_path), 
                    "-w", str(tmp_wav), 
                    "-s", str(speed)], 
                    check=True)
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
    words = txt.split("\n")
    chunk_lists = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    return ["\n".join(l) for l in chunk_lists]

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
    print("""Commands: [n]ext chunk, [p]revious chunk, 
          [i]ncrease speed, [d]ecrease speed, [q]uit""")
    print("> ", end='')
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Listen to PDF files using text-to-speech")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--first_page", default=1, type=int, help="First page number")
    parser.add_argument("--speed", default=180, type=int, help="Speech speed (words per minute)")
    parser.add_argument("--chunk_size", default=5, type=int, help="Text chunks size")

    args = parser.parse_args()
    curr_speed = args.speed
    chunk_i = 0

    with TemporaryDirectory(prefix="pdf2speech_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        pdf_txt_path = pdf_to_text(args.filename, args.first_page, tmp_dir_path)
        chunk_paths = file_make_chunks(tmp_dir_path, pdf_txt_path, args.chunk_size)

        while chunk_i < len(chunk_paths):
            chunk_path = chunk_paths[chunk_i]
            tmp_wav = txt_to_wav(chunk_path, curr_speed)
            stop_playing = Event()
            thread = play_wav(tmp_wav, stop_playing)
            
            print_prompt(chunk_i, chunk_paths)
            prev_chunk_i = chunk_i
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
                elif cmd == "":
                    pass
                else:
                    print(f"Unkown command: {cmd}")
            stop_playing.set()
            if prev_chunk_i == chunk_i:
                chunk_i += 1


if __name__ == "__main__":
    main()
