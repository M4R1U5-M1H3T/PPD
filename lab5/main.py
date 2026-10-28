import ctypes
import os
import string
import sys

from fa import FA

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CODE_IDENTIFIER = 0
CODE_CONSTANT = 1
SYM_IDENTIFIER = 0
SYM_CONSTANT = 1

WORD_CHARS = string.ascii_letters + string.digits + "_"


class STPosition(ctypes.Structure):
    _fields_ = [("bucket", ctypes.c_int), ("index", ctypes.c_int)]


class SymbolTable:

    def __init__(self):
        name = "symtab.dll" if os.name == "nt" else "libsymtab.so"
        try:
            self.lib = ctypes.CDLL(os.path.join(BASE_DIR, name))
        except OSError:
            sys.exit(f"Cannot load {name}. Compile it from symtab.c.")
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


class Scanner:

    def __init__(self, tokens, st):
        self.tokens = tokens
        self.st = st
        self.fa_identifier = FA(os.path.join(BASE_DIR, "fa_identifier.txt"))
        self.fa_number = FA(os.path.join(BASE_DIR, "fa_number.txt"))
        self.fa_string = FA(os.path.join(BASE_DIR, "fa_string.txt"))
        self.pif = []
        self.errors = []

    def error(self, line, column, message, text):
        self.errors.append(f"Lexical error at line {line}, column {column}: {message}: {text}")

    def add_identifier(self, text):
        self.pif.append((text, CODE_IDENTIFIER, self.st.add(text, SYM_IDENTIFIER)))

    def add_constant(self, text):
        self.pif.append((text, CODE_CONSTANT, self.st.add(text, SYM_CONSTANT)))

    def scan(self, source):
        line = 1
        line_start = 0
        i = 0
        while i < len(source):
            ch = source[i]
            column = i - line_start + 1
            if ch == "\n":
                line += 1
                line_start = i + 1
                i += 1
            elif ch in " \t\r":
                i += 1
            elif source.startswith("//", i):
                end = source.find("\n", i)
                i = len(source) if end == -1 else end
            elif ch in WORD_CHARS:
                end = i
                while end < len(source) and source[end] in WORD_CHARS:
                    end += 1
                text = source[i:end]
                if self.fa_identifier.accepts(text):
                    code = self.tokens.get(text, CODE_IDENTIFIER)
                    if code > CODE_CONSTANT:
                        self.pif.append((text, code, None))
                    else:
                        self.add_identifier(text)
                elif self.fa_number.accepts(text):
                    self.add_constant(text)
                elif text.isdigit():
                    self.error(line, column, "invalid constant (a number cannot have leading zeros)", text)
                else:
                    self.error(line, column, "invalid identifier", text)
                i = end
            elif ch == '"':
                length = self.fa_string.longest_prefix(source, i)
                if length:
                    self.add_constant(source[i:i + length])
                    i += length
                else:
                    line_end = source.find("\n", i)
                    if line_end == -1:
                        line_end = len(source)
                    close = source.find('"', i + 1, line_end)
                    if close == -1:
                        self.error(line, column, "string constant is not closed on the same line",
                                   source[i:line_end])
                        i = line_end
                    else:
                        self.error(line, column, "invalid character inside string constant",
                                   source[i:close + 1])
                        i = close + 1
            elif source[i:i + 2] in self.tokens:
                self.pif.append((source[i:i + 2], self.tokens[source[i:i + 2]], None))
                i += 2
            elif ch in self.tokens:
                self.pif.append((ch, self.tokens[ch], None))
                i += 1
            else:
                self.error(line, column, "invalid character", ch)
                i += 1


def load_tokens(path):
    tokens = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                tokens[parts[0]] = int(parts[1])
    return tokens


def write_pif(pif, path):
    with open(path, "w") as f:
        f.write(f"Program Internal Form ({len(pif)} entries)\n\n")
        f.write(f"{'token':<24} {'code':<6} ST position\n")
        for text, code, pos in pif:
            position = f"({pos[0]}, {pos[1]})" if pos else "-"
            f.write(f"{text:<24} {code:<6} {position}\n")


def main():
    program_file = os.path.join(BASE_DIR, input("Program file: ").strip())
    if not os.path.isfile(program_file):
        print("File not found:", program_file)
        return

    tokens = load_tokens(os.path.join(BASE_DIR, "tokens.txt"))
    with open(program_file) as f:
        source = f.read()

    st = SymbolTable()
    scanner = Scanner(tokens, st)
    scanner.scan(source)

    write_pif(scanner.pif, os.path.join(BASE_DIR, "PIF.txt"))
    st.write(os.path.join(BASE_DIR, "ST.txt"))
    st.destroy()

    with open(os.path.join(BASE_DIR, "errors.txt"), "w") as f:
        if scanner.errors:
            for error in scanner.errors:
                print(error)
                f.write(error + "\n")
            print(f"{len(scanner.errors)} lexical error(s) found.")
        else:
            print("The program is lexically correct.")
            f.write("No lexical errors.\n")
    print("Output written to PIF.txt, ST.txt and errors.txt")


if __name__ == "__main__":
    main()
