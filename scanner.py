import os
from typing import Optional, List, Tuple, Dict


class Scanner:
    def __init__(self, source: str):
        self.source = source
        self.index = 0
        self.line = 1

        self.tokens_by_line: Dict[int, List[Tuple[str, str]]] = {}
        self.errors: List[Tuple[int, str, str]] = []

        self.eof_reached = False

    def _peek(self) -> Optional[str]:
        if self.index + 1 < len(self.source):
            return self.source[self.index + 1]
        return None

    def _advance(self) -> Optional[str]:
        if self.index >= len(self.source):
            return None

        ch = self.source[self.index]
        self.index += 1

        if ch == "\n":
            self.line += 1

        return ch

    def _current_char(self) -> Optional[str]:
        if self.index < len(self.source):
            return self.source[self.index]
        return None

    def _is_letter(self, ch: str) -> bool:
        return ch.isalpha()

    def _is_digit(self, ch: str) -> bool:
        return ch.isdigit()

    def _is_alnum(self, ch: str) -> bool:
        return ch.isalnum()

def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "input.txt")

    try:
        with open(input_path, "r", encoding="utf-8", newline="") as f:
            source = f.read()
    except OSError:
        print("input.txt was not found.")
        return

    scanner = Scanner(source)