import unittest

import re
from subtitle_parser import SubtitleError, Subtitle, \
    SrtParser, WebVttParser, \
    render_html, render_csv, render_srt


def ts(hour, minute, second, milli):
    return ((hour * 60 + minute) * 60 + second) * 1000 + milli


class TestSrtSubtitles(unittest.TestCase):
    def test_valid(self):
        import io
        import textwrap

        parser = SrtParser(io.StringIO(textwrap.dedent('''\
            1
            00:00:00,123 --> 00:00:03,456
            Hi there

            2
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format
        ''')))
        parser.parse()
        self.assertEqual(parser.subtitles, [
            Subtitle(1, ts(0, 0, 0, 123), ts(0, 0, 3, 456), 'Hi there'),
            Subtitle(
                2, ts(0, 1, 4, 843), ts(0, 1, 5, 428),
                'This is an example of a\nsubtitle file in SRT format',
            ),
        ])

    def test_warnings(self):
        import io
        import textwrap

        parser = SrtParser(io.StringIO(textwrap.dedent('''\
            2
            00:00:00,123 --> 00:00:03,456
            Hi there



            5
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format
        ''')))
        parser.parse()
        self.assertEqual(parser.subtitles, [
            Subtitle(2, ts(0, 0, 0, 123), ts(0, 0, 3, 456), 'Hi there'),
            Subtitle(
                5, ts(0, 1, 4, 843), ts(0, 1, 5, 428),
                'This is an example of a\nsubtitle file in SRT format',
            ),
        ])
        self.assertEqual(parser.warnings, [
            (1, 'Subtitle number is 2, expected 1'),
            (7, 'Subtitle number is 5, expected 3'),
        ])

    def test_wrong(self):
        import io

        with self.assertRaises(SubtitleError) as err:
            SrtParser(io.StringIO('1\ntest\n')).parse()
        self.assertEqual(err.exception.args[0], 'Invalid timestamps line 2')

        with self.assertRaises(SubtitleError) as err:
            SrtParser(
                io.StringIO('1\n00:00:00,123 --> 00:00:03,456\n\n'),
            ).parse()
        self.assertEqual(
            err.exception.args[0],
            'No content in subtitle line 2',
        )

        with self.assertRaises(SubtitleError) as err:
            SrtParser(io.StringIO('1\n')).parse()
        self.assertEqual(err.exception.args[0], 'Missing timestamps line 1')

        with self.assertRaises(SubtitleError) as err:
            SrtParser(
                io.StringIO('00:00:00,123 --> 00:00:03,456\nHi there\n'),
            ).parse()
        self.assertEqual(
            err.exception.args[0],
            'Missing subtitle number line 1',
        )

    def test_invalid_unicode(self):
        import codecs
        import io

        with self.assertRaises(SubtitleError) as err:
            SrtParser(codecs.getreader('utf-8')(io.BytesIO(
                b'1\n00:00:00,123 --> 00:00:03,456\nHi there\n\n' * 100
                + b'\xE9\n'
                + b'1\n00:00:00,123 --> 00:00:03,456\nHi there\n\n' * 100
            ))).parse()
        m = re.match(
            '^Invalid unicode in subtitles near line ([0-9]+)$',
            err.exception.args[0],
        )
        self.assertTrue(m)
        # Can't assert exact line number, codec will raise before you get to
        # the exact line because it decodes big chunks at a time
        self.assertTrue(350 < int(m.group(1), 10) < 400)


class TestRender(unittest.TestCase):
    subtitles = [
        Subtitle(
            2, ts(0, 0, 0, 123), ts(0, 0, 3, 456),
            'Hi there', name='Remi',
        ),
        Subtitle(
            5, ts(0, 1, 4, 843), ts(0, 1, 5, 428),
            'This is an example of a\nsubtitle file in SRT format',
        ),
    ]

    @classmethod
    def call_render(cls, func, show_name):
        import io

        out = io.StringIO()
        func(cls.subtitles, out, show_name=show_name)
        return out.getvalue()

    def test_html(self):
        nonames = (
            '<p>00:00:00.123 Hi there</p>\n'
            + '<p>00:01:04.843 This is an example of a<br>'
            + 'subtitle file in SRT format</p>\n'
        )
        names = (
            '<p>00:00:00.123 Remi: Hi there</p>\n'
            + '<p>00:01:04.843 This is an example of a'
            + '<br>subtitle file in SRT format</p>\n'
        )

        self.assertEqual(
            self.call_render(render_html, True),
            names,
        )
        self.assertEqual(
            self.call_render(render_html, False),
            nonames,
        )
        self.assertEqual(
            self.call_render(render_html, None),
            names,
        )

    def test_csv(self):
        import textwrap

        nonames = textwrap.dedent('''\
            start,end,text\r
            00:00:00.123,00:00:03.456,Hi there\r
            00:01:04.843,00:01:05.428,"This is an example of a
            subtitle file in SRT format"\r
        ''')
        names = textwrap.dedent('''\
            start,end,name,text\r
            00:00:00.123,00:00:03.456,Remi,Hi there\r
            00:01:04.843,00:01:05.428,,"This is an example of a
            subtitle file in SRT format"\r
        ''')

        self.assertEqual(
            self.call_render(render_csv, True),
            names,
        )
        self.assertEqual(
            self.call_render(render_csv, False),
            nonames,
        )
        self.assertEqual(
            self.call_render(render_csv, None),
            nonames,
        )

    def test_srt(self):
        import textwrap

        nonames = textwrap.dedent('''\
            1
            00:00:00,123 --> 00:00:03,456
            Hi there

            2
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format

        ''')
        names = textwrap.dedent('''\
            1
            00:00:00,123 --> 00:00:03,456
            [Remi]
            Hi there

            2
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format

        ''')

        self.assertEqual(
            self.call_render(render_srt, True),
            names,
        )
        self.assertEqual(
            self.call_render(render_srt, False),
            nonames,
        )
        self.assertEqual(
            self.call_render(render_srt, None),
            names,
        )


class TestWebVttSubtitles(unittest.TestCase):
    def test_valid(self):
        import io
        import textwrap

        # From https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API

        parser = WebVttParser(io.StringIO(textwrap.dedent('''\
            WEBVTT

            STYLE
            ::cue {
              background-image: linear-gradient(to bottom, dimgray, lightgray);
              color: papayawhip;
            }
            /* Style blocks cannot use blank lines nor arrows */

            NOTE comment blocks can be used between style blocks.

            STYLE
            ::cue(b) {
              color: peachpuff;
            }

            1
            00:00:00,123 --> 00:00:03,456
            Hi there

            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format

            NOTE style blocks cannot appear after the first cue.
        ''')))
        parser.parse()
        self.assertEqual(parser.subtitles, [
            Subtitle(1, ts(0, 0, 0, 123), ts(0, 0, 3, 456), 'Hi there'),
            Subtitle(
                None, ts(0, 1, 4, 843), ts(0, 1, 5, 428),
                'This is an example of a\nsubtitle file in SRT format',
            ),
        ])

    def test_wrong(self):
        import io

        with self.assertRaises(SubtitleError) as err:
            WebVttParser(
                io.StringIO('1\n00:00:00,123 --> 00:00:03,456\ntest\n'),
            ).parse()
        self.assertEqual(
            err.exception.args[0],
            "First line doesn't start with 'WEBVTT'",
        )

    def test_numbering_check(self):
        import io
        import textwrap

        parser = WebVttParser(io.StringIO(textwrap.dedent('''\
            WEBVTT

            1
            00:00:00,123 --> 00:00:01,456
            number

            00:00:02,000 --> 00:00:03,000
            no number

            00:00:04,000 --> 00:00:05,000
            no number

            2
            00:00:06,000 --> 00:00:07,000
            number

            4
            00:00:08,000 --> 00:00:09,000
            wrong number

            00:00:10,000 --> 00:00:11,000
            no number
        ''')))
        parser.parse()
        self.assertEqual(parser.subtitles, [
            Subtitle(1, ts(0, 0, 0, 123), ts(0, 0, 1, 456), 'number'),
            Subtitle(None, ts(0, 0, 2, 0), ts(0, 0, 3, 0), 'no number'),
            Subtitle(None, ts(0, 0, 4, 0), ts(0, 0, 5, 0), 'no number'),
            Subtitle(2, ts(0, 0, 6, 0), ts(0, 0, 7, 0), 'number'),
            Subtitle(4, ts(0, 0, 8, 0), ts(0, 0, 9, 0), 'wrong number'),
            Subtitle(None, ts(0, 0, 10, 0), ts(0, 0, 11, 0), 'no number'),
        ])
        self.assertEqual(parser.warnings, [
            (6, 'Subtitle numbers stop line 7'),
            (13, 'Subtitle numbers (re)starts line 14'),
            (17, 'Subtitle number is 4, expected 3'),
            (20, 'Subtitle numbers stop line 21'),
        ])

    def test_webex_check(self):
        import io
        import textwrap

        parser = WebVttParser(io.StringIO(textwrap.dedent('''\
            WEBVTT

            1 "Shmo, Jonathan" (1838608384)
            00:11:03.989 --> 00:11:07.169
            Another option is just to pop the tool tip.

            2 "Doe, Kevin" (3768348160)
            00:11:07.169 --> 00:11:16.619
            Right. That's okay. That's I'm okay with that.

            3 "Shmo, Jonathan" (1838608384)
            00:11:16.619 --> 00:11:23.369
            Yep, yeah, we can just defaulted on for the 1st time.

            4 "Doe, Kevin" (3768348160)
            00:11:23.369 --> 00:11:28.679
            Um, Paul, I think Paul had the hands up.

            5 "Conf WA HQ B5 3A" (1129774080)
            00:11:28.679 --> 00:11:34.649
            What is what is the difference for the user?

            6 "Conf WA HQ B5 3A" (1129774080)
            00:11:34.649 --> 00:11:38.429
            Whether there's Bluetooth connection.

            7 "Conf WA HQ B5 3A" (1129774080)
            00:11:38.429 --> 00:11:42.929
            Or there's no Bluetooth connection because.

            8 "Conf WA HQ B5 3A" (1129774080)
            00:11:42.929 --> 00:11:47.309
            If you lose Bluetooth connection, you still have your GPS.
        ''')))
        parser.parse()
        self.assertEqual(parser.subtitles, [
            Subtitle(
                1, ts(0, 11, 3, 989), ts(0, 11, 7, 169),
                "Another option is just to pop the tool tip.",
                name="Shmo, Jonathan",
            ),
            Subtitle(
                2, ts(0, 11, 7, 169), ts(0, 11, 16, 619),
                "Right. That's okay. That's I'm okay with that.",
                name="Doe, Kevin",
            ),
            Subtitle(
                3, ts(0, 11, 16, 619), ts(0, 11, 23, 369),
                "Yep, yeah, we can just defaulted on for the 1st time.",
                name="Shmo, Jonathan",
            ),
            Subtitle(
                4, ts(0, 11, 23, 369), ts(0, 11, 28, 679),
                "Um, Paul, I think Paul had the hands up.",
                name="Doe, Kevin",
            ),
            Subtitle(
                5, ts(0, 11, 28, 679), ts(0, 11, 34, 649),
                "What is what is the difference for the user?",
                name="Conf WA HQ B5 3A",
            ),
            Subtitle(
                6, ts(0, 11, 34, 649), ts(0, 11, 38, 429),
                "Whether there's Bluetooth connection.",
                name="Conf WA HQ B5 3A",
            ),
            Subtitle(
                7, ts(0, 11, 38, 429), ts(0, 11, 42, 929),
                "Or there's no Bluetooth connection because.",
                name="Conf WA HQ B5 3A",
            ),
            Subtitle(
                8, ts(0, 11, 42, 929), ts(0, 11, 47, 309),
                "If you lose Bluetooth connection, you still have your GPS.",
                name="Conf WA HQ B5 3A",
            ),
        ])


if __name__ == '__main__':
    unittest.main()
