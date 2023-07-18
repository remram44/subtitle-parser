Changelog
=========

1.3.0 (2023-07-18)
------------------

* Read the speaker name from WebVTT files, such as the ones written by WebEx. Add the `--with-name` and `--without-name` to the converter. CSVs will not contain the speaker name by default to maintain compatibility.

1.2.0 (2023-01-11)
------------------

* Fix a `TypeError` if subtitle numbers were not required but present, and one is missing. Show a warning.
* Compatibility with `chardet` 5.

1.1.0 (2022-05-02)
------------------

* Raise `SubtitleError` for invalid unicode input instead of `UnicodeDecodeError`.

1.0.1 (2022-01-28)
------------------

* Don't error if you don't have `chardet` and you didn't set `--input-charset`.

1.0.0 (2022-01-27)
------------------

* First release
