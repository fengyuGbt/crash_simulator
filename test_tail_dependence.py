#!/usr/bin/env python3
"""测试Vine copula尾部依赖系数计算"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
from src.vine_copula import VineCopulaModel, generate_sample_returns

print("=" * 60)
print("Vine copula尾部依赖系数测试")
print("=" * 60)

# 测试1：高尾部依赖的数据
print("\n【测试1】高尾部依赖数据（tail_dependence=0.7）")
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
returns = generate_sample_returns(tickers, n_days=1000, correlation=0.6, tail_dependence=0.7)

model = VineCopulaModel(tickers)
result = model.fit(returns)

print(f"拟合结果类型: {type(result)}")
print(f"拟合结果属性: {[a for a in dir(result) if not a.startswith('_')]}")
if hasattr(result, 'copula_families'):
    print(f"copula族: {result.copula_families}")
if hasattr(result, 'n_params'):
    print(f"参数数: {result.n_params}")

tail_deps = result.tail_dependencies
print(f"\n尾部依赖系数（共{len(tail_deps)}对）:")
print(f"{'股票对':<15} {'下尾':<8} {'上尾':<8} {'tau':<8} {'copula族'}")
print("-" * 60)
for td in tail_deps[:5]:  # 只显示前5对
    print(f"{td.ticker_i}-{td.ticker_j:<8} {td.lower_tail:<8.3f} {td.upper_tail:<8.3f} {td.kendall_tau:<8.3f} {td.copula_family}")

avg_lower = np.mean([td.lower_tail for td in tail_deps])
avg_upper = np.mean([td.upper_tail for td in tail_deps])
print(f"\n平均下尾依赖: {avg_lower:.3f}")
print(f"平均上尾依赖: {avg_upper:.3f}")

# 测试2：低尾部依赖的数据
print("\n" + "=" * 60)
print("【测试2】低尾部依赖数据（tail_dependence=0.1）")
returns2 = generate_sample_returns(tickers, n_days=1000, correlation=0.3, tail_dependence=0.1)

model2 = VineCopulaModel(tickers)
result2 = model2.fit(returns2)

print(f"拟合成功: {result2.success}")
print(f"copula族: {result2.copula_families}")

tail_deps2 = result2.tail_dependencies
avg_lower2 = np.mean([td.lower_tail for td in tail_deps2])
avg_upper2 = np.mean([td.upper_tail for td in tail_deps2])
print(f"平均下尾依赖: {avg_lower2:.3f}")
print(f"平均上尾依赖: {avg_upper2:.3f}")

# 测试3：条件跌幅模拟
print("\n" + "=" * 60)
print("【测试3】条件跌幅模拟（大盘跌30%）")
sim_drops = model.simulate_conditional_drop(-0.30, n_simulations=1000)
print(f"模拟形状: {sim_drops.shape}")
print(f"各股票平均跌幅:")
for col in sim_drops.columns:
    print(f"  {col}: {sim_drops[col].mean()*100:.1f}%")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
