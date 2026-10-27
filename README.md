# 计算器

Miyu 脚本包，带一件工具 `calculator`：算一个或几个算式（用 `;` 或换行隔开）。

| 参数 | 说明 |
|---|---|
| `expression` | 算式。`+ - * / // %`，`^` 和 `**` 都是乘方。函数：sin cos tan asin acos atan atan2 sinh cosh tanh sqrt cbrt abs ln log(x[, 底]) log2 log10 exp floor ceil round(x[, 位数]) trunc factorial gcd lcm comb perm min max hypot degrees radians。常数：pi e tau inf |
| `angle` | 三角函数的单位：`rad`（默认）、`deg` |

整数照精确值算（`2^100` 给全部位数），浮点给 15 位有效数字。`round` 是四舍五入（.5 远离零）。结果超过约 3 万位、阶乘超过 5000! 的不算。不用 `eval`，只认上面这些写法。只用标准库，不联网。
