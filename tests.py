import unittest

from subtitle_parser import SubtitleError, Subtitle, SrtParser


class TestSrtSubtitles(unittest.TestCase):
    def test_valid(self):
        import io
        import textwrap

        parser = SrtParser()
        parser.parse(io.StringIO(textwrap.dedent('''\
            1
            00:00:00,123 --> 00:00:03,456
            Hi there

            2
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format
        ''')))
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

        parser = SrtParser()
        parser.parse(io.StringIO(textwrap.dedent('''\
            2
            00:00:00,123 --> 00:00:03,456
            Hi there



            5
            00:01:04,843 --> 00:01:05,428
            This is an example of a
            subtitle file in SRT format
        ''')))
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
            SrtParser().parse(io.StringIO('1\ntest\n'))
        self.assertEqual(err.exception.args[0], 'Invalid timestamps line 2')

        with self.assertRaises(SubtitleError) as err:
            SrtParser().parse(
                io.StringIO('1\n00:00:00,123 --> 00:00:03,456\n\n'),
            )
        self.assertEqual(
            err.exception.args[0],
            'No content in subtitle line 2',
        )

        with self.assertRaises(SubtitleError) as err:
            SrtParser().parse(io.StringIO('1\n'))
        self.assertEqual(err.exception.args[0], 'Missing timestamps line 1')


if __name__ == '__main__':
    unittest.main()
