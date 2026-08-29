#!/usr/bin/env python3
"""测试Vine copula拟合是否成功"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
from src.vine_copula import VineCopulaModel, generate_sample_returns

print("=" * 60)
print("Vine copula拟合验证")
print("=" * 60)

# 生成示例数据
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
print(f"\n生成示例数据: {len(tickers)}只股票，500天")
returns = generate_sample_returns(tickers, n_days=500, correlation=0.6, tail_dependence=0.5)
print(f"  数据形状: {returns.shape}")

# 拟合Vine copula
print("\n拟合Vine copula...")
model = VineCopulaModel(tickers)
result = model.fit(returns)

print(f"\n拟合结果:")
print(f"  股票数: {len(result.tickers)}")
print(f"  观测数: {result.n_observations}")
print(f"  对数似然: {result.log_likelihood:.2f}")
print(f"  AIC: {result.aic:.2f}")
print(f"  BIC: {result.bic:.2f}")
print(f"  尾部依赖对数: {len(result.tail_dependencies)}")

# 显示尾部依赖
print(f"\n尾部依赖系数:")
for td in result.tail_dependencies[:10]:
    print(f"  {td.ticker_i} - {td.ticker_j}: 下尾={td.lower_tail:.3f}, 上尾={td.upper_tail:.3f}, "
          f"tau={td.kendall_tau:.3f}, copula={td.copula_family}")

# 统计
lower_tails = [td.lower_tail for td in result.tail_dependencies]
print(f"\n尾部依赖统计:")
print(f"  平均下尾依赖: {np.mean(lower_tails):.4f}")
print(f"  最大下尾依赖: {np.max(lower_tails):.4f}")
print(f"  高尾部依赖(>0.2)对数: {sum(1 for lt in lower_tails if lt > 0.2)}")

# 测试条件跌幅模拟
print(f"\n条件跌幅模拟（大盘跌30%）:")
drops = model.simulate_conditional_drop(market_drop=-0.30, n_simulations=1000, random_seed=42)
print(f"  模拟次数: {len(drops)}")
for ticker in tickers:
    avg = drops[ticker].mean()
    std = drops[ticker].std()
    print(f"    {ticker}: 平均{avg*100:.1f}%, 标准差{std*100:.1f}%")

# 检查模型对象
print(f"\n模型对象检查:")
print(f"  model.model: {model.model}")
print(f"  model.fitted: {model.fitted}")
if model.model is not None:
    print(f"  model.model.dim: {model.model.dim}")
    print(f"  model.model.npars: {model.model.npars}")
    print(f"  model.model.families: {model.model.families}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
