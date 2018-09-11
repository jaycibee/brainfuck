from argparse import ArgumentParser, FileType
from tatsu import compile
from tatsu.exceptions import ParseException
from sys import stdout, exit, __stdout__
from copy import copy

MAX_RECURSION_DEPTH = 100

__all__ = ['execute']

parser = compile("""
start = { stmt }* $ ;
loop = '[' @:( { stmt }* ) ']' ;
stmt = /[\.,\+\-><]/ | loop ;
""")


class Error:
    def __init__(self, text):
        print(f"\033[31m\033[1m{self.__class__.__name__}:\033[0m {text}")
        exit()


class SyntaxError(Error):
    pass


class ParsingError(Error):
    pass


class RecursionError(Error):
    pass


class RuntimeError(Error):
    pass


class _Getch:
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def read(self, _):
        return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


stdin = _Getch()


def parse(text):
    global parser
    text = "".join([i for i in text if i in "><+-.,[]"])
    try:
        return parser.parse(text)
    except ParseException as e:
        SyntaxError(str(e))
    except BaseException as e:
        ParsingError(str(e))


def walker(ast, globals=[0 for i in range(256)], cur=0, loop=False, _r=0):
    if _r >= MAX_RECURSION_DEPTH:
        RecursionError("Exceeded maximal loop nesting depth")
    loopcond = copy(cur)
    while globals[loopcond] > 0 or loop is False:
        for token in ast:
            if token == ">":
                cur = (cur + 1) % 256
            elif token == "<":
                cur = (cur + 1) % 256
            elif token == "+":
                globals[cur] = (globals[cur] + 1) % 128
            elif token == "-":
                globals[cur] = (globals[cur] - 1) % 128
            elif token == ".":
                stdout.write(chr(globals[cur]))
            elif token == ",":
                globals[cur] = ord(stdin.read(1)) % 128
            else:
                walker(token, globals, cur, True, _r + 1)
        if not loop:
            break


def execute(text):
    walker(parse(text))


def __cli_init__():
    global stdout, stdin
    cli = ArgumentParser()
    cli.add_argument(type=FileType("r"), metavar="file", dest="file", help="File to execute")
    cli.add_argument("--stdout", type=FileType("w"), metavar="filename", dest="out",
                     help="Optional file to write output to")
    cli.add_argument("--stdin", type=FileType("r"), metavar="filename", dest="inp",
                     help="Optional file to take input from")
    args = cli.parse_args()
    stdout = args.out if args.out is not None else stdout
    stdin = args.inp if args.inp is not None else stdin
    with args.file as f:
        ast = parse(f.read())
    try:
        walker(ast)
    except BaseException as e:
        RuntimeError(str(e))
    print("\n\033[35m(Finished execution)\033[0m")


if __name__ == '__main__':
    __cli_init__()
