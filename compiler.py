import os
from scanner import Scanner, write_scanner_outputs
from parser import Parser, write_parser_outputs

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "input.txt")

    try:
        with open(input_path, "r", encoding="utf-8", newline="") as f:
            source = f.read()
    except OSError:
        print("input.txt was not found.")
        return

    # 1. Lexical analysis
    scanner = Scanner(source)
    scanner.scan_all()
    write_scanner_outputs(scanner, base_dir)

    # 2. Syntax analysis
    parser = Parser(Scanner(source))
    parser.parse()
    write_parser_outputs(parser, base_dir)

if __name__ == "__main__":
    main()