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

def text_to_wav(txt_file: NamedTemporaryFile, speed: int) -> NamedTemporaryFile:
    tmp_wav = NamedTemporaryFile("rb+")
    subprocess.run(["espeak", 
                    "-f", txt_file.name, 
                    "-w", tmp_wav.name, 
                    "-s", str(speed)], 
                    check=True)
    return tmp_wav

def play_wav(wav_file: NamedTemporaryFile) -> None:
    subprocess.run(["aplay", wav_file.name], check=True)

def text_cut_chunks(txt: str, chunk_size: int) -> List[str]:
    words = txt.split()
    return [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]

def file_make_chunks(txt_file: NamedTemporaryFile, chunk_size: int) -> List[NamedTemporaryFile]:
    txt_file.seek(0)
    txt_str = txt_file.read()
    chunks = text_cut_chunks(txt_str, chunk_size)



def main():
    parser = argparse.ArgumentParser(description="Convert PDF text to speech and play it.")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--first_page", default=1, type=int, help="First page number")
    parser.add_argument("--speed", default=160, type=int, help="Speech speed (words per minute)")
    parser.add_argument("--chunk_size", default=50, type=int, help="Text chunks size")

    args = parser.parse_args()
    with TemporaryDirectory(prefix="pdf2speech") as tmp_dir:
        tmp_dir_path = Path(tmp_dir.name)
        txt_file = pdf_to_text(args.filename, args.first_page, tmp_dir_path)
        pass


if __name__ == "__main__":
    main()
