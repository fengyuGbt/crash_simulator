#!/usr/bin/env python3
"""股灾压力测试工具 - 基础功能测试"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

from src.exposure import create_sample_portfolio
from src.hazard import HazardEngine
from src.loss import LossEngine
from src.advice import PositionAdvisor

print("=" * 60)
print("股灾压力测试工具 - 基础功能测试")
print("=" * 60)

# 1. 测试投资组合
print("\n[1] 测试投资组合...")
p = create_sample_portfolio()
print(f"  组合名称: {p.name}")
print(f"  股票数量: {len(p.positions)}")
print(f"  总市值: ${p.total_value:,.0f}")
print(f"  加权Beta: {p.weighted_beta:.2f}")
print(f"  行业分布: {dict(p.sector_exposure)}")

# 2. 测试危险引擎
print("\n[2] 测试危险引擎...")
h = HazardEngine()
crashes = h.get_available_crashes()
print(f"  可用股灾事件: {len(crashes)}")
for c in crashes:
    print(f"    - {c['event_name']}: 跌幅{c['market_drop']*100:.1f}%, 概率{c['probability']*100:.1f}%")

# 3. 测试损失计算（蒙特卡洛）
print("\n[3] 测试蒙特卡洛损失计算（1000次模拟）...")
l = LossEngine(h)
results, df = l.run_monte_carlo(p, n_simulations=1000, random_seed=42)
print(f"  模拟次数: {len(results)}")
print(f"  损失分布统计:")
print(df['total_loss_pct'].describe().to_string())

# 4. 测试风险度量
print("\n[4] 测试风险度量...")
rm = l.calculate_risk_metrics(df, p.total_value)
print(f"  预期损失: ${rm.expected_loss:,.0f} ({rm.expected_loss_pct*100:.1f}%)")
print(f"  95% VaR: ${rm.var_95:,.0f} ({rm.var_95_pct*100:.1f}%)")
print(f"  99% VaR: ${rm.var_99:,.0f} ({rm.var_99_pct*100:.1f}%)")
print(f"  95% CVaR: ${rm.cvar_95:,.0f} ({rm.cvar_95_pct*100:.1f}%)")
print(f"  最坏情况: ${rm.max_loss:,.0f} ({rm.max_loss_pct*100:.1f}%)")

# 5. 测试仓位建议
print("\n[5] 测试仓位建议...")
advisor = PositionAdvisor(total_risk_budget_pct=0.02)
advice = advisor.calculate_portfolio_advice(p, total_capital=100000)
print(f"  总本金: ${advice.total_capital:,.0f}")
print(f"  总风险预算: ${advice.total_risk_budget:,.0f} ({advice.total_risk_budget_pct*100:.1f}%)")
print(f"  建议总仓位: ${advice.suggested_total_value:,.0f} ({advice.suggested_leverage*100:.0f}%)")
print(f"  建议持有现金: ${advice.suggested_cash:,.0f}")
print(f"  各股票建议:")
for pa in advice.position_advices:
    direction = "加仓" if pa.adjustment > 0 else "减仓" if pa.adjustment < 0 else "持有"
    print(f"    {pa.ticker}: 波动{pa.volatility*100:.0f}%, 止损{pa.stop_loss_distance*100:.0f}%, "
          f"建议仓位{pa.suggested_weight*100:.0f}%, {direction}${abs(pa.adjustment):,.0f}")

print("\n" + "=" * 60)
print("所有测试通过！")
print("=" * 60)
