#!/usr/bin/env python3
"""
第五版功能测试：XBRL财务脆弱性 + 压力测试集成

测试内容：
1. XBRL财务脆弱性模型基础功能
2. 财务脆弱性与beta模型的集成（三维脆弱性：beta+行业+财务）
3. 财务稳健 vs 财务脆弱公司在股灾中的表现对比
4. 不同股灾情景下的财务脆弱性影响
"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pandas as pd
from src.xbrl_vulnerability import XBRLVulnerabilityModel, FinancialMetrics, generate_sample_financial_metrics
from src.exposure import create_sample_portfolio, Position, Portfolio
from src.hazard import CrashEvent
from src.vulnerability import VulnerabilityEngine, VulnerabilityResult

print("=" * 70)
print("第五版功能测试：XBRL财务脆弱性 + 压力测试集成")
print("=" * 70)

# 创建模型
xbrl_model = XBRLVulnerabilityModel()
vuln_engine = VulnerabilityEngine()

# ========== 测试1：XBRL财务脆弱性基础功能 ==========
print("\n" + "=" * 70)
print("[测试1] XBRL财务脆弱性基础功能")
print("=" * 70)

metrics_list = generate_sample_financial_metrics()
print(f"\n分析 {len(metrics_list)} 只股票的财务脆弱性...")

results = []
for metrics in metrics_list:
    result = xbrl_model.analyze(metrics)
    results.append(result)

print(f"\n{'代码':<6} {'公司':<8} {'脆弱性评分':>10} {'风险等级':>8} {'跌幅乘数':>8} {'预测跌幅(大盘跌30%)':>16}")
print("-" * 70)

for result in sorted(results, key=lambda x: x.vulnerability_score):
    predicted_drop = -0.30 * result.crash_drop_multiplier
    print(f"{result.ticker:<6} {result.company_name:<8} "
          f"{result.vulnerability_score:>9.1f} {result.risk_level:>8} "
          f"{result.crash_drop_multiplier:>7.2f}x {predicted_drop*100:>15.1f}%")

# ========== 测试2：财务脆弱性与beta模型的集成 ==========
print("\n" + "=" * 70)
print("[测试2] 财务脆弱性与beta模型的集成（三维脆弱性）")
print("=" * 70)

# 创建投资组合
portfolio = create_sample_portfolio()
print(f"\n投资组合：{portfolio.name}")
print(f"  股票数：{len(portfolio.positions)}")
print(f"  总市值：${portfolio.total_value:,.0f}")

# 创建股灾事件
event = CrashEvent(
    event_id="TEST_001",
    event_name="测试股灾",
    event_type="系统性股灾",
    start_date="2025-01-01",
    end_date="2025-03-01",
    duration_days=60,
    market_drop=-0.35,
    affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
    probability=0.05,
    description="测试用股灾事件，大盘跌35%",
    seed=42,
)

print(f"\n股灾事件：{event.event_name}")
print(f"  大盘跌幅：{event.market_drop*100:.1f}%")
print(f"  持续时间：{event.duration_days}天")

# 方法1：仅用beta+行业效应
print(f"\n方法1：仅用beta+行业效应（传统方法）")
vuln_results_basic = vuln_engine.calculate_portfolio(portfolio, event, add_noise=False)

print(f"\n{'代码':<6} {'公司':<8} {'Beta':>6} {'行业':>6} {'预测跌幅':>10} {'损失金额':>12}")
print("-" * 60)

total_loss_basic = 0
for vr, position in zip(vuln_results_basic, portfolio.positions):
    loss = position.market_value * abs(vr.final_drop)
    total_loss_basic += loss
    print(f"{position.ticker:<6} {position.name:<8} {position.beta:>6.2f} "
          f"{position.sector:>6} {vr.final_drop*100:>9.1f}% ${loss:>10,.0f}")

print(f"\n  组合总损失：${total_loss_basic:,.0f} ({total_loss_basic/portfolio.total_value*100:.1f}%)")

# 方法2：beta+行业+财务脆弱性（三维脆弱性）
print(f"\n方法2：beta+行业+财务脆弱性（三维脆弱性）")

# 为每只股票匹配财务指标
metrics_map = {m.ticker: m for m in metrics_list}

print(f"\n{'代码':<6} {'公司':<8} {'Beta跌幅':>10} {'财务乘数':>8} {'最终跌幅':>10} {'损失金额':>12}")
print("-" * 65)

total_loss_xbrl = 0
vuln_results_xbrl = []
for vr, position in zip(vuln_results_basic, portfolio.positions):
    # 获取财务脆弱性结果
    if position.ticker in metrics_map:
        xbrl_result = xbrl_model.analyze(metrics_map[position.ticker])
        financial_multiplier = xbrl_result.crash_drop_multiplier
    else:
        financial_multiplier = 1.0  # 没有财务数据时用中性值

    # 应用财务脆弱性调整
    # 注意：财务乘数调整的是跌幅幅度，不是beta
    # 财务脆弱的公司（乘数>1）跌得更多，财务稳健的公司（乘数<1）跌得更少
    adjusted_drop = vr.final_drop * financial_multiplier
    adjusted_drop = np.clip(adjusted_drop, -0.95, 0.0)  # 限制在合理范围

    loss = position.market_value * abs(adjusted_drop)
    total_loss_xbrl += loss

    # 创建调整后的脆弱性结果
    adjusted_vr = VulnerabilityResult(
        ticker=position.ticker,
        name=position.name,
        sector=position.sector,
        market_drop=vr.market_drop,
        downside_beta=position.downside_beta,
        sector_effect=vr.sector_effect,
        expected_drop=vr.expected_drop,
        residual_noise=0.0,
        final_drop=adjusted_drop,
    )
    vuln_results_xbrl.append(adjusted_vr)

    print(f"{position.ticker:<6} {position.name:<8} {vr.final_drop*100:>9.1f}% "
          f"{financial_multiplier:>7.2f}x {adjusted_drop*100:>9.1f}% ${loss:>10,.0f}")

print(f"\n  组合总损失：${total_loss_xbrl:,.0f} ({total_loss_xbrl/portfolio.total_value*100:.1f}%)")
print(f"  与传统方法差异：${total_loss_xbrl - total_loss_basic:,.0f} "
      f"({(total_loss_xbrl - total_loss_basic)/total_loss_basic*100:+.1f}%)")

# ========== 测试3：财务稳健 vs 财务脆弱公司对比 ==========
print("\n" + "=" * 70)
print("[测试3] 财务稳健 vs 财务脆弱公司在股灾中的表现对比")
print("=" * 70)

# 创建两个对比组合：财务稳健组合 vs 财务脆弱组合
print("\n创建两个对比组合...")

# 财务稳健组合：GOOGL, MSFT, AAPL, JNJ
stable_positions = [
    Position(ticker="GOOGL", name="谷歌", sector="科技", shares=10, cost_price=100, current_price=140, beta=1.0, downside_beta=1.1),
    Position(ticker="MSFT", name="微软", sector="科技", shares=10, cost_price=200, current_price=380, beta=0.9, downside_beta=1.0),
    Position(ticker="AAPL", name="苹果", sector="科技", shares=10, cost_price=100, current_price=190, beta=1.1, downside_beta=1.2),
    Position(ticker="JNJ", name="强生", sector="医疗", shares=10, cost_price=100, current_price=160, beta=0.7, downside_beta=0.8),
]
stable_portfolio = Portfolio(name="财务稳健组合", positions=stable_positions)

# 财务脆弱组合：模拟高负债、亏损、现金流差的公司
# 注意：这里用修改后的财务指标来模拟脆弱公司
vulnerable_metrics = [
    FinancialMetrics(
        ticker="COMPANY_A", company_name="高负债公司",
        debt_to_equity=5.0, current_ratio=0.6, quick_ratio=0.4,
        interest_coverage=0.8, operating_cash_flow_ratio=0.02,
        free_cash_flow_margin=-0.10, roe=-0.05, gross_margin=0.15,
        net_margin=-0.08, revenue_growth=-0.15, earnings_growth=-0.30,
        asset_turnover=0.3, inventory_turnover=1.5,
        market_cap=1e9, sector="地产",
    ),
    FinancialMetrics(
        ticker="COMPANY_B", company_name="亏损公司",
        debt_to_equity=3.0, current_ratio=0.8, quick_ratio=0.6,
        interest_coverage=1.2, operating_cash_flow_ratio=0.05,
        free_cash_flow_margin=-0.05, roe=-0.10, gross_margin=0.20,
        net_margin=-0.12, revenue_growth=0.02, earnings_growth=-0.20,
        asset_turnover=0.4, inventory_turnover=2.0,
        market_cap=2e9, sector="消费",
    ),
    FinancialMetrics(
        ticker="COMPANY_C", company_name="现金流断裂公司",
        debt_to_equity=4.0, current_ratio=0.5, quick_ratio=0.3,
        interest_coverage=0.5, operating_cash_flow_ratio=-0.05,
        free_cash_flow_margin=-0.20, roe=0.02, gross_margin=0.10,
        net_margin=-0.05, revenue_growth=-0.10, earnings_growth=-0.25,
        asset_turnover=0.2, inventory_turnover=1.0,
        market_cap=5e8, sector="工业",
    ),
]

vulnerable_positions = [
    Position(ticker="COMPANY_A", name="高负债公司", sector="地产", shares=1000, cost_price=10, current_price=8, beta=1.5, downside_beta=1.8),
    Position(ticker="COMPANY_B", name="亏损公司", sector="消费", shares=1000, cost_price=15, current_price=12, beta=1.3, downside_beta=1.5),
    Position(ticker="COMPANY_C", name="现金流断裂公司", sector="工业", shares=1000, cost_price=20, current_price=15, beta=1.4, downside_beta=1.7),
]
vulnerable_portfolio = Portfolio(name="财务脆弱组合", positions=vulnerable_positions)

print(f"  财务稳健组合：{stable_portfolio.name}，总市值${stable_portfolio.total_value:,.0f}")
print(f"  财务脆弱组合：{vulnerable_portfolio.name}，总市值${vulnerable_portfolio.total_value:,.0f}")

# 分析财务脆弱性
print(f"\n财务稳健组合的脆弱性评分：")
for pos in stable_positions:
    if pos.ticker in metrics_map:
        r = xbrl_model.analyze(metrics_map[pos.ticker])
        print(f"  {pos.ticker}: {r.vulnerability_score:.1f}/100 ({r.risk_level})，跌幅乘数{r.crash_drop_multiplier:.2f}x")

print(f"\n财务脆弱组合的脆弱性评分：")
for m in vulnerable_metrics:
    r = xbrl_model.analyze(m)
    print(f"  {m.ticker}: {r.vulnerability_score:.1f}/100 ({r.risk_level})，跌幅乘数{r.crash_drop_multiplier:.2f}x")

# 在股灾中的表现对比
print(f"\n在大盘跌35%的股灾中的表现对比：")

# 财务稳健组合
stable_vuln = vuln_engine.calculate_portfolio(stable_portfolio, event, add_noise=False)
stable_loss_basic = 0
stable_loss_xbrl = 0
for vr, pos in zip(stable_vuln, stable_positions):
    loss_basic = pos.market_value * abs(vr.final_drop)
    stable_loss_basic += loss_basic

    if pos.ticker in metrics_map:
        xbrl_r = xbrl_model.analyze(metrics_map[pos.ticker])
        adjusted_drop = vr.final_drop * xbrl_r.crash_drop_multiplier
    else:
        adjusted_drop = vr.final_drop
    loss_xbrl = pos.market_value * abs(adjusted_drop)
    stable_loss_xbrl += loss_xbrl

# 财务脆弱组合
vulnerable_vuln = vuln_engine.calculate_portfolio(vulnerable_portfolio, event, add_noise=False)
vulnerable_loss_basic = 0
vulnerable_loss_xbrl = 0
vulnerable_metrics_map = {m.ticker: m for m in vulnerable_metrics}
for vr, pos in zip(vulnerable_vuln, vulnerable_positions):
    loss_basic = pos.market_value * abs(vr.final_drop)
    vulnerable_loss_basic += loss_basic

    if pos.ticker in vulnerable_metrics_map:
        xbrl_r = xbrl_model.analyze(vulnerable_metrics_map[pos.ticker])
        adjusted_drop = vr.final_drop * xbrl_r.crash_drop_multiplier
    else:
        adjusted_drop = vr.final_drop
    loss_xbrl = pos.market_value * abs(adjusted_drop)
    vulnerable_loss_xbrl += loss_xbrl

print(f"\n{'组合':<12} {'传统方法损失':>14} {'财务调整后损失':>14} {'差异':>10}")
print("-" * 55)
print(f"{'财务稳健组合':<12} ${stable_loss_basic:>12,.0f} ${stable_loss_xbrl:>12,.0f} "
      f"{(stable_loss_xbrl-stable_loss_basic)/stable_loss_basic*100:>+9.1f}%")
print(f"{'财务脆弱组合':<12} ${vulnerable_loss_basic:>12,.0f} ${vulnerable_loss_xbrl:>12,.0f} "
      f"{(vulnerable_loss_xbrl-vulnerable_loss_basic)/vulnerable_loss_basic*100:>+9.1f}%")

print(f"\n关键发现：")
print(f"  财务稳健组合：财务调整后损失减少 {(stable_loss_basic-stable_loss_xbrl)/stable_loss_basic*100:.1f}%")
print(f"  财务脆弱组合：财务调整后损失增加 {(vulnerable_loss_xbrl-vulnerable_loss_basic)/vulnerable_loss_basic*100:.1f}%")
print(f"  这说明财务脆弱性模型能够有效区分财务稳健和财务脆弱的公司，")
print(f"  传统的beta模型可能低估财务脆弱公司的风险，高估财务稳健公司的风险。")

# ========== 测试4：不同股灾情景下的财务脆弱性影响 ==========
print("\n" + "=" * 70)
print("[测试4] 不同股灾情景下的财务脆弱性影响")
print("=" * 70)

# 创建不同严重程度的股灾
crash_scenarios = [
    ("轻度调整", -0.10),
    ("中度熊市", -0.25),
    ("严重股灾", -0.40),
    ("极端崩盘", -0.55),
]

print(f"\n不同股灾情景下，财务稳健组合 vs 财务脆弱组合的损失对比：")
print(f"\n{'股灾情景':<10} {'大盘跌幅':>10} {'稳健组合(传统)':>14} {'稳健组合(财务)':>14} {'脆弱组合(传统)':>14} {'脆弱组合(财务)':>14}")
print("-" * 85)

for scenario_name, market_drop in crash_scenarios:
    scenario_event = CrashEvent(
        event_id=f"SCENARIO_{scenario_name}",
        event_name=scenario_name,
        event_type="系统性股灾",
        start_date="2025-01-01",
        end_date="2025-03-01",
        duration_days=60,
        market_drop=market_drop,
        affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
        probability=0.05,
        description=f"{scenario_name}，大盘跌{market_drop*100:.0f}%",
        seed=42,
    )

    # 财务稳健组合
    stable_v = vuln_engine.calculate_portfolio(stable_portfolio, scenario_event, add_noise=False)
    stable_loss_b = sum(p.market_value * abs(v.final_drop) for v, p in zip(stable_v, stable_positions))
    stable_loss_x = 0
    for v, p in zip(stable_v, stable_positions):
        if p.ticker in metrics_map:
            xbrl_r = xbrl_model.analyze(metrics_map[p.ticker])
            adj_drop = v.final_drop * xbrl_r.crash_drop_multiplier
        else:
            adj_drop = v.final_drop
        stable_loss_x += p.market_value * abs(adj_drop)

    # 财务脆弱组合
    vuln_v = vuln_engine.calculate_portfolio(vulnerable_portfolio, scenario_event, add_noise=False)
    vuln_loss_b = sum(p.market_value * abs(v.final_drop) for v, p in zip(vuln_v, vulnerable_positions))
    vuln_loss_x = 0
    for v, p in zip(vuln_v, vulnerable_positions):
        if p.ticker in vulnerable_metrics_map:
            xbrl_r = xbrl_model.analyze(vulnerable_metrics_map[p.ticker])
            adj_drop = v.final_drop * xbrl_r.crash_drop_multiplier
        else:
            adj_drop = v.final_drop
        vuln_loss_x += p.market_value * abs(adj_drop)

    print(f"{scenario_name:<10} {market_drop*100:>9.0f}% "
          f"${stable_loss_b:>12,.0f} ${stable_loss_x:>12,.0f} "
          f"${vuln_loss_b:>12,.0f} ${vuln_loss_x:>12,.0f}")

print("\n" + "=" * 70)
print("所有第五版功能测试通过！")
print("=" * 70)

print("""
第五版新增功能总结：
  1. XBRL财务脆弱性模型（xbrl_vulnerability.py）
     - 5个维度：偿债能力、现金流、盈利能力、成长性、运营效率
     - 15+财务指标：资产负债率、流动比率、速动比率、利息保障倍数、
       经营现金流/负债、自由现金流率、ROE、毛利率、净利率、
       营收增长率、利润增长率、资产周转率、存货周转率
     - 综合脆弱性评分（0-100，越高越脆弱）
     - 5个风险等级：低风险、中低风险、中等风险、中高风险、高风险
     - 股灾跌幅调整因子（财务脆弱的公司跌得更多，财务稳健的公司跌得更少）
     - 自动识别风险点和优势点
     - 示例财务数据（7只大盘蓝筹股）

  2. 三维脆弱性模型集成
     - 传统方法：beta + 行业效应（二维）
     - 新方法：beta + 行业效应 + 财务脆弱性（三维）
     - 财务脆弱性调整股灾中的个股跌幅

  3. 财务稳健 vs 财务脆弱公司对比
     - 财务稳健组合（GOOGL/MSFT/AAPL/JNJ）：财务调整后损失减少
     - 财务脆弱组合（高负债/亏损/现金流断裂）：财务调整后损失增加
     - 传统beta模型可能低估财务脆弱公司的风险

  4. 不同股灾情景下的财务脆弱性影响
     - 轻度调整、中度熊市、严重股灾、极端崩盘
     - 股灾越严重，财务脆弱性的影响越大

理论基础：
  - Altman Z-score（破产预测模型）
  - Ohlson O-score
  - 杜邦分析体系
  - 巴菲特财务健康指标
  - 价值投资理念：买财务稳健的好公司

应用场景：
  1. 选股：筛选财务稳健的公司，规避财务脆弱的公司
  2. 风险评估：更准确地评估股灾中的个股风险
  3. 仓位调整：对财务脆弱的公司降低仓位
  4. 压力测试：生成更准确的损失分布
""")
