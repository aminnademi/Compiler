import os
from typing import Optional, List, Tuple, Dict


class Scanner:
    KEYWORDS = ["if", "else", "void", "int", "repeat", "break", "until", "return"]
    KEYWORD_SET = set(KEYWORDS)

    SYMBOLS = {
        ";", ":", ",", "[", "]", "(", ")", "{", "}", "+", "-", "*", "=", "<", ">", "/"
    }

    WHITESPACE = {" ", "\n", "\r", "\t", "\v", "\f"}

    def __init__(self, source: str):
        self.source = source
        self.index = 0
        self.line = 1
        self.eof_reached = False

        # Output buffers
        self.tokens_by_line: Dict[int, List[Tuple[str, str]]] = {}
        self.errors: List[Tuple[int, str, str]] = []

        # Symbol table starts with the reserved keywords in the required order.
        self.symbol_table: List[str] = self.KEYWORDS.copy()
        self.symbol_set = set(self.KEYWORDS)

    """
    Small input helpers: one character lookahead, one-character advance, 
    and a few utility checks for readability.
    """
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
    
    def _add_token(self, line_no: int, token_type: str, token_lexeme: str) -> None:
        if line_no not in self.tokens_by_line:
            self.tokens_by_line[line_no] = []
        self.tokens_by_line[line_no].append((token_type, token_lexeme))

    def _add_error(self, line_no: int, thrown: str, message: str) -> None:
        self.errors.append((line_no, thrown, message))

    def _add_symbol(self, lexeme: str) -> None:
        if lexeme not in self.symbol_set:
            self.symbol_set.add(lexeme)
            self.symbol_table.append(lexeme)

def main() -> None:
    # The scanner reads input.txt from the same folder as this script.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "input.txt")

    try:
        with open(input_path, "r", encoding="utf-8", newline="") as f:
            source = f.read()
    except OSError:
        print("input.txt was not found.")
        return

    scanner = Scanner(source)