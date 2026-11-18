# calculator.py 的测试（审计 2026-11-18 #170）。
#
# 跑法（在仓库根）：
#   python3 -I -B -m unittest discover -s .github/tests
# （不加 -t .：.github 不是合法的包名，加了 unittest 会报 Start directory is not importable。）
#
# 只用标准库，不联网。每条都用子进程跑脚本：timeout=10 秒、地址空间上限 1 GiB，
# 超时就算失败，测试本身不会卡住或吃光内存。HOME、XDG_* 指到临时目录。
# 放在 .github/tests/ 而不是 tests/：打包会跳过 .github，测试不会进包。

import json
import os
import pathlib
import resource
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "calculator.py"
TIMEOUT = 10          # 子进程最多跑这么久，超了算失败
QUICK = 2.0           # 「很快返回」的标准
MEMORY = 1 << 30      # 子进程地址空间上限


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))


class Calc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = self.tmp.name
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
                    "HOME": root, "XDG_CONFIG_HOME": root, "XDG_CACHE_HOME": root,
                    "XDG_STATE_HOME": root, "XDG_DATA_HOME": root}

    def run_calc(self, args):
        """跑一次脚本，返回 (退出码, stdout+stderr, 用时秒)。超时直接判失败。"""
        start = time.monotonic()
        try:
            p = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT)], input=json.dumps(args),
                               capture_output=True, text=True, timeout=TIMEOUT, env=self.env,
                               preexec_fn=limit_memory)
        except subprocess.TimeoutExpired:
            self.fail(f"{args} 跑了 {TIMEOUT} 秒还没返回")
        return p.returncode, p.stdout + p.stderr, time.monotonic() - start

    # 审计 #170-1：MAX_FACTORIAL=5000、MAX_INT_BITS 约 3 万位都允许超过 4300 位的整数，
    # 但 show() 里 str(int) 撞上 Python 的 4300 位转换上限，抛 ValueError 打 traceback。
    def test_factorial_5000_prints_digit_count(self):
        code, out, _ = self.run_calc({"expression": "factorial(5000)"})
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out[-500:])
        self.assertIn("16326 位", out)

    # 同一个缺陷，走乘方：2^20000 有 6021 位，在 MAX_INT_BITS 之内。
    def test_big_power_prints_digit_count(self):
        code, out, _ = self.run_calc({"expression": "2^20000"})
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out[-500:])
        self.assertIn("6021 位", out)

    # 审计 #170-2：rounded() 直接算 10 ** int(digits)，没走 power() 的上限，
    # round(1, 10^9) 要算十亿位的整数，CPU 内存一起吃（30 秒都不返回）。
    # 负的很大的位数同理：10 ** -10^9 下溢成 0.0，接着除以零抛 ZeroDivisionError。
    # 修好后应很快返回：给出结果，或者一句友好错误；不能卡住、不能 traceback。
    def test_round_huge_digits_returns_quickly(self):
        for expr in ("round(1, 10^9)", "round(1, 10000000)", "round(1.5, -10^9)"):
            with self.subTest(expr=expr):
                code, out, took = self.run_calc({"expression": expr})
                self.assertNotIn("Traceback", out)
                self.assertLess(took, QUICK, f"{expr} 用了 {took:.1f} 秒")
                self.assertTrue(out.startswith(f"{expr} = ") or "错误：" in out, out[-300:])

    # 审计 #170-3：comb/perm 先让 math.comb/perm 把结果整个算出来，
    # 之后 check_int 才查位数；comb(10^7, 5*10^6) 30 秒都不返回。
    # 修好后应先估结果大小，很快报「结果太大」。
    def test_comb_perm_huge_refused_quickly(self):
        for expr in ("comb(10^7, 5*10^6)", "perm(10^7, 5*10^6)"):
            with self.subTest(expr=expr):
                code, out, took = self.run_calc({"expression": expr})
                self.assertNotIn("Traceback", out)
                self.assertLess(took, QUICK, f"{expr} 用了 {took:.1f} 秒")
                self.assertEqual(code, 1, out[-300:])
                self.assertIn("结果太大", out)

    # 防改坏（现在就绿）：小的组合数照常精确算。
    def test_small_comb_still_exact(self):
        code, out, _ = self.run_calc({"expression": "comb(52, 5)"})
        self.assertEqual(code, 0, out)
        self.assertIn("= 2598960", out)

    # 审计 #170-4：angle 只认 == "deg"，写错成 "degrees" 不报错、静默按弧度算
    # （sin(90) 给 0.894）。应报错，指出 angle 只能是 rad 或 deg。
    def test_unknown_angle_rejected(self):
        code, out, _ = self.run_calc({"expression": "sin(90)", "angle": "degrees"})
        self.assertNotIn("0.893996663600558", out)
        self.assertEqual(code, 1, out)
        self.assertIn("angle", out)

    # 防改坏（现在就绿）：deg 照常按角度算。
    def test_deg_still_works(self):
        code, out, _ = self.run_calc({"expression": "sin(90)", "angle": "deg"})
        self.assertEqual(code, 0, out)
        self.assertIn("sin(90) = 1", out)


if __name__ == "__main__":
    unittest.main()
