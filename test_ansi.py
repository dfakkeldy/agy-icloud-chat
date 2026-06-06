import re

def strip_ansi_and_control(text):
    text = text.replace('\x04', '')
    text = text.replace('\x1b]0;', '')
    ANSI_ESCAPE = re.compile(r'''
        \x1B
        (?:
            [@-Z\\-_]
        |
            \[
            [0-?]*
            [ -/]*
            [@-~]
        |
            [()][A-Z0-9]
        |
            \].*?(?:\x07|\x1B\\)
        |
            [78c]
        )
    ''', re.VERBOSE)
    return ANSI_ESCAPE.sub('', text)

text = '\x04Right now it\'s **Saturday**.\n\x1b[?1006l\x1b[?1003l\x1b[?1002l\x1b[?1000l\x1b(B\x1b[>4m\x1b[<u\x1b[?1004l\x1b[?2031l\x1b[?2004l\x1b[?25h\x1b7\x1b[r\x1b8\x1b]0;\x1b[?25h'
print(repr(strip_ansi_and_control(text)))
