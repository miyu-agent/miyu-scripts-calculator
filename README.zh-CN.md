<p align="center">
  <a href="README.md">English</a> | 简体中文
</p>

# 计算器

> <sub>本文档由 Anthropic 的 Claude Fable 5.2 生成。</sub>

这是 Miyu 的一个脚本软件包，提供一件工具 `calculator`，用来计算一个或者多个算式。多个算式之间用 `;` 或者换行隔开。

| 参数 | 说明 |
|---|---|
| `expression` | 算式。运算符有 `+ - * / // %`，`^` 和 `**` 都表示乘方。函数：sin cos tan asin acos atan atan2 sinh cosh tanh sqrt cbrt abs ln log(x[, 底]) log2 log10 exp floor ceil round(x[, 位数]) trunc factorial gcd lcm comb perm min max hypot degrees radians。常数：pi e tau inf |
| `angle` | 三角函数使用的单位：`rad`（默认）或者 `deg` |

整数按精确值计算（`2^100` 会给出全部位数），浮点数给出 15 位有效数字。`round` 是四舍五入（.5 向远离零的方向舍入）。如果结果超过约 3 万位，或者阶乘超过 5000!，工具不会计算。工具不使用 `eval`，只接受上面列出的写法。它只使用标准库，不需要联网。
