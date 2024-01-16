# pdf2speech
Simple python application to read pdf's out loud

# Usage
```
usage: pdf2speech.py [-h] [--first_page FIRST_PAGE] [--speed SPEED] [--chunk_size CHUNK_SIZE] [--engine {espeak,mimic3}] filename

Listen to PDF files using text-to-speech

positional arguments:
  filename              PDF filename

optional arguments:
  -h, --help            show this help message and exit
  --first_page FIRST_PAGE
                        First page number
  --speed SPEED         Speech speed (words per minute)
  --chunk_size CHUNK_SIZE
                        Text chunks size
  --engine {espeak,mimic3}
                        Engine used for TTS
```
Example: `python pdf2speech.py test_data/pg11.pdf`

# Requirements

- [`pdftotext`](https://en.wikipedia.org/wiki/Pdftotext), install package `poppler-utils` on linux.
- [`espeak`](https://espeak.sourceforge.net/), install package `espeak` on linux.
    - [mbrola voices for espeak](https://github.com/espeak-ng/espeak-ng/blob/master/docs/mbrola.md#installation-of-standard-packages) also need to be installed to get a better sounding voice
- [`mimic3`](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#docker-image) better sounding alternative to espeak, easy to use via docker. See also [mimic3-server](https://github.com/MycroftAI/mimic3/blob/master/docker/mimic3-server) script to run the server more easily.
- [`aplay`](https://github.com/alsa-project/alsa-utils), install package `alsa-utils` on linux.

# Note
This project was developed in a few hours of my spare time. If someone wants to build on this and maybe submit pull requests to improve it, I'm happy to take a look at it.
