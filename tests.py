import unittest

import re
from subtitle_parser import SubtitleError, Subtitle, SrtParser, WebVttParser


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
            Subtitle(1, (0, 0, 0, 123), (0, 0, 3, 456), 'Hi there'),
            Subtitle(
                2, (0, 1, 4, 843), (0, 1, 5, 428),
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
            Subtitle(2, (0, 0, 0, 123), (0, 0, 3, 456), 'Hi there'),
            Subtitle(
                5, (0, 1, 4, 843), (0, 1, 5, 428),
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
            Subtitle(1, (0, 0, 0, 123), (0, 0, 3, 456), 'Hi there'),
            Subtitle(
                None, (0, 1, 4, 843), (0, 1, 5, 428),
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


if __name__ == '__main__':
    unittest.main()
