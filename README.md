subtitle-parser
===============

This is a simple Python library for parsing subtitle files in SRT or WebVTT format.

How to use stand-alone?
-----------------------

You can use this as a script to convert subtitles to HTML or CSV.

If you have installed it using `pip install subtitle-parser`, use `python3 -m subtitle_parser`. If you have cloned this repository or downloaded the file, use `python3 subtitle_parser.py`.

Examples:

```
$ python3 subtitle_parser.py --to csv Zoom_transcript.vtt --output transcript.csv
```

```
$ python3 -m subtitle_parser --to html episode.srt --input-charset iso-8859-15 --output dialogue.html
```

How to use as a library?
------------------------

```python
import subtitle_parser

with open('some_file.srt', 'r') as input_file:
    parser = subtitle_parser.SrtParser(input_file)
    parser.parse()

parser.print_warnings()

for subtitle in parser.subtitles:
    print(subtitle.text)
```
