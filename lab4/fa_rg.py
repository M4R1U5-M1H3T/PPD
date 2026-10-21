import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EPSILON = "epsilon"
SECTION = re.compile(r"^(nonterminals|terminals|start|classes|productions):(.*)$")


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


def symbol_matches(symbol, ch, classes):
    if symbol in classes:
        return re.fullmatch(classes[symbol], ch) is not None
    return symbol == ch


class RG:

    def __init__(self, nonterminals, terminals, start, productions, classes):
        self.nonterminals = nonterminals
        self.terminals = terminals
        self.start = start
        self.productions = productions
        self.classes = classes

    @staticmethod
    def from_file(path):
        s = read_sections(path)
        productions = {}
        for line in s.get("productions", []):
            left, right = line.split("->")
            for alternative in right.split("|"):
                symbols = alternative.split()
                rhs = () if symbols == [EPSILON] else tuple(symbols)
                productions.setdefault(left.strip(), []).append(rhs)
        classes = {}
        for line in s.get("classes", []):
            name, pattern = line.split(None, 1)
            classes[name] = pattern
        return RG(s["nonterminals"][0].split(), s["terminals"][0].split(), s["start"][0],
                  productions, classes)

    def is_regular(self):
        start_has_epsilon = False
        start_on_right = False
        for left, rights in self.productions.items():
            if left not in self.nonterminals:
                return False
            for rhs in rights:
                if len(rhs) == 0:
                    if left != self.start:
                        return False
                    start_has_epsilon = True
                elif rhs[0] not in self.terminals:
                    return False
                elif len(rhs) == 2:
                    if rhs[1] not in self.nonterminals:
                        return False
                    start_on_right = start_on_right or rhs[1] == self.start
                elif len(rhs) > 2:
                    return False
        return not (start_has_epsilon and start_on_right)

    def __str__(self):
        lines = [f"N = {{{', '.join(self.nonterminals)}}}",
                 f"E = {{{', '.join(self.terminals)}}}",
                 f"S = {self.start}",
                 "P:"]
        for left in self.nonterminals:
            rights = [" ".join(rhs) if rhs else EPSILON for rhs in self.productions.get(left, [])]
            if rights:
                lines.append(f"  {left} -> {' | '.join(rights)}")
        for name, pattern in self.classes.items():
            lines.append(f"  where {name} = {pattern}")
        lines.append("Regular (right-linear): " + ("yes" if self.is_regular() else "no"))
        return "\n".join(lines)


class FA:

    def __init__(self, states, alphabet, initial, finals, transitions, classes):
        self.states = states
        self.alphabet = alphabet
        self.initial = initial
        self.finals = finals
        self.transitions = transitions
        self.classes = classes

    def is_deterministic(self):
        return all(len(targets) == 1 for targets in self.transitions.values())

    def accepts(self, word):
        current = {self.initial}
        for ch in word:
            following = set()
            for (p, a), targets in self.transitions.items():
                if p in current and symbol_matches(a, ch, self.classes):
                    following |= targets
            if not following:
                return False
            current = following
        return bool(current & self.finals)

    def save(self, path):
        with open(path, "w") as f:
            f.write(f"states: {' '.join(self.states)}\n")
            f.write(f"alphabet: {' '.join(self.alphabet)}\n")
            f.write(f"initial: {self.initial}\n")
            f.write(f"finals: {' '.join(s for s in self.states if s in self.finals)}\n")
            if self.classes:
                f.write("classes:\n")
                for name, pattern in self.classes.items():
                    f.write(f"{name} {pattern}\n")
            f.write("transitions:\n")
            for (p, a), targets in self.transitions.items():
                for q in sorted(targets):
                    f.write(f"{p} {a} {q}\n")

    def __str__(self):
        lines = [f"Q  = {{{', '.join(self.states)}}}",
                 f"E  = {{{', '.join(self.alphabet)}}}",
                 f"q0 = {self.initial}",
                 f"F  = {{{', '.join(s for s in self.states if s in self.finals)}}}",
                 "delta:"]
        for (p, a), targets in self.transitions.items():
            lines.append(f"  delta({p}, {a}) = {{{', '.join(sorted(targets))}}}")
        for name, pattern in self.classes.items():
            lines.append(f"  where {name} = {pattern}")
        lines.append("Deterministic: " + ("yes" if self.is_deterministic() else "no"))
        return "\n".join(lines)


def rg_to_fa(rg):
    final = "K"
    while final in rg.nonterminals:
        final += "'"
    transitions = {}
    finals = {final}
    for left, rights in rg.productions.items():
        for rhs in rights:
            if len(rhs) == 0:
                finals.add(left)
            else:
                target = rhs[1] if len(rhs) == 2 else final
                transitions.setdefault((left, rhs[0]), set()).add(target)
    return FA(list(rg.nonterminals) + [final], list(rg.terminals), rg.start,
              finals, transitions, dict(rg.classes))


def main():
    rg = None
    fa = None
    menu = ("\n1. Read RG from file\n2. Transform RG -> FA\n"
            "3. Check a sequence with the FA\n0. Exit")
    while True:
        print(menu)
        option = input("> ").strip()
        if option == "1":
            path = os.path.join(BASE_DIR, input("RG file: ").strip())
            if not os.path.isfile(path):
                print("File not found:", path)
                continue
            rg = RG.from_file(path)
            fa = None
            print(rg)
        elif option == "2":
            if rg is None:
                print("Read an RG first (option 1).")
            elif not rg.is_regular():
                print("The grammar is not regular, it cannot be transformed.")
            else:
                fa = rg_to_fa(rg)
                print(fa)
                name = input("Save to file (leave empty to skip): ").strip()
                if name:
                    fa.save(os.path.join(BASE_DIR, name))
                    print("Saved to", name)
        elif option == "3":
            if fa is None:
                print("Transform an RG first (option 2).")
                continue
            word = input("Sequence: ")
            print("accepted" if fa.accepts(word) else "not accepted")
        elif option == "0":
            break


if __name__ == "__main__":
    main()
