from _typeshed import Incomplete
from collections.abc import Generator

STRING_TYPES: Incomplete
STRING_TYPES = str
xrange = range
tokens: Incomplete
literals: str

def t_CPP_WS(t): ...

t_CPP_POUND: str
t_CPP_DPOUND: str
t_CPP_ID: str

def CPP_INTEGER(t): ...
t_CPP_INTEGER = CPP_INTEGER
t_CPP_FLOAT: str

def t_CPP_STRING(t): ...
def t_CPP_CHAR(t): ...
def t_CPP_COMMENT1(t): ...
def t_CPP_COMMENT2(t): ...
def t_error(t): ...
def trigraph(input): ...

class Macro:
    name: Incomplete
    value: Incomplete
    arglist: Incomplete
    variadic: Incomplete
    vararg: Incomplete
    source: Incomplete
    def __init__(self, name, value, arglist: Incomplete | None = ..., variadic: bool = ...) -> None: ...

class Preprocessor:
    lexer: Incomplete
    macros: Incomplete
    path: Incomplete
    temp_path: Incomplete
    parser: Incomplete
    def __init__(self, lexer: Incomplete | None = ...) -> None: ...
    def tokenize(self, text): ...
    def error(self, file, line, msg) -> None: ...
    t_ID: Incomplete
    t_INTEGER: Incomplete
    t_INTEGER_TYPE: Incomplete
    t_STRING: Incomplete
    t_SPACE: Incomplete
    t_NEWLINE: Incomplete
    t_WS: Incomplete
    def lexprobe(self) -> None: ...
    def add_path(self, path) -> None: ...
    def group_lines(self, input) -> Generator[Incomplete, None, None]: ...
    def tokenstrip(self, tokens): ...
    def collect_args(self, tokenlist): ...
    def macro_prescan(self, macro): ...
    def macro_expand_args(self, macro, args): ...
    def expand_macros(self, tokens, expanded: Incomplete | None = ...): ...
    def evalexpr(self, tokens): ...
    source: Incomplete
    def parsegen(self, input, source: Incomplete | None = ...) -> Generator[Incomplete, None, None]: ...
    def include(self, tokens) -> Generator[Incomplete, None, None]: ...
    def define(self, tokens) -> None: ...
    def undef(self, tokens) -> None: ...
    ignore: Incomplete
    def parse(self, input, source: Incomplete | None = ..., ignore=...) -> None: ...
    def token(self): ...