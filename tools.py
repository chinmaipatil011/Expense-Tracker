import ast, operator
from langchain_core.tools import tool
from db import insert_expense, summarize
from pydantic import BaseModel, StrictInt, StrictFloat
from typing import Union

_ALLOWED={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
          ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow,
          ast.USub:operator.neg,ast.UAdd:operator.pos}
def safe_calculate(expression):
    if not isinstance(expression,str) or len(expression)>120:
        raise ValueError("Expression must be a string under 120 characters.")
    def walk(node):
        if isinstance(node,ast.Expression): return walk(node.body)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float): return node.value
        if isinstance(node,ast.BinOp) and type(node.op) in _ALLOWED:
            if isinstance(node.op,ast.Pow) and abs(walk(node.right))>8: raise ValueError("Exponent too large.")
            value=_ALLOWED[type(node.op)](walk(node.left),walk(node.right))
            if abs(value)>1e12: raise ValueError("Result too large.")
            return value
        if isinstance(node,ast.UnaryOp) and type(node.op) in _ALLOWED: return _ALLOWED[type(node.op)](walk(node.operand))
        raise ValueError("Only basic arithmetic is allowed.")
    try: return walk(ast.parse(expression,mode="eval"))
    except (SyntaxError,ZeroDivisionError,OverflowError) as exc: raise ValueError("Invalid arithmetic expression.") from exc

from pydantic import BaseModel
from typing import Any

class AddExpenseInput(BaseModel):
    amount: Any
    category: str
    note: str = ""


@tool(args_schema=AddExpenseInput)
def add_expense(amount: float, category: str, note: str = "") -> dict:
    """Save one expense. Amount must be positive; category must not be empty."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0 or amount > 1e9:
        raise ValueError("Amount must be a positive number no greater than 1,000,000,000.")

    if not isinstance(category, str) or not category.strip() or len(category) > 80:
        raise ValueError("Category must be non-empty and at most 80 characters.")

    if not isinstance(note, str) or len(note) > 300:
        raise ValueError("Note must be at most 300 characters.")

    return insert_expense(round(float(amount), 2), category, note)


@tool
def get_expense_summary(days: int) -> dict:
    """Get expense totals grouped by category for the past number of days (1 to 3650)."""
    if isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=3650:
        raise ValueError("Days must be a whole number from 1 to 3650.")
    return summarize(days)

@tool
def calculate(expression: str) -> str:
    """Safely calculate basic arithmetic, for example '(45 + 12) * 2'. Never use Python eval."""
    return str(safe_calculate(expression))

TOOL_LIST=[add_expense,get_expense_summary,calculate]
TOOL_MAP={t.name:t for t in TOOL_LIST}
