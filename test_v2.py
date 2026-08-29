#!/usr/bin/env python3
"""
股灾压力测试工具 - 第二版功能测试
测试：系统动力学反馈回路 + Vine copula尾部依赖
"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pandas as pd

from src.exposure import create_sample_portfolio
from src.system_dynamics import SystemDynamicsEngine, FeedbackParams
from src.vine_copula import VineCopulaModel, generate_sample_returns
from src.vulnerability import VineCopulaVulnerability
from src.hazard import CrashEvent

print("=" * 70)
print("股灾压力测试工具 - 第二版功能测试")
print("=" * 70)

# ========== 测试1：系统动力学反馈回路 ==========
print("\n" + "=" * 70)
print("[测试1] 系统动力学反馈回路")
print("=" * 70)

sd_engine = SystemDynamicsEngine()

# 模拟一个初始跌10%的股灾，持续60天
print("\n模拟初始冲击-10%，持续60天...")
sim_df = sd_engine.simulate(initial_shock=-0.10, n_days=60, random_seed=42)

print(f"  模拟天数: {len(sim_df)}")
print(f"  初始价格: 100.0")
print(f"  最低价格: {sim_df['price'].min():.2f}")
print(f"  最大跌幅: {sim_df['cumulative_drop'].min()*100:.1f}%")
print(f"  最大跌幅天数: 第{sim_df['cumulative_drop'].idxmin()}天")
print(f"  最低情绪: {sim_df['sentiment'].min():.3f}")
print(f"  最低流动性: {sim_df['liquidity'].min():.3f}")
print(f"  最大强制卖出: {sim_df['forced_selling'].max():.4f}")
print(f"  最大恐慌卖出: {sim_df['panic_selling'].max():.4f}")

# 获取摘要
summary = sd_engine.get_crash_summary(sim_df)
print(f"\n  股灾摘要:")
for k, v in summary.items():
    print(f"    {k}: {v}")

# 测试不同初始冲击的对比
print("\n不同初始冲击的对比:")
for shock in [-0.05, -0.10, -0.15, -0.20]:
    sim = sd_engine.simulate(initial_shock=shock, n_days=60, random_seed=42)
    max_drop = sim['cumulative_drop'].min()
    print(f"  初始冲击{shock*100:.0f}% -> 最大跌幅{max_drop*100:.1f}% (放大倍数{max_drop/shock:.1f}x)")

# 测试政策干预
print("\n政策干预效果对比:")
params_no_intervention = FeedbackParams(policy_intervention=False)
params_with_intervention = FeedbackParams(policy_intervention=True, intervention_threshold=-0.15, intervention_strength=0.5)

sd_no_int = SystemDynamicsEngine(params_no_intervention)
sd_with_int = SystemDynamicsEngine(params_with_intervention)

sim_no = sd_no_int.simulate(initial_shock=-0.20, n_days=60, random_seed=42)
sim_with = sd_with_int.simulate(initial_shock=-0.20, n_days=60, random_seed=42)

print(f"  无干预: 最大跌幅{sim_no['cumulative_drop'].min()*100:.1f}%")
print(f"  有干预: 最大跌幅{sim_with['cumulative_drop'].min()*100:.1f}%")
print(f"  干预效果: 减少跌幅{(sim_no['cumulative_drop'].min() - sim_with['cumulative_drop'].min())*100:.1f}个百分点")

# ========== 测试2：Vine Copula尾部依赖 ==========
print("\n" + "=" * 70)
print("[测试2] Vine Copula尾部依赖")
print("=" * 70)

# 生成示例收益率数据
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "JPM", "JNJ"]
print(f"\n生成示例收益率数据: {len(tickers)}只股票，252天")
returns = generate_sample_returns(tickers, n_days=252, correlation=0.5, tail_dependence=0.4)
print(f"  数据形状: {returns.shape}")
print(f"  平均收益率: {returns.mean().mean()*100:.4f}%")
print(f"  平均波动率: {returns.std().mean()*100:.2f}%")

# 拟合Vine copula
print("\n拟合Vine copula模型...")
vine_model = VineCopulaModel(tickers)
fit_result = vine_model.fit(returns, vine_type="rvine")

print(f"  拟合股票数: {len(fit_result.tickers)}")
print(f"  观测数: {fit_result.n_observations}")
print(f"  对数似然: {fit_result.log_likelihood:.2f}")
print(f"  AIC: {fit_result.aic:.2f}")
print(f"  BIC: {fit_result.bic:.2f}")
print(f"  尾部依赖对数: {len(fit_result.tail_dependencies)}")

# 显示尾部依赖
print("\n尾部依赖系数（前10对）:")
for i, td in enumerate(fit_result.tail_dependencies[:10]):
    print(f"  {td.ticker_i} - {td.ticker_j}: 下尾={td.lower_tail:.3f}, 上尾={td.upper_tail:.3f}, "
          f"Kendall tau={td.kendall_tau:.3f}, copula={td.copula_family}")

# 尾部依赖统计
lower_tails = [td.lower_tail for td in fit_result.tail_dependencies]
print(f"\n尾部依赖统计:")
print(f"  平均下尾依赖: {np.mean(lower_tails):.4f}")
print(f"  最大下尾依赖: {np.max(lower_tails):.4f}")
print(f"  高尾部依赖(>0.3)对数: {sum(1 for lt in lower_tails if lt > 0.3)}")

# 测试条件跌幅模拟
print("\n条件跌幅模拟（给定大盘跌30%）:")
drops_df = vine_model.simulate_conditional_drop(market_drop=-0.30, n_simulations=1000, random_seed=42)
print(f"  模拟次数: {len(drops_df)}")
print(f"  各股票平均跌幅:")
for ticker in tickers:
    avg_drop = drops_df[ticker].mean()
    std_drop = drops_df[ticker].std()
    print(f"    {ticker}: 平均{avg_drop*100:.1f}%, 标准差{std_drop*100:.1f}%")

# ========== 测试3：Vine Copula脆弱性模型 ==========
print("\n" + "=" * 70)
print("[测试3] Vine Copula脆弱性模型（集成到压力测试）")
print("=" * 70)

portfolio = create_sample_portfolio()
print(f"\n投资组合: {portfolio.name}")
print(f"  股票数: {len(portfolio.positions)}")
print(f"  总市值: ${portfolio.total_value:,.0f}")

# 创建Vine copula脆弱性模型（用示例数据自动拟合）
print("\n创建Vine Copula脆弱性模型（自动拟合示例数据）...")
vine_vuln = VineCopulaVulnerability(use_sample_data=True)

# 创建一个测试事件
test_event = CrashEvent(
    event_id="TEST_001",
    event_name="测试股灾",
    event_type="系统性股灾",
    start_date="2025-01-01",
    end_date="2025-03-01",
    duration_days=60,
    market_drop=-0.40,
    affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
    probability=0.02,
    description="测试用股灾事件",
)

# 计算联合跌幅
print("\n计算股灾中的联合跌幅（大盘跌40%）...")
vuln_results = vine_vuln.calculate_portfolio(portfolio, test_event, n_simulations=100)

print(f"  各股票预期跌幅:")
for vr in vuln_results:
    print(f"    {vr.ticker} ({vr.sector}): 预期{vr.expected_drop*100:.1f}%, "
          f"最终{vr.final_drop*100:.1f}% (行业效应{vr.sector_effect*100:.1f}%)")

# 计算组合加权跌幅
portfolio_drop = vine_vuln.calculate_portfolio_drop(portfolio, test_event)
print(f"\n  投资组合加权平均跌幅: {portfolio_drop*100:.1f}%")

# 尾部依赖摘要
tail_summary = vine_vuln.get_tail_dependence_summary()
print(f"\n  尾部依赖摘要:")
for k, v in tail_summary.items():
    print(f"    {k}: {v}")

# ========== 测试4：系统动力学生成股灾情景集 ==========
print("\n" + "=" * 70)
print("[测试4] 系统动力学生成股灾情景集（用于蒙特卡洛）")
print("=" * 70)

print("\n生成50个股灾情景...")
scenarios = sd_engine.generate_crash_scenarios(
    n_scenarios=50,
    initial_shock_range=(-0.05, -0.25),
    n_days=60,
    base_seed=42,
)

print(f"  生成情景数: {len(scenarios)}")
print(f"  初始冲击范围: {min(s['initial_shock'] for s in scenarios)*100:.0f}% ~ "
      f"{max(s['initial_shock'] for s in scenarios)*100:.0f}%")
print(f"  最大跌幅范围: {min(s['最大跌幅'] for s in scenarios)*100:.1f}% ~ "
      f"{max(s['最大跌幅'] for s in scenarios)*100:.1f}%")
print(f"  平均最大跌幅: {np.mean([s['最大跌幅'] for s in scenarios])*100:.1f}%")
print(f"  平均最大跌幅天数: {np.mean([s['最大跌幅天数'] for s in scenarios]):.0f}天")

# 显示前5个情景
print("\n前5个情景:")
for s in scenarios[:5]:
    print(f"  {s['scenario_id']}: 初始冲击{s['initial_shock']*100:.0f}%, "
          f"最大跌幅{s['最大跌幅']*100:.1f}%, 第{s['最大跌幅天数']}天见底")

print("\n" + "=" * 70)
print("所有第二版功能测试通过！")
print("=" * 70)
print("\n新增功能总结:")
print("  1. 系统动力学反馈回路：杠杆爆仓→强制卖出→更跌，情绪恐慌→抛售→更跌，流动性枯竭")
print("  2. Vine copula尾部依赖：捕捉危机时股票间相关性飙升，下尾依赖建模")
print("  3. Vine copula脆弱性模型：集成到压力测试，替代/补充beta模型")
print("  4. 系统动力学情景生成：生成多个股灾情景，用于蒙特卡洛事件集")
print("  5. 政策干预模拟：限制杠杆/救市等政策对股灾的影响")
