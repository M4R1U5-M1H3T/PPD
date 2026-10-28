import re

SECTION = re.compile(r"^(states|alphabet|initial|finals|classes|transitions):(.*)$")


class FA:

    def __init__(self, path):
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
                    sections[current] = [match.group(2).strip()] if match.group(2).strip() else []
                elif current is not None:
                    sections[current].append(line)
        self.initial = sections["initial"][0]
        self.finals = set(sections["finals"][0].split())
        self.classes = {}
        for line in sections.get("classes", []):
            name, pattern = line.split(None, 1)
            self.classes[name] = re.compile(pattern)
        self.transitions = {}
        for line in sections["transitions"]:
            p, a, q = line.split()
            self.transitions.setdefault(p, []).append((a, q))

    def matches(self, symbol, ch):
        if symbol in self.classes:
            return self.classes[symbol].fullmatch(ch) is not None
        return symbol == ch

    def step(self, states, ch):
        return {q for p in states for a, q in self.transitions.get(p, []) if self.matches(a, ch)}

    def longest_prefix(self, text, start):
        states = {self.initial}
        length = 0
        i = start
        while states and i < len(text):
            states = self.step(states, text[i])
            i += 1
            if states & self.finals:
                length = i - start
        return length

    def accepts(self, word):
        return len(word) > 0 and self.longest_prefix(word, 0) == len(word)
