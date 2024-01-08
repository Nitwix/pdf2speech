# pdf2speech
Simple python application to read pdf's out loud

# Usage
```usage: pdf2speech.py [-h] [--first_page FIRST_PAGE] [--speed SPEED] [--chunk_size CHUNK_SIZE] filename

Convert PDF text to speech and play it.

positional arguments:
  filename              PDF filename

optional arguments:
  -h, --help            show this help message and exit
  --first_page FIRST_PAGE
                        First page number
  --speed SPEED         Speech speed (words per minute)
  --chunk_size CHUNK_SIZE
                        Text chunks size
```
Example: `python pdf2speech.py test_data/pg11.pdf`

# Requirements

- [`pdftotext`](https://en.wikipedia.org/wiki/Pdftotext), install package `poppler-utils` on linux.
- [`espeak`](https://espeak.sourceforge.net/), install package `espeak` on linux.
- [`aplay`](https://github.com/alsa-project/alsa-utils), install package `alsa-utils` on linux.