import os
import re

import ply.lex as lex
import ply.yacc as yacc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EPSILON = "epsilon"
SECTION = re.compile(r"^(nonterminals|terminals|start|productions):(.*)$")
PIF_ENTRY = re.compile(r"^(.*\S)\s+(\d+)\s+(\(\d+, \d+\)|-)$")


def read_sections(path):
    sections = {}
    current = None
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            match = SECTION.match(line)
            if match:
                current = match.group(1)
                sections[current] = []
                if match.group(2).strip():
                    sections[current].append(match.group(2).strip())
            elif current is not None:
                sections[current].append(line)
    return sections


class Grammar:

    def __init__(self, path):
        s = read_sections(path)
        self.nonterminals = s["nonterminals"][0].split()
        self.terminals = s["terminals"][0].split()
        self.start = s["start"][0]
        self.productions = []
        for line in s["productions"]:
            left, right = line.split("->", 1)
            for alternative in right.split("|"):
                symbols = alternative.split()
                self.productions.append((left.strip(), [] if symbols == [EPSILON] else symbols))

    def production(self, number):
        left, right = self.productions[number - 1]
        return f"{left} -> {' '.join(right) if right else EPSILON}"


class PIFLexer:

    def __init__(self, pif, names):
        self.pif = pif
        self.names = names
        self.index = 0

    def token(self):
        if self.index == len(self.pif):
            return None
        text, terminal = self.pif[self.index]
        token = lex.LexToken()
        token.type = self.names[terminal]
        token.value = text
        token.lineno = 1
        token.lexpos = self.index
        self.index += 1
        return token


class Parser:

    def __init__(self, grammar):
        self.names = {terminal: f"T{i}" for i, terminal in enumerate(grammar.terminals)}
        self.tokens = list(self.names.values())
        self.start = grammar.start
        self.reductions = []
        for number, (left, right) in enumerate(grammar.productions, 1):
            action = self.action(number)
            action.__doc__ = f"{left} : {' '.join(self.names.get(s, s) for s in right)}"
            setattr(self, f"p_{number:03d}", action)
        self.parser = yacc.yacc(module=self, write_tables=False, debug=False)

    def action(self, number):
        def reduce(p):
            self.reductions.append(number)
        return reduce

    def p_error(self, token):
        if token is None:
            raise SyntaxError("Syntax error: unexpected end of program")
        raise SyntaxError(f"Syntax error at PIF entry {token.lexpos + 1}: unexpected token {token.value}")

    def parse(self, pif):
        self.reductions = []
        self.parser.parse(lexer=PIFLexer(pif, self.names))
        return self.reductions[::-1]


def load_tokens(path):
    tokens = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                tokens[int(parts[1])] = parts[0]
    return tokens


def read_pif(path, tokens):
    pif = []
    with open(path) as f:
        for line in f:
            match = PIF_ENTRY.match(line.rstrip("\n"))
            if match:
                pif.append((match.group(1), tokens[int(match.group(2))]))
    return pif


def write_productions(grammar, productions, path):
    with open(path, "w") as f:
        f.write(f"String of productions ({len(productions)} productions)\n\n")
        f.write(" ".join(map(str, productions)) + "\n\n")
        f.write(f"{'number':<8} production\n")
        for number in productions:
            f.write(f"{number:<8} {grammar.production(number)}\n")


def main():
    pif_file = os.path.join(BASE_DIR, input("PIF file: ").strip())
    if not os.path.isfile(pif_file):
        print("File not found:", pif_file)
        return

    grammar = Grammar(os.path.join(BASE_DIR, "grammar.txt"))
    tokens = load_tokens(os.path.join(BASE_DIR, "tokens.txt"))
    pif = read_pif(pif_file, tokens)
    parser = Parser(grammar)
    output = os.path.join(BASE_DIR, "productions.txt")

    try:
        productions = parser.parse(pif)
    except SyntaxError as error:
        print(error)
        with open(output, "w") as f:
            f.write(f"{error}\n")
        print("Output written to productions.txt")
        return

    write_productions(grammar, productions, output)
    print("The program is syntactically correct.")
    print("Output written to productions.txt")


if __name__ == "__main__":
    main()
