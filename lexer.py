import ctypes
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CODE_IDENTIFIER = 0
CODE_CONSTANT = 1
SYM_IDENTIFIER = 0
SYM_CONSTANT = 1

TOKEN_REGEX = re.compile(r"""
    (?P<COMMENT>      //[^\n]*                         )
  | (?P<NEWLINE>      \n                               )
  | (?P<SPACE>        [ \t\r]+                         )
  | (?P<BAD_ID>       [0-9]+[A-Za-z_][A-Za-z0-9_]*     )
  | (?P<BAD_NUMBER>   0[0-9]+                          )
  | (?P<NUMBER>       0|[1-9][0-9]*                    )
  | (?P<WORD>         [A-Za-z][A-Za-z0-9_]*            )
  | (?P<STRING>       "[^"\n]*"                        )
  | (?P<OPEN_STRING>  "[^"\n]*                         )
  | (?P<OPERATOR>     ==|!=|<=|>=|[-+*/%=<>]           )
  | (?P<SEPARATOR>    [{}\[\](),;]                     )
  | (?P<INVALID>      .                                )
""", re.VERBOSE)

STRING_CHAR_REGEX = re.compile(r'[A-Za-z0-9 :.,!?=\-+_()%/*<>]')

ERROR_MESSAGES = {
    "BAD_ID": "invalid identifier (it cannot start with a digit)",
    "BAD_NUMBER": "invalid constant (a number cannot have leading zeros)",
    "OPEN_STRING": "string constant is not closed on the same line",
    "INVALID": "invalid character",
}


class STPosition(ctypes.Structure):
    _fields_ = [("bucket", ctypes.c_int), ("index", ctypes.c_int)]


class SymbolTable:

    def __init__(self):
        name = "symtab.dll" if os.name == "nt" else "libsymtab.so"
        try:
            self.lib = ctypes.CDLL(os.path.join(BASE_DIR, name))
        except OSError:
            sys.exit(f"Cannot load {name}. Compile it from symtab.c (see the top of lexer.py).")
        self.lib.st_create.restype = ctypes.c_void_p
        self.lib.st_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.st_add.restype = STPosition
        self.lib.st_write.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.st_destroy.argtypes = [ctypes.c_void_p]
        self.table = self.lib.st_create()

    def add(self, name, kind):
        pos = self.lib.st_add(self.table, name.encode(), kind)
        return pos.bucket, pos.index

    def write(self, path):
        self.lib.st_write(self.table, path.encode())

    def destroy(self):
        self.lib.st_destroy(self.table)


def load_tokens(path):
    tokens = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                tokens[parts[0]] = int(parts[1])
    return tokens


def scan(source, tokens, st):
    pif = []      # entries: (token, code, ST position or None)
    errors = []
    line = 1
    line_start = 0

    for match in TOKEN_REGEX.finditer(source):
        kind = match.lastgroup
        text = match.group()
        column = match.start() - line_start + 1

        if kind == "NEWLINE":
            line += 1
            line_start = match.end()
        elif kind in ("COMMENT", "SPACE"):
            pass
        elif kind in ERROR_MESSAGES:
            errors.append(f"Lexical error at line {line}, column {column}: {ERROR_MESSAGES[kind]}: {text}")
        elif kind == "NUMBER":
            pif.append((text, CODE_CONSTANT, st.add(text, SYM_CONSTANT)))
        elif kind == "STRING":
            bad = [c for c in text[1:-1] if not STRING_CHAR_REGEX.fullmatch(c)]
            if bad:
                errors.append(f"Lexical error at line {line}, column {column}: "
                              f"invalid character '{bad[0]}' inside string constant: {text}")
            else:
                pif.append((text, CODE_CONSTANT, st.add(text, SYM_CONSTANT)))
        elif kind == "WORD":
            # a reserved word if it is in the token list, otherwise an identifier
            code = tokens.get(text, CODE_IDENTIFIER)
            if code > CODE_CONSTANT:
                pif.append((text, code, None))
            else:
                pif.append((text, CODE_IDENTIFIER, st.add(text, SYM_IDENTIFIER)))
        else:  # OPERATOR or SEPARATOR
            pif.append((text, tokens[text], None))

    return pif, errors


def write_pif(pif, path):
    with open(path, "w") as f:
        f.write(f"Program Internal Form ({len(pif)} entries)\n\n")
        f.write(f"{'token':<24} {'code':<6} ST position\n")
        for text, code, pos in pif:
            position = f"({pos[0]}, {pos[1]})" if pos else "-"
            f.write(f"{text:<24} {code:<6} {position}\n")


def main():
    tokens_file = os.path.join(BASE_DIR, "tokens.txt")
    program_file = os.path.join(BASE_DIR, input("Program file: ").strip())
    if not os.path.isfile(program_file):
        print("File not found:", program_file)
        return

    tokens = load_tokens(tokens_file)
    with open(program_file) as f:
        source = f.read()

    st = SymbolTable()
    pif, errors = scan(source, tokens, st)

    write_pif(pif, os.path.join(BASE_DIR, "PIF.txt"))
    st.write(os.path.join(BASE_DIR, "ST.txt"))
    st.destroy()

    with open(os.path.join(BASE_DIR, "errors.txt"), "w") as f:
        if errors:
            for error in errors:
                print(error)
                f.write(error + "\n")
            print(f"{len(errors)} lexical error(s) found.")
        else:
            print("The program is lexically correct.")
            f.write("No lexical errors.\n")
    print("Output written to PIF.txt, ST.txt and errors.txt")


if __name__ == "__main__":
    main()
