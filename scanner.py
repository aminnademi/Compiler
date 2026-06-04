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

    """
    Main scanner routine.
    It skips whitespace and comments, recognizes the next valid token,
    and reports lexical errors in panic style so scanning can continue.
    When the input ends, it returns the special EOF token "$".
    """

    def get_next_token(self) -> Tuple[str, str, int]:
        if self.eof_reached:
            return "$", "$", self.line

        while self.index < len(self.source):
            ch = self._current_char()

            if ch in self.WHITESPACE:
                self._advance()
                continue

            # Handle stray "*/" before treating "/" as a normal symbol.
            if ch == "*" and self._peek() == "/":
                line_no = self.line
                self._advance()
                self._advance()
                self._add_error(line_no, "*/", "Unmatched comment")
                continue

            # Comment handling: consume everything until "*/" or EOF.
            if ch == "/" and self._peek() == "*":
                comment_start_line = self.line
                comment_text = []
                comment_text.append(self._advance())  # /
                comment_text.append(self._advance())  # *

                prev = ""
                while self.index < len(self.source):
                    c = self._current_char()
                    comment_text.append(self._advance())
                    if prev == "*" and c == "/":
                        break
                    prev = c
                else:
                    thrown = "".join(comment_text)
                    if len(thrown) > 7:
                        thrown = thrown[:7] + "..."
                    self._add_error(comment_start_line, thrown, "Unclosed comment")
                    self.eof_reached = True
                    return "$", "$", self.line

                continue

            # Identifiers and keywords start with a letter and can continue with letters or digits.
            if self._is_letter(ch):
                start_line = self.line
                lexeme = []
                while self.index < len(self.source) and self._is_alnum(self._current_char()):
                    lexeme.append(self._advance())

                token = "".join(lexeme)
                if token in self.KEYWORD_SET:
                    return "KEYWORD", token, start_line

                self._add_symbol(token)
                return "ID", token, start_line

            # Numbers are simple digit sequences, but things like 123abc are
            # invalid numbers and must be discarded as one error, not split.
            if self._is_digit(ch):
                start_line = self.line
                lexeme = []
                while self.index < len(self.source) and self._is_digit(self._current_char()):
                    lexeme.append(self._advance())

                token = "".join(lexeme)

                if self.index < len(self.source) and self._is_letter(self._current_char()):
                    while self.index < len(self.source) and self._is_alnum(self._current_char()):
                        lexeme.append(self._advance())
                    bad = "".join(lexeme)
                    self._add_error(start_line, bad, "Invalid number")
                    continue

                return "NUM", token, start_line

            # Two-character symbols are checked before single-character symbols.
            if ch == "=" and self._peek() == "=":
                start_line = self.line
                self._advance()
                self._advance()
                return "SYMBOL", "==", start_line

            if ch == ">" and self._peek() == "=":
                start_line = self.line
                self._advance()
                self._advance()
                return "SYMBOL", ">=", start_line

            if ch in self.SYMBOLS:
                start_line = self.line
                self._advance()
                return "SYMBOL", ch, start_line

            # Any other character is simply an invalid input and is skipped.
            start_line = self.line
            bad_char = self._advance()
            self._add_error(start_line, bad_char if bad_char is not None else "", "Invalid input")

        self.eof_reached = True
        return "$", "$", self.line

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