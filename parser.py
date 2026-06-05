import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from scanner import Scanner

# --- Grammar Definition ---
# Epsilon symbol for empty productions
EPS = "ε"

# Grammar as a dictionary: nonterminal -> list of productions (each production is a list of symbols)
GRAMMAR: Dict[str, List[List[str]]] = {
    "Program": [["Declaration-list"]],
    "Declaration-list": [["Declaration", "Declaration-list"], []],
    "Declaration": [["Declaration-initial", "Declaration-prime"]],
    "Declaration-initial": [["Type-specifier", "ID"]],
    "Declaration-prime": [["Fun-declaration-prime"], ["Var-declaration-prime"]],
    "Var-declaration-prime": [[";"], ["[", "NUM", "]", ";"]],
    "Fun-declaration-prime": [["{", "Params", "}", "Compound-stmt"]],
    "Type-specifier": [["int"], ["void"]],
    "Params": [["int", "ID", "Param-prime", "Param-list"], ["void"]],
    "Param-list": [[",", "Param", "Param-list"], []],
    "Param": [["Declaration-initial", "Param-prime"]],
    "Param-prime": [["[", "]"], []],
    "Compound-stmt": [["{", "Declaration-list", "Statement-list", "}"]],
    "Statement-list": [["Statement", "Statement-list"], []],
    "Statement": [["Expression-stmt"], ["Compound-stmt"], ["Selection-stmt"], ["Iteration-stmt"], ["Return-stmt"]],
    "Expression-stmt": [["Expression", ";"], ["break", ";", ";"]],
    "Selection-stmt": [["if", "(", "Expression", ")", "Statement", "else", "Statement"]],
    "Iteration-stmt": [["repeat", "Statement", "until", "(", "Expression", ")"]],
    "Return-stmt": [["return", "Return-stmt-prime"]],
    "Return-stmt-prime": [[";"], ["Expression", ";"]],
    "Expression": [["Simple-expression-zegond"], ["ID", "B"]],
    "B": [["=", "Expression"], ["[", "Expression", "]", "H"], ["Simple-expression-prime"]],
    "H": [["=", "Expression"], ["G", "D", "C"]],
    "Simple-expression-zegond": [["Additive-expression-zegond", "C"]],
    "Simple-expression-prime": [["Additive-expression-prime", "C"]],
    "C": [["Relop", "Additive-expression"], []],
    "Relop": [["<"], ["=="]],
    "Additive-expression": [["Term", "D"]],
    "Additive-expression-prime": [["Term-prime", "D"]],
    "Additive-expression-zegond": [["Term-zegond", "D"]],
    "D": [["Addo", "Term", "D"], []],
    "Addo": [["+"], ["-"]],
    "Term": [["Factor", "G"]],
    "Term-prime": [["Factor-prime", "G"]],
    "Term-zegond": [["Factor-zegond", "G"]],
    "G": [["*", "Factor", "G"], []],
    "Factor": [["(", "Expression", ")"], ["ID", "Var-call-prime"], ["NUM"]],
    "Var-call-prime": [["(", "Args", ")"], ["Var-prime"]],
    "Var-prime": [["[", "Expression", "]"], []],
    "Factor-prime": [["(", "Args", ")"], []],
    "Factor-zegond": [["(", "Expression", ")"], ["NUM"]],
    "Args": [["Arg-list"], []],
    "Arg-list": [["Expression", "Arg-list-prime"]],
    "Arg-list-prime": [[",", "Expression", "Arg-list-prime"], []],
}

# --- FIRST and FOLLOW Sets Computation ---
# Standard algorithm for FIRST and FOLLOW sets used for error recovery (synchronization)
def compute_first_follow(
    grammar: Dict[str, List[List[str]]], start_symbol: str
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    first: Dict[str, Set[str]] = {nt: set() for nt in grammar}
    # Compute FIRST sets iteratively until no change
    changed = True
    while changed:
        changed = False
        for head, productions in grammar.items():
            for prod in productions:
                if not prod:
                    if EPS not in first[head]:
                        first[head].add(EPS)
                        changed = True
                    continue
                nullable = True
                for sym in prod:
                    if sym in grammar:
                        before = len(first[head])
                        first[head] |= (first[sym] - {EPS})
                        if len(first[head]) != before:
                            changed = True
                        if EPS in first[sym]:
                            continue
                        nullable = False
                        break
                    else:
                        if sym not in first[head]:
                            first[head].add(sym)
                            changed = True
                        nullable = False
                        break
                if nullable and EPS not in first[head]:
                    first[head].add(EPS)
                    changed = True
    # Compute FOLLOW sets
    follow: Dict[str, Set[str]] = {nt: set() for nt in grammar}
    follow[start_symbol].add("$")
    changed = True
    while changed:
        changed = False
        for head, productions in grammar.items():
            for prod in productions:
                trailer = follow[head].copy()
                for sym in reversed(prod):
                    if sym in grammar:
                        before = len(follow[sym])
                        follow[sym] |= trailer
                        if len(follow[sym]) != before:
                            changed = True
                        if EPS in first[sym]:
                            trailer = trailer | (first[sym] - {EPS})
                        else:
                            trailer = first[sym] - {EPS}
                    else:
                        trailer = {sym}
    return first, follow

FIRST, FOLLOW = compute_first_follow(GRAMMAR, "Program")

# --- Parse Tree Node Definition ---
@dataclass
class TreeNode:
    label: str
    children: List["TreeNode"]

    def __init__(self, label: str):
        self.label = label
        self.children = []

    def add(self, child: "TreeNode") -> "TreeNode":
        self.children.append(child)
        return child

# --- Recursive Descent Parser with Panic Mode Error Recovery ---
"""
The parser consumes tokens from the scanner and builds a parse tree.
It uses the computed FOLLOW sets for synchronization on errors.
"""
class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.current_type, self.current_lexeme, self.current_line = self._next_token()
        self.errors: List[str] = []
        self.in_panic = False  # flag to avoid cascading error messages
        self.root = None

    def _next_token(self) -> Tuple[str, str, int]:
        token = self.scanner.get_next_token()
        return token[0], token[1], token[2]

    def sym(self) -> str:
        """Return the current symbol (token type or lexeme) used for lookahead decisions."""
        if self.current_type in {"ID", "NUM", "$"}:
            return self.current_type
        return self.current_lexeme

    def report_error(self) -> None:
        """Record a syntax error message."""
        self.errors.append(
            f'Syntax error at line {self.current_line}: unexpected token "{self.current_lexeme}"'
        )

    def sync(self, sync_set: Set[str]) -> None:
        """Skip tokens until we find one in the given synchronisation set (panic mode)."""
        while self.sym() != "$" and self.sym() not in sync_set:
            self.current_type, self.current_lexeme, self.current_line = self._next_token()

    def match(self, expected: str, parent: TreeNode, sync_set: Set[str]) -> bool:
        """Try to match the expected terminal. On failure, report error, synchronize, and return False."""
        if self.sym() == expected:
            parent.add(TreeNode(expected))
            self.current_type, self.current_lexeme, self.current_line = self._next_token()
            self.in_panic = False
            return True

        if not self.in_panic:
            self.report_error()
            self.in_panic = True

        if self.sym() not in sync_set:
            self.sync(sync_set)

        return False

    # --- Parsing methods: each nonterminal gets a `parse_xxx` method ---
    # They follow the grammar structure and build the parse tree via parent nodes.

    def parse(self) -> TreeNode:
        self.root = TreeNode("Program")
        self.parse_declaration_list(self.root)
        return self.root

    def parse_declaration_list(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Declaration-list"))
        if self.sym() in {"int", "void"}:
            self.parse_declaration(node)
            self.parse_declaration_list(node)
        elif self.sym() in FOLLOW["Declaration-list"] or self.sym() == "$":
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Declaration-list"])
            node.add(TreeNode(EPS))
        return node

    def parse_declaration(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Declaration"))
        self.parse_declaration_initial(node)
        self.parse_declaration_prime(node)
        return node

    def parse_declaration_initial(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Declaration-initial"))
        self.parse_type_specifier(node)
        self.match("ID", node, FOLLOW["Declaration-initial"])
        return node

    def parse_declaration_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Declaration-prime"))
        if self.sym() == "{":
            self.parse_fun_declaration_prime(node)
        elif self.sym() in {";", "["}:
            self.parse_var_declaration_prime(node)
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Declaration-prime"])
        return node

    def parse_var_declaration_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Var-declaration-prime"))
        if self.sym() == ";":
            self.match(";", node, FOLLOW["Var-declaration-prime"])
        elif self.sym() == "[":
            self.match("[", node, FOLLOW["Var-declaration-prime"])
            self.match("NUM", node, FOLLOW["Var-declaration-prime"])
            self.match("]", node, FOLLOW["Var-declaration-prime"])
            self.match(";", node, FOLLOW["Var-declaration-prime"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Var-declaration-prime"])
        return node

    def parse_fun_declaration_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Fun-declaration-prime"))
        self.match("{", node, FOLLOW["Fun-declaration-prime"])
        self.parse_params(node)
        self.match("}", node, FOLLOW["Fun-declaration-prime"])
        self.parse_compound_stmt(node)
        return node

    def parse_type_specifier(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Type-specifier"))
        if self.sym() in {"int", "void"}:
            self.match(self.sym(), node, FOLLOW["Type-specifier"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Type-specifier"])
        return node

    def parse_params(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Params"))
        if self.sym() == "int":
            self.match("int", node, FOLLOW["Params"])
            self.match("ID", node, FOLLOW["Params"])
            self.parse_param_prime(node)
            self.parse_param_list(node)
        elif self.sym() == "void":
            self.match("void", node, FOLLOW["Params"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Params"])
        return node

    def parse_param_list(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Param-list"))
        if self.sym() == ",":
            self.match(",", node, FOLLOW["Param-list"])
            self.parse_param(node)
            self.parse_param_list(node)
        elif self.sym() in FOLLOW["Param-list"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Param-list"])
            node.add(TreeNode(EPS))
        return node

    def parse_param(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Param"))
        self.parse_declaration_initial(node)
        self.parse_param_prime(node)
        return node

    def parse_param_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Param-prime"))
        if self.sym() == "[":
            self.match("[", node, FOLLOW["Param-prime"])
            self.match("]", node, FOLLOW["Param-prime"])
        elif self.sym() in FOLLOW["Param-prime"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Param-prime"])
            node.add(TreeNode(EPS))
        return node

    def parse_compound_stmt(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Compound-stmt"))
        self.match("{", node, FOLLOW["Compound-stmt"])
        self.parse_declaration_list(node)
        self.parse_statement_list(node)
        self.match("}", node, FOLLOW["Compound-stmt"])
        return node

    def parse_statement_list(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Statement-list"))
        if self.sym() in {"if", "{", "repeat", "break", "return", "ID", "NUM", "("}:
            self.parse_statement(node)
            self.parse_statement_list(node)
        elif self.sym() in FOLLOW["Statement-list"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Statement-list"])
            node.add(TreeNode(EPS))
        return node

    def parse_statement(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Statement"))
        if self.sym() == "{":
            self.parse_compound_stmt(node)
        elif self.sym() == "if":
            self.parse_selection_stmt(node)
        elif self.sym() == "repeat":
            self.parse_iteration_stmt(node)
        elif self.sym() == "return":
            self.parse_return_stmt(node)
        elif self.sym() == "break" or self.sym() in {"ID", "NUM", "("}:
            self.parse_expression_stmt(node)
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Statement"])
        return node

    def parse_expression_stmt(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Expression-stmt"))
        if self.sym() == "break":
            self.match("break", node, FOLLOW["Expression-stmt"])
            self.match(";", node, FOLLOW["Expression-stmt"])
            self.match(";", node, FOLLOW["Expression-stmt"])
        else:
            self.parse_expression(node)
            self.match(";", node, FOLLOW["Expression-stmt"])
        return node

    def parse_selection_stmt(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Selection-stmt"))
        self.match("if", node, FOLLOW["Selection-stmt"])
        self.match("(", node, FOLLOW["Selection-stmt"])
        self.parse_expression(node)
        self.match(")", node, FOLLOW["Selection-stmt"])
        self.parse_statement(node)
        self.match("else", node, FOLLOW["Selection-stmt"])
        self.parse_statement(node)
        return node

    def parse_iteration_stmt(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Iteration-stmt"))
        self.match("repeat", node, FOLLOW["Iteration-stmt"])
        self.parse_statement(node)
        self.match("until", node, FOLLOW["Iteration-stmt"])
        self.match("(", node, FOLLOW["Iteration-stmt"])
        self.parse_expression(node)
        self.match(")", node, FOLLOW["Iteration-stmt"])
        return node

    def parse_return_stmt(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Return-stmt"))
        self.match("return", node, FOLLOW["Return-stmt"])
        self.parse_return_stmt_prime(node)
        return node

    def parse_return_stmt_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Return-stmt-prime"))
        if self.sym() == ";":
            self.match(";", node, FOLLOW["Return-stmt-prime"])
        elif self.sym() in {"ID", "NUM", "("}:
            self.parse_expression(node)
            self.match(";", node, FOLLOW["Return-stmt-prime"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Return-stmt-prime"])
        return node

    def parse_expression(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Expression"))
        if self.sym() in {"NUM", "("}:
            self.parse_simple_expression_zegond(node)
        elif self.sym() == "ID":
            self.match("ID", node, FOLLOW["Expression"])
            self.parse_B(node)
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Expression"])
        return node

    def parse_B(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("B"))
        if self.sym() == "=":
            self.match("=", node, FOLLOW["B"])
            self.parse_expression(node)
        elif self.sym() == "[":
            self.match("[", node, FOLLOW["B"])
            self.parse_expression(node)
            self.match("]", node, FOLLOW["B"])
            self.parse_H(node)
        else:
            self.parse_simple_expression_prime(node)
        return node

    def parse_H(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("H"))
        if self.sym() == "=":
            self.match("=", node, FOLLOW["H"])
            self.parse_expression(node)
        else:
            self.parse_G(node)
            self.parse_D(node)
            self.parse_C(node)
        return node

    def parse_simple_expression_zegond(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Simple-expression-zegond"))
        self.parse_additive_expression_zegond(node)
        self.parse_C(node)
        return node

    def parse_simple_expression_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Simple-expression-prime"))
        self.parse_additive_expression_prime(node)
        self.parse_C(node)
        return node

    def parse_C(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("C"))
        if self.sym() in {"<", "=="}:
            self.parse_Relop(node)
            self.parse_additive_expression(node)
        elif self.sym() in FOLLOW["C"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["C"])
            node.add(TreeNode(EPS))
        return node

    def parse_Relop(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Relop"))
        if self.sym() in {"<", "=="}:
            self.match(self.sym(), node, FOLLOW["Relop"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Relop"])
        return node

    def parse_additive_expression(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Additive-expression"))
        self.parse_term(node)
        self.parse_D(node)
        return node

    def parse_additive_expression_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Additive-expression-prime"))
        self.parse_term_prime(node)
        self.parse_D(node)
        return node

    def parse_additive_expression_zegond(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Additive-expression-zegond"))
        self.parse_term_zegond(node)
        self.parse_D(node)
        return node

    def parse_D(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("D"))
        if self.sym() in {"+", "-"}:
            self.parse_Addo(node)
            self.parse_term(node)
            self.parse_D(node)
        elif self.sym() in FOLLOW["D"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["D"])
            node.add(TreeNode(EPS))
        return node

    def parse_Addo(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Addo"))
        if self.sym() in {"+", "-"}:
            self.match(self.sym(), node, FOLLOW["Addo"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Addo"])
        return node

    def parse_term(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Term"))
        self.parse_factor(node)
        self.parse_G(node)
        return node

    def parse_term_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Term-prime"))
        self.parse_factor_prime(node)
        self.parse_G(node)
        return node

    def parse_term_zegond(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Term-zegond"))
        self.parse_factor_zegond(node)
        self.parse_G(node)
        return node

    def parse_G(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("G"))
        if self.sym() == "*":
            self.match("*", node, FOLLOW["G"])
            self.parse_factor(node)
            self.parse_G(node)
        elif self.sym() in FOLLOW["G"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["G"])
            node.add(TreeNode(EPS))
        return node

    def parse_factor(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Factor"))
        if self.sym() == "(":
            self.match("(", node, FOLLOW["Factor"])
            self.parse_expression(node)
            self.match(")", node, FOLLOW["Factor"])
        elif self.sym() == "ID":
            self.match("ID", node, FOLLOW["Factor"])
            self.parse_var_call_prime(node)
        elif self.sym() == "NUM":
            self.match("NUM", node, FOLLOW["Factor"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Factor"])
        return node

    def parse_var_call_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Var-call-prime"))
        if self.sym() == "(":
            self.match("(", node, FOLLOW["Var-call-prime"])
            self.parse_args(node)
            self.match(")", node, FOLLOW["Var-call-prime"])
        else:
            self.parse_var_prime(node)
        return node

    def parse_var_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Var-prime"))
        if self.sym() == "[":
            self.match("[", node, FOLLOW["Var-prime"])
            self.parse_expression(node)
            self.match("]", node, FOLLOW["Var-prime"])
        elif self.sym() in FOLLOW["Var-prime"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Var-prime"])
            node.add(TreeNode(EPS))
        return node

    def parse_factor_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Factor-prime"))
        if self.sym() == "(":
            self.match("(", node, FOLLOW["Factor-prime"])
            self.parse_args(node)
            self.match(")", node, FOLLOW["Factor-prime"])
        elif self.sym() in FOLLOW["Factor-prime"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Factor-prime"])
            node.add(TreeNode(EPS))
        return node

    def parse_factor_zegond(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Factor-zegond"))
        if self.sym() == "(":
            self.match("(", node, FOLLOW["Factor-zegond"])
            self.parse_expression(node)
            self.match(")", node, FOLLOW["Factor-zegond"])
        elif self.sym() == "NUM":
            self.match("NUM", node, FOLLOW["Factor-zegond"])
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Factor-zegond"])
        return node

    def parse_args(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Args"))
        if self.sym() in {"ID", "NUM", "("}:
            self.parse_arg_list(node)
        elif self.sym() in FOLLOW["Args"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Args"])
            node.add(TreeNode(EPS))
        return node

    def parse_arg_list(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Arg-list"))
        if self.sym() in {"ID", "NUM", "("}:
            self.parse_expression(node)
            self.parse_arg_list_prime(node)
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Arg-list"])
        return node

    def parse_arg_list_prime(self, parent: TreeNode) -> TreeNode:
        node = parent.add(TreeNode("Arg-list-prime"))
        if self.sym() == ",":
            self.match(",", node, FOLLOW["Arg-list-prime"])
            self.parse_expression(node)
            self.parse_arg_list_prime(node)
        elif self.sym() in FOLLOW["Arg-list-prime"]:
            node.add(TreeNode(EPS))
        else:
            if not self.in_panic:
                self.report_error()
                self.in_panic = True
            self.sync(FOLLOW["Arg-list-prime"])
            node.add(TreeNode(EPS))
        return node

# --- Tree Rendering ---
def render_tree(root: TreeNode) -> str:
    """Convert the parse tree into a textual tree representation."""
    lines: List[str] = []

    def walk(node: TreeNode, prefix: str = "", is_last: bool = True, is_root: bool = False) -> None:
        if is_root:
            lines.append(node.label)
        else:
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + node.label)

        if node.children:
            next_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(node.children):
                walk(child, next_prefix, i == len(node.children) - 1, False)

    walk(root, is_root=True)
    return "\n".join(lines) + "\n"


def write_parser_outputs(parser: Parser, out_dir: str) -> None:
    parse_tree_path = os.path.join(out_dir, "parse_tree.txt")
    syntax_errors_path = os.path.join(out_dir, "syntax_errors.txt")

    # Parse tree
    if parser.root is not None:
        tree_str = render_tree(parser.root)
        with open(parse_tree_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(tree_str)

    # Syntax errors
    with open(syntax_errors_path, "w", encoding="utf-8", newline="\n") as f:
        if not parser.errors:
            f.write("There is no syntax error.\n")
        else:
            f.write("\n".join(parser.errors) + "\n")
            
# --- Main Driver ---
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
    parser = Parser(scanner)
    parser.parse()
    write_parser_outputs(parser, base_dir)

if __name__ == "__main__":
    main()