import argparse
import codecs
import os.path
import re
import sys
import traceback


__version__ = '1.1.0'


__all__ = [
    'SubtitleError', 'Subtitle',
    'SrtParser', 'WebVttParser',
    'render_html', 'render_csv',
]


class SubtitleError(ValueError):
    """Invalid subtitle file"""


def format_timestamp(ts):
    return '{0:02}:{1:02}:{2:02}.{3:03}'.format(*ts)


class Subtitle(object):
    def __init__(self, number, start, end, text):
        self.number = number
        self.start = start
        self.end = end
        self.text = text

    def __eq__(self, other):
        return (
            self.number, self.start, self.end, self.text,
        ) == (
            other.number, other.start, other.end, other.text,
        )

    def __hash__(self):
        return hash((
            self.number, self.start, self.end, self.text,
        ))

    def __repr__(self):
        return (
            '<Subtitle number={number} '
            + 'start={start} end={end} text={text}>'
        ).format(
            number=self.number,
            start=format_timestamp(self.start),
            end=format_timestamp(self.end),
            text=self.text,
        )


class SrtParser(object):
    number_required = True

    _re_timestamps = re.compile(
        r'^(.*) --> (.*)$',
    )
    _re_timestamp = re.compile(
        r'^([0-9]+)?:([0-9][0-9]):([0-9][0-9])[,.]([0-9][0-9][0-9])$',
    )

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.lineno = 0
        self._next_line = None
        self.subtitles = []
        self.warnings = []

    def print_warnings(self, fileobj=sys.stderr):
        try:
            filename = self.fileobj.name
        except AttributeError:
            filename = None
        if not isinstance(filename, str):
            filename = repr(self.fileobj)
        for lineno, text in self.warnings:
            print(
                "{name}:{lineno}: {text}".format(
                    name=filename,
                    lineno=lineno,
                    text=text,
                ),
                file=fileobj,
            )

    def parse(self):
        # Skip blank lines
        while self.next_line() == '':
            self.read_line()

        # Read subtitles
        while self.parse_subtitle():
            pass

    def parse_subtitle(self):
        # Read subtitle number
        line = self.next_line()
        if line is None:
            return False
        if '-->' not in line:
            self.read_line()
            try:
                subtitle_number = int(line)
            except (ValueError, OverflowError):
                raise SubtitleError(
                    "Invalid subtitle number line {lineno}".format(
                        lineno=self.lineno,
                    ),
                )

            prev_subtitle_number = 0
            if self.subtitles:
                prev_subtitle_number = self.subtitles[-1].number
            if subtitle_number != prev_subtitle_number + 1:
                self.warning(
                    "Subtitle number is {actual}, expected {expected}".format(
                        actual=subtitle_number,
                        expected=prev_subtitle_number + 1,
                    ),
                )
        elif self.number_required:
            raise SubtitleError(
                "Missing subtitle number line {lineno}".format(
                    lineno=self.lineno + 1,
                ),
            )
        else:
            subtitle_number = None

        # Read timestamps
        start, end = self.parse_timestamps()

        # Read lines
        first_line_lineno = self.lineno
        lines = []
        line = self.read_line()
        while line:
            lines.append(line)
            line = self.read_line()
        if not lines:
            raise SubtitleError(
                "No content in subtitle line {lineno}".format(
                    lineno=first_line_lineno,
                ),
            )

        self.subtitles.append(Subtitle(
            subtitle_number, start, end,
            '\n'.join(lines),
        ))

        self.skip_blank_lines()

        return True

    def skip_blank_lines(self):
        line = self.next_line()
        while line == '':
            self.read_line()
            line = self.next_line()

    def decode_timestamp(self, s):
        m = self._re_timestamp.match(s)
        if not m:
            raise SubtitleError(
                "Invalid timestamp line {lineno}".format(
                    lineno=self.lineno,
                ),
            )
        try:
            hours = m.group(1)
            if hours:
                hours = int(hours)
            else:
                hours = 0
            minutes = int(m.group(2))
            seconds = int(m.group(3))
            milliseconds = int(m.group(4))
        except ValueError:
            raise SubtitleError(
                "Invalid timestamp line {lineno}".format(
                    lineno=self.lineno,
                ),
            )
        return hours, minutes, seconds, milliseconds

    def parse_timestamps(self):
        line = self.read_line()
        if line is None:
            raise SubtitleError(
                "Missing timestamps line {lineno}".format(
                    lineno=self.lineno,
                ),
            )
        m = self._re_timestamps.match(line)
        if not m:
            raise SubtitleError(
                "Invalid timestamps line {lineno}".format(
                    lineno=self.lineno,
                ),
            )
        ts = m.groups()
        ts = (self.decode_timestamp(s) for s in ts)
        start, end = ts
        return start, end

    def read_line(self):
        try:
            if self._next_line is None:
                try:
                    line = next(self.fileobj)
                except StopIteration:
                    return None
            else:
                line = self._next_line
                try:
                    self._next_line = next(self.fileobj)
                except StopIteration:
                    self._next_line = None
        except UnicodeDecodeError as e:
            raise SubtitleError(
                "Invalid unicode in subtitles near line {lineno}".format(
                    lineno=self.lineno + 1,
                ),
            ) from e
        self.lineno += 1
        return line.rstrip('\r\n')

    def next_line(self):
        if self._next_line is None:
            try:
                self._next_line = next(self.fileobj)
            except StopIteration:
                return None
            except UnicodeDecodeError as e:
                raise SubtitleError(
                    "Invalid unicode in subtitles near line {lineno}".format(
                        lineno=self.lineno + 1,
                    ),
                ) from e
        return self._next_line.rstrip('\r\n')

    def warning(self, message, *, lineno=None):
        if lineno is None:
            lineno = self.lineno
        self.warnings.append((lineno, message))


class WebVttParser(SrtParser):
    number_required = False

    def parse(self):
        # Expect 'WEBVTT' on first line
        line = self.read_line()
        if line is None:
            raise SubtitleError("File is empty")
        if not line.startswith('WEBVTT'):
            raise SubtitleError("First line doesn't start with 'WEBVTT'")

        super(WebVttParser, self).parse()

    def parse_subtitle(self):
        line = self.next_line()

        # Skip comments
        if line is None:
            return False
        elif line.startswith('NOTE ') or line == 'STYLE':
            self.skip_until_blank_line()
            return True

        return super(WebVttParser, self).parse_subtitle()

    def skip_until_blank_line(self):
        line = self.next_line()
        while line:
            self.read_line()
            line = self.next_line()
        self.skip_blank_lines()


def render_html(subtitles, file_out):
    import html

    for subtitle in subtitles:
        print(
            "<p>{ts} {text}</p>".format(
                ts=format_timestamp(subtitle.start),
                text=html.escape(subtitle.text).replace('\n', '<br>'),
            ),
            file=file_out,
        )


def render_csv(subtitles, file_out):
    import csv

    writer = csv.writer(file_out)
    writer.writerow(['start', 'end', 'text'])
    for subtitle in subtitles:
        writer.writerow([
            format_timestamp(subtitle.start),
            format_timestamp(subtitle.end),
            subtitle.text,
        ])


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--to', help="Output format")
    arg_parser.add_argument('--input-charset', default=None)
    arg_parser.add_argument('input', help="Input subtitles")
    arg_parser.add_argument('--output', '-o', help="Output file name")

    args = arg_parser.parse_args()

    # Pick format
    if not args.to:
        arg_parser.error("No output format specified (use --to)")
        return
    to = args.to.lower()
    if to == 'html':
        render_func = render_html
        ext = '.html'
    elif to == 'csv':
        render_func = render_csv
        ext = '.csv'
    else:
        arg_parser.error("Requested output format is not supported")
        return

    # Pick input
    if not args.input:
        arg_parser.error("No input subtitles file specified")
        return
    elif not os.path.exists(args.input):
        arg_parser.error("Specified input subtitles doesn't exist")
        return
    file_input = open(args.input, 'rb')

    # Pick encoding
    if args.input_charset is None:
        try:
            import chardet
        except ImportError:
            charset = None
            print("chardet is not available", file=sys.stderr)
        else:
            detector = chardet.UniversalDetector()
            chunk = file_input.read(4096)
            while chunk and not detector.done:
                detector.feed(chunk)
                chunk = file_input.read(4096)
            detector.close()
            charset = detector.result['encoding']
            file_input.seek(0, 0)

        if charset:
            print(
                "{name}: charset detected as '{charset}'".format(
                    name=args.input,
                    charset=charset,
                ),
                file=sys.stderr
            )
        else:
            charset = 'utf-8'
            print(
                "{name}: couldn't detect charset, using '{charset}'".format(
                    name=args.input,
                    charset=charset,
                ),
                file=sys.stderr,
            )
    else:
        charset = args.input_charset
    file_input = codecs.getreader(charset)(file_input)

    # Pick output
    if not args.output:
        output = os.path.splitext(args.input)[0] + ext
        if os.path.exists(output):
            arg_parser.error(
                (
                    "Default output is {path} but it already exists, "
                    + "please remove it or use --output"
                ).format(path=os.path.basename(output)),
            )
            return
    else:
        output = args.output
    file_output = open(output, 'w', encoding='utf-8')

    # Parse
    if args.input.lower().endswith('.vtt'):
        parser_cls = WebVttParser
    else:
        parser_cls = SrtParser
    parser = parser_cls(file_input)
    try:
        parser.parse()
    except SubtitleError:
        print(
            "Error processing {name}:".format(name=args.input),
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    # Print warnings
    for lineno, text in parser.warnings:
        print(
            "{name}:{lineno}: {text}".format(
                name=args.input,
                lineno=lineno,
                text=text,
            ),
            file=sys.stderr,
        )

    # Write output
    render_func(parser.subtitles, file_output)
    file_output.close()


if __name__ == '__main__':
    main()
