import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from scanner import Scanner

EPS = "ε"

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


def compute_first_follow(
    grammar: Dict[str, List[List[str]]], start_symbol: str
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    first: Dict[str, Set[str]] = {nt: set() for nt in grammar}

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


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.current_type, self.current_lexeme, self.current_line = self._next_token()
        self.errors: List[str] = []
        self.in_panic = False

    def _next_token(self) -> Tuple[str, str, int]:
        token = self.scanner.get_next_token()
        return token[0], token[1], token[2]

    def sym(self) -> str:
        if self.current_type in {"ID", "NUM", "$"}:
            return self.current_type
        return self.current_lexeme

    def report_error(self) -> None:
        self.errors.append(
            f'Syntax error at line {self.current_line}: unexpected token "{self.current_lexeme}"'
        )

    def sync(self, sync_set: Set[str]) -> None:
        while self.sym() != "$" and self.sym() not in sync_set:
            self.current_type, self.current_lexeme, self.current_line = self._next_token()

    def match(self, expected: str, parent: TreeNode, sync_set: Set[str]) -> bool:
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
