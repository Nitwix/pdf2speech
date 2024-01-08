import subprocess
import argparse
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List
from pathlib import Path

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

def play_wav(wav_path: Path) -> None:
    subprocess.run(["aplay", str(wav_path)], check=True)

def text_cut_chunks(txt: str, chunk_size: int) -> List[str]:
    words = txt.split(" ")
    chunk_lists = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    return [" ".join(l) for l in chunk_lists]

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


def main():
    parser = argparse.ArgumentParser(description="Convert PDF text to speech and play it.")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--first_page", default=1, type=int, help="First page number")
    parser.add_argument("--speed", default=160, type=int, help="Speech speed (words per minute)")
    parser.add_argument("--chunk_size", default=50, type=int, help="Text chunks size")

    args = parser.parse_args()
    with TemporaryDirectory(prefix="pdf2speech_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        pdf_txt_path = pdf_to_text(args.filename, args.first_page, tmp_dir_path)
        chunk_paths = file_make_chunks(tmp_dir_path, pdf_txt_path, args.chunk_size)
        for chunk_path in chunk_paths:
            tmp_wav = txt_to_wav(chunk_path, args.speed)
            play_wav(tmp_wav)


if __name__ == "__main__":
    main()
