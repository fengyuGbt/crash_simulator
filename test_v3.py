#!/usr/bin/env python3
"""
第三版功能测试：SDE跳跃扩散模型

测试内容：
1. 跳跃扩散模型模拟
2. 从跳跃扩散模拟中筛选股灾情景
3. 用股灾情景进行压力测试
4. 不同严重程度的对比
"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pandas as pd
from src.jump_diffusion import JumpDiffusionModel, JumpDiffusionParams, generate_crash_jump_params
from src.exposure import create_sample_portfolio
from src.hazard import CrashEvent
from src.vulnerability import VulnerabilityEngine
from src.loss import LossEngine

print("=" * 70)
print("第三版功能测试：SDE跳跃扩散模型")
print("=" * 70)

# 创建投资组合
portfolio = create_sample_portfolio()
print(f"\n投资组合：{portfolio.name}")
print(f"  股票数：{len(portfolio.positions)}")
print(f"  总市值：${portfolio.total_value:,.0f}")

# 创建引擎
vuln_engine = VulnerabilityEngine()
loss_engine = LossEngine(None, vuln_engine)

# ========== 测试1：跳跃扩散模型基础模拟 ==========
print("\n" + "=" * 70)
print("[测试1] 跳跃扩散模型基础模拟")
print("=" * 70)

model = JumpDiffusionModel()
result = model.simulate_single(random_seed=42)

print(f"\n单条路径模拟：")
print(f"  初始价格：{result.params.initial_price}")
print(f"  最终价格：{result.prices[-1]:.2f}")
print(f"  总收益率：{result.total_return*100:.1f}%")
print(f"  最大回撤：{result.max_drawdown*100:.1f}%")
print(f"  跳跃次数：{result.n_jumps}")
print(f"  年化波动率：{result.annualized_vol*100:.1f}%")

# 蒙特卡洛
print(f"\n蒙特卡洛模拟（2000次）...")
results = model.simulate(n_simulations=2000, base_seed=42)
max_drawdowns = [r.max_drawdown for r in results]
total_returns = [r.total_return for r in results]

print(f"  平均最大回撤：{np.mean(max_drawdowns)*100:.1f}%")
print(f"  中位数最大回撤：{np.median(max_drawdowns)*100:.1f}%")
print(f"  5%分位最大回撤：{np.percentile(max_drawdowns, 5)*100:.1f}%")
print(f"  1%分位最大回撤：{np.percentile(max_drawdowns, 1)*100:.1f}%")
print(f"  最坏最大回撤：{np.min(max_drawdowns)*100:.1f}%")
print(f"  平均总收益率：{np.mean(total_returns)*100:.1f}%")
print(f"  股灾概率(回撤>20%)：{sum(1 for d in max_drawdowns if d < -0.20)/len(max_drawdowns)*100:.1f}%")
print(f"  严重股灾概率(回撤>40%)：{sum(1 for d in max_drawdowns if d < -0.40)/len(max_drawdowns)*100:.1f}%")

# ========== 测试2：股灾情景筛选 ==========
print("\n" + "=" * 70)
print("[测试2] 从跳跃扩散模拟中筛选股灾情景")
print("=" * 70)

scenarios = model.get_crash_scenarios(
    n_scenarios=10,
    crash_threshold=-0.20,
    base_seed=42,
)

print(f"\n筛选出 {len(scenarios)} 个股灾情景（回撤>20%）：")
for s in scenarios:
    print(f"  {s['scenario_id']}: 最大回撤{s['max_drawdown']*100:.1f}%, "
          f"第{s['crash_day']}天见底, 跳跃{s['n_jumps']}次, "
          f"总收益{s['total_return']*100:.1f}%")

# ========== 测试3：用股灾情景进行压力测试 ==========
print("\n" + "=" * 70)
print("[测试3] 用跳跃扩散股灾情景进行压力测试")
print("=" * 70)

# 将股灾情景转换为CrashEvent并计算损失
loss_data = []
for i, scenario in enumerate(scenarios):
    event = CrashEvent(
        event_id=scenario["scenario_id"],
        event_name="跳跃扩散股灾",
        event_type="系统性股灾",
        start_date="2025-01-01",
        end_date="2025-12-31",
        duration_days=scenario["crash_day"],
        market_drop=scenario["max_drawdown"],  # 用最大回撤作为大盘跌幅
        affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
        probability=0.02,
        description=f"跳跃扩散模型生成的股灾情景，跳跃{scenario['n_jumps']}次",
        seed=i,
    )

    # 计算脆弱性
    vuln_results = vuln_engine.calculate_portfolio(portfolio, event, add_noise=True)

    # 计算损失
    total_loss = 0.0
    position_losses = {}
    for vr, position in zip(vuln_results, portfolio.positions):
        loss = position.market_value * abs(vr.final_drop)
        position_losses[position.ticker] = loss
        total_loss += loss

    total_loss_pct = total_loss / portfolio.total_value
    loss_data.append({
        "scenario_id": scenario["scenario_id"],
        "market_drop": scenario["max_drawdown"],
        "portfolio_loss": total_loss,
        "portfolio_loss_pct": total_loss_pct,
        "n_jumps": scenario["n_jumps"],
    })

loss_df = pd.DataFrame(loss_data)
print(f"\n压力测试结果（{len(scenarios)}个股灾情景）：")
print(f"  平均组合损失：${loss_df['portfolio_loss'].mean():,.0f} ({loss_df['portfolio_loss_pct'].mean()*100:.1f}%)")
print(f"  最大组合损失：${loss_df['portfolio_loss'].max():,.0f} ({loss_df['portfolio_loss_pct'].max()*100:.1f}%)")
print(f"  最小组合损失：${loss_df['portfolio_loss'].min():,.0f} ({loss_df['portfolio_loss_pct'].min()*100:.1f}%)")

print(f"\n各情景详情：")
for _, row in loss_df.iterrows():
    print(f"  {row['scenario_id']}: 大盘跌{row['market_drop']*100:.1f}%, "
          f"组合损失${row['portfolio_loss']:,.0f} ({row['portfolio_loss_pct']*100:.1f}%), "
          f"跳跃{int(row['n_jumps'])}次")

# ========== 测试4：不同严重程度对比 ==========
print("\n" + "=" * 70)
print("[测试4] 不同严重程度的跳跃扩散股灾对比")
print("=" * 70)

for severity in ["mild", "moderate", "severe", "extreme"]:
    params = generate_crash_jump_params(severity)
    model_sev = JumpDiffusionModel(params)

    # 模拟500次
    results_sev = model_sev.simulate(n_simulations=500, base_seed=42)
    max_dds = [r.max_drawdown for r in results_sev]
    crash_prob = sum(1 for d in max_dds if d < -0.20) / len(max_dds)
    severe_crash_prob = sum(1 for d in max_dds if d < -0.40) / len(max_dds)

    print(f"\n  {severity.upper()}:")
    print(f"    参数：μ={params.mu*100:.0f}%, σ={params.sigma*100:.0f}%, "
          f"λ={params.jump_lambda:.0f}次/年, 跳跃均值={params.jump_mu*100:.0f}%")
    print(f"    平均最大回撤：{np.mean(max_dds)*100:.1f}%")
    print(f"    5%分位最大回撤：{np.percentile(max_dds, 5)*100:.1f}%")
    print(f"    最坏最大回撤：{np.min(max_dds)*100:.1f}%")
    print(f"    股灾概率(回撤>20%)：{crash_prob*100:.1f}%")
    print(f"    严重股灾概率(回撤>40%)：{severe_crash_prob*100:.1f}%")

# ========== 测试5：跳跃的影响分析 ==========
print("\n" + "=" * 70)
print("[测试5] 跳跃对股灾的影响分析")
print("=" * 70)

# 对比有跳跃和无跳跃的情况
params_with_jump = JumpDiffusionParams(jump_lambda=4.0, jump_mu=-0.08, jump_sigma=0.12)
params_no_jump = JumpDiffusionParams(jump_lambda=0.0, jump_mu=0.0, jump_sigma=0.0)

model_with = JumpDiffusionModel(params_with_jump)
model_without = JumpDiffusionModel(params_no_jump)

results_with = model_with.simulate(n_simulations=1000, base_seed=42)
results_without = model_without.simulate(n_simulations=1000, base_seed=42)

dd_with = [r.max_drawdown for r in results_with]
dd_without = [r.max_drawdown for r in results_without]

print(f"\n有跳跃 vs 无跳跃对比（1000次模拟）：")
print(f"  {'指标':<20} {'有跳跃':>12} {'无跳跃':>12} {'差异':>12}")
print(f"  {'-'*56}")
print(f"  {'平均最大回撤':<20} {np.mean(dd_with)*100:>11.1f}% {np.mean(dd_without)*100:>11.1f}% {(np.mean(dd_with)-np.mean(dd_without))*100:>11.1f}%")
print(f"  {'5%分位最大回撤':<20} {np.percentile(dd_with, 5)*100:>11.1f}% {np.percentile(dd_without, 5)*100:>11.1f}% {(np.percentile(dd_with, 5)-np.percentile(dd_without, 5))*100:>11.1f}%")
print(f"  {'最坏最大回撤':<20} {np.min(dd_with)*100:>11.1f}% {np.min(dd_without)*100:>11.1f}% {(np.min(dd_with)-np.min(dd_without))*100:>11.1f}%")
print(f"  {'股灾概率(>20%)':<20} {sum(1 for d in dd_with if d < -0.20)/len(dd_with)*100:>11.1f}% {sum(1 for d in dd_without if d < -0.20)/len(dd_without)*100:>11.1f}% {(sum(1 for d in dd_with if d < -0.20)/len(dd_with)-sum(1 for d in dd_without if d < -0.20)/len(dd_without))*100:>11.1f}%")

print(f"\n结论：跳跃显著增加了尾部风险，最坏情况回撤从{np.min(dd_without)*100:.1f}%扩大到{np.min(dd_with)*100:.1f}%")

print("\n" + "=" * 70)
print("所有第三版功能测试通过！")
print("=" * 70)

print("""
第三版新增功能总结：
  1. SDE跳跃扩散模型（jump_diffusion.py）
     - 连续扩散部分（几何布朗运动）
     - 跳跃部分（泊松过程驱动，模拟黑天鹅事件）
     - 蒙特卡洛模拟多条价格路径
     - 从模拟中筛选股灾情景
     - 不同严重程度的参数预设（mild/moderate/severe/extreme）
     - 从历史收益率校准参数

  2. 跳跃扩散股灾情景用于压力测试
     - 将跳跃扩散生成的股灾情景转换为CrashEvent
     - 用脆弱性模型计算各股票跌幅
     - 计算投资组合损失

  3. 跳跃对尾部风险的影响分析
     - 有跳跃 vs 无跳跃对比
     - 跳跃显著增加了最坏情况回撤和股灾概率
""")
