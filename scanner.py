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