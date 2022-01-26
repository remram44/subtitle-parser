import re


class SubtitleError(ValueError):
    """Invalid subtitle file"""


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
        def format_ts(ts):
            return '{0:02}:{1:02}:{2:02},{3:03}'.format(*ts)

        return (
            '<Subtitle number={number} '
            + 'start={start} end={end} text={text}>'
        ).format(
            number=self.number,
            start=format_ts(self.start),
            end=format_ts(self.end),
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
        self.lineno += 1
        return line.rstrip('\r\n')

    def next_line(self):
        if self._next_line is None:
            try:
                self._next_line = next(self.fileobj)
            except StopIteration:
                return None
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
        if line != 'WEBVTT':
            raise SubtitleError("First line is not 'WEBVTT'")

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
