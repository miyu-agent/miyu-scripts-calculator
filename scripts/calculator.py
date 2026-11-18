#!/usr/bin/env python3
# Display name: Calculator
# 显示名称：计算器
# Description: Evaluate arithmetic exactly: + - * / // % ^, trig, logs, roots, factorial, gcd, comb and more. Integers stay exact; no symbolic math.
# 描述：算一个或几个算式：四则、乘方、三角、对数、开方、阶乘、组合数等，整数照精确值算，不做符号运算。
# Timeout: 20
# Need load: no
# Clicall: yes
# Parameters:
# {"type": "object", "properties": {
#   "expression": {"type": "string", "description": "One expression, or several separated by ; or new lines. ^ and ** are power. Functions: sin cos tan asin acos atan atan2 sinh cosh tanh sqrt cbrt abs ln log(x[, base]) log2 log10 exp floor ceil round(x[, digits]) trunc factorial gcd lcm comb perm min max hypot degrees radians. Constants: pi e tau inf."},
#   "angle": {"type": "string", "enum": ["rad", "deg"], "description": "Unit for trig functions. Default rad."}
# }, "required": ["expression"]}

import ast
import json
import math
import operator
import sys

MAX_EXPRESSION = 4000
MAX_INT_BITS = 100_000   # 结果超过约 3 万位十进制的不算
MAX_FACTORIAL = 5000

CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}


class Failure(Exception):
    pass


def check_int(value):
    if isinstance(value, int) and value.bit_length() > MAX_INT_BITS:
        raise Failure("结果太大（超过约 3 万位）")
    return value


def power(base, exponent):
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        if base not in (0, 1, -1) and exponent * max(abs(base).bit_length() - 1, 1) > MAX_INT_BITS:
            raise Failure("结果太大（超过约 3 万位）")
        return base ** exponent
    try:
        result = float(base) ** float(exponent)
    except ZeroDivisionError:
        raise Failure("0 不能取负数次方") from None
    except OverflowError:
        raise Failure("结果超出浮点数范围") from None
    if isinstance(result, complex):
        raise Failure("负数的非整数次方是复数，这里不算")
    return result


def divide(a, b):
    if b == 0:
        raise Failure("除以零")
    if isinstance(a, int) and isinstance(b, int) and a % b == 0:
        return a // b
    return a / b


def floordiv(a, b):
    if b == 0:
        raise Failure("除以零")
    return a // b


def modulo(a, b):
    if b == 0:
        raise Failure("对零取余")
    return a % b


BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: divide, ast.FloorDiv: floordiv, ast.Mod: modulo, ast.Pow: power}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def make_functions(degrees):
    to_rad = math.radians if degrees else (lambda x: x)
    from_rad = math.degrees if degrees else (lambda x: x)

    def log(x, base=None):
        return math.log(x) if base is None else math.log(x, base)

    def rounded(x, digits=0):
        # 四舍五入（.5 远离零），不是 Python 的银行家舍入
        # 浮点数的指数在 ±308 以内，位数再多舍入不出别的结果，先拦下，免得算巨大的 10 的幂
        if abs(digits) > 308:
            raise Failure("round 的位数要在 -308 到 308 之间")
        factor = 10 ** int(digits)
        value = math.floor(abs(x) * factor + 0.5) / factor
        value = math.copysign(value, x)
        return int(value) if digits <= 0 else value

    def factorial(n):
        if not float(n).is_integer() or n < 0:
            raise Failure("阶乘只算非负整数")
        if n > MAX_FACTORIAL:
            raise Failure(f"阶乘只算到 {MAX_FACTORIAL}!")
        return math.factorial(int(n))

    def comb(n, k):
        if isinstance(n, int) and isinstance(k, int) and 0 <= k <= n:
            m = min(k, n - k)
            # C(n, m) ≥ (n/m)^m：下界就超了上限的，不去算
            if m > 0 and m * (math.log2(n) - math.log2(m)) > MAX_INT_BITS:
                raise Failure("结果太大（超过约 3 万位）")
        return math.comb(n, k)

    def perm(n, k=None):
        if isinstance(n, int) and n >= 0 and (k is None or isinstance(k, int) and 0 <= k <= n):
            m = min(n if k is None else k, n // 2)
            # 前 m 个因子都大于 n/2，P(n, k) > (n/2)^m：下界就超了上限的，不去算
            if m > 0 and m * (math.log2(n) - 1) > MAX_INT_BITS:
                raise Failure("结果太大（超过约 3 万位）")
        return math.perm(n, k)

    def lcm(*values):
        # 两两累乘着算、每步查位数：参数都在上限内，每一步的结果至多两倍上限
        result = 1
        for value in values:
            result = check_int(math.lcm(result, value))
        return result

    return {
        "sin": lambda x: math.sin(to_rad(x)), "cos": lambda x: math.cos(to_rad(x)),
        "tan": lambda x: math.tan(to_rad(x)),
        "asin": lambda x: from_rad(math.asin(x)), "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)), "atan2": lambda y, x: from_rad(math.atan2(y, x)),
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "sqrt": lambda x: math.isqrt(x) if isinstance(x, int) and x >= 0 and math.isqrt(x) ** 2 == x else math.sqrt(x),
        "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
        "abs": abs, "ln": math.log, "log": log, "log2": math.log2, "log10": math.log10,
        "exp": math.exp, "floor": math.floor, "ceil": math.ceil, "round": rounded, "trunc": math.trunc,
        "factorial": factorial, "gcd": math.gcd, "lcm": lcm, "comb": comb, "perm": perm,
        "min": min, "max": max, "hypot": math.hypot, "degrees": math.degrees, "radians": math.radians,
    }


def evaluate(node, functions):
    if isinstance(node, ast.Expression):
        return evaluate(node.body, functions)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise Failure(f"不认识的名字：{node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left = evaluate(node.left, functions)
        right = evaluate(node.right, functions)
        return check_int(BINARY[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](evaluate(node.operand, functions))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        func = functions.get(node.func.id)
        if func is None:
            raise Failure(f"不认识的函数：{node.func.id}")
        args = [evaluate(arg, functions) for arg in node.args]
        try:
            return check_int(func(*args))
        except TypeError:
            raise Failure(f"{node.func.id} 的参数个数或类型不对") from None
        except ValueError:
            raise Failure(f"{node.func.id} 的参数超出定义域") from None
        except OverflowError:
            raise Failure(f"{node.func.id} 的结果超出浮点数范围") from None
    raise Failure(f"不支持的写法：{ast.unparse(node) if hasattr(ast, 'unparse') else type(node).__name__}")


def show(value):
    if isinstance(value, int):
        text = str(value)
        return text if len(text) <= 60 else f"{text}（{len(text)} 位）"
    if math.isinf(value) or math.isnan(value):
        return str(value)
    # 浮点照 15 位有效数字给：0.1+0.2 给 0.3，sin(30°) 给 0.5
    return f"{value:.15g}"


def short(source):
    source = source.strip()
    return source if len(source) <= 80 else source[:77] + "…"


def calculate(source, functions):
    text = source.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise Failure("算式写法不对：看看括号、运算符") from None
    return evaluate(tree, functions)


def known_params():
    """开头 Parameters 里写的参数名：不认识的参数直接报错，免得写错的名字被悄悄当成没给。"""
    lines, inside = [], False
    with open(__file__, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            if line.startswith("# Parameters:"):
                inside = True
            elif inside:
                lines.append(line[1:])
    return set(json.loads("".join(lines)).get("properties", {}))


def reject_unknown(args):
    unknown = sorted(set(args) - known_params())
    if unknown:
        print(f"错误：不认识的参数：{'、'.join(unknown)}。能用的：{'、'.join(sorted(known_params()))}")
        sys.exit(1)


def main():
    try:
        args = json.load(sys.stdin)
    except ValueError as exc:
        print(f"错误：参数不是 JSON 对象：{exc}")
        sys.exit(1)
    if not isinstance(args, dict):
        print("错误：参数要是一个 JSON 对象")
        sys.exit(1)
    reject_unknown(args)
    # 整数结果已由 MAX_INT_BITS 限住（约 3 万位），用不着 Python 的 4300 位转换上限
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    expression = args.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        print("错误：expression 要写，例如 \"sqrt(2) * sin(pi/4)\"")
        sys.exit(1)
    if len(expression) > MAX_EXPRESSION:
        print(f"错误：算式太长，上限 {MAX_EXPRESSION} 字")
        sys.exit(1)
    angle = args.get("angle")
    if angle not in (None, "rad", "deg"):
        print("错误：angle 只能是 rad（弧度）或 deg（角度）")
        sys.exit(1)
    functions = make_functions(angle == "deg")
    parts = [p for p in expression.replace("\n", ";").split(";") if p.strip()]
    lines, failed = [], False
    for part in parts:
        try:
            lines.append(f"{short(part)} = {show(calculate(part, functions))}")
        except Failure as exc:
            failed = True
            lines.append(f"{short(part)}：错误：{exc}")
        except RecursionError:
            failed = True
            lines.append(f"{short(part)}：错误：嵌套太深")
    print("\n".join(lines))
    sys.exit(1 if failed and len(parts) == 1 else 0)


if __name__ == "__main__":
    main()
