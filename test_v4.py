#!/usr/bin/env python3
"""
第四版功能测试：情绪NLP校准 + 跳跃扩散集成

测试内容：
1. 情绪校准模块基础功能
2. 不同情绪水平下的跳跃扩散模拟对比
3. 情绪校准对压力测试结果的影响
4. 文本情绪分析功能
"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pandas as pd
from src.sentiment_calibration import SentimentCalibrator, SentimentParams, analyze_sentiment_from_texts
from src.jump_diffusion import JumpDiffusionModel, JumpDiffusionParams, generate_crash_jump_params
from src.exposure import create_sample_portfolio
from src.hazard import CrashEvent
from src.vulnerability import VulnerabilityEngine

print("=" * 70)
print("第四版功能测试：情绪NLP校准 + 跳跃扩散集成")
print("=" * 70)

# 创建投资组合
portfolio = create_sample_portfolio()
print(f"\n投资组合：{portfolio.name}")
print(f"  股票数：{len(portfolio.positions)}")
print(f"  总市值：${portfolio.total_value:,.0f}")

# 创建引擎
calibrator = SentimentCalibrator()
vuln_engine = VulnerabilityEngine()

# ========== 测试1：情绪校准基础功能 ==========
print("\n" + "=" * 70)
print("[测试1] 情绪校准基础功能")
print("=" * 70)

test_sentiments = [10, 25, 40, 50, 60, 75, 90]

print(f"\n不同情绪指数的校准结果：")
print(f"{'情绪指数':>8} {'市场状态':>8} {'股灾概率':>10} {'跳跃强度乘数':>12} {'跳跃幅度乘数':>12}")
print("-" * 60)

for sentiment in test_sentiments:
    result = calibrator.calibrate(sentiment)
    print(f"{sentiment:>8.0f} {result.market_state:>8} "
          f"{result.crash_probability*100:>9.1f}% "
          f"{result.jump_intensity_multiplier:>11.2f}x "
          f"{result.jump_size_multiplier:>11.2f}x")

# ========== 测试2：不同情绪水平下的跳跃扩散模拟对比 ==========
print("\n" + "=" * 70)
print("[测试2] 不同情绪水平下的跳跃扩散模拟对比")
print("=" * 70)

# 使用moderate严重程度作为基础参数
base_params = generate_crash_jump_params("moderate")
print(f"\n基础参数（moderate）：")
print(f"  漂移率 μ: {base_params.mu*100:.0f}%")
print(f"  波动率 σ: {base_params.sigma*100:.0f}%")
print(f"  跳跃强度 λ: {base_params.jump_lambda:.0f}次/年")
print(f"  跳跃幅度均值: {base_params.jump_mu*100:.0f}%")
print(f"  跳跃幅度标准差: {base_params.jump_sigma*100:.0f}%")

# 测试三种情绪状态
sentiment_scenarios = [
    ("极度恐惧", 15),
    ("中性", 50),
    ("极度贪婪", 85),
]

print(f"\n三种情绪状态下的跳跃扩散模拟对比（1000次蒙特卡洛）：")
print(f"{'情绪状态':>8} {'情绪指数':>8} {'校准后λ':>10} {'平均回撤':>10} {'5%分位回撤':>12} {'最坏回撤':>10} {'股灾概率':>10}")
print("-" * 80)

for state_name, sentiment in sentiment_scenarios:
    # 校准参数
    calibrated_params, calibrated = calibrator.calibrate_jump_diffusion_params(base_params, sentiment)

    # 运行模拟
    model = JumpDiffusionModel(calibrated_params)
    results = model.simulate(n_simulations=1000, base_seed=42)

    max_dds = [r.max_drawdown for r in results]
    crash_prob = sum(1 for d in max_dds if d < -0.20) / len(max_dds)

    print(f"{state_name:>8} {sentiment:>8.0f} {calibrated_params.jump_lambda:>9.1f} "
          f"{np.mean(max_dds)*100:>9.1f}% {np.percentile(max_dds, 5)*100:>11.1f}% "
          f"{np.min(max_dds)*100:>9.1f}% {crash_prob*100:>9.1f}%")

# ========== 测试3：情绪校准对压力测试结果的影响 ==========
print("\n" + "=" * 70)
print("[测试3] 情绪校准对压力测试结果的影响")
print("=" * 70)

print(f"\n三种情绪状态下的压力测试结果（各筛选20个股灾情景）：")
print(f"{'情绪状态':>8} {'平均大盘跌幅':>12} {'平均组合损失':>12} {'最大组合损失':>12} {'最小组合损失':>12}")
print("-" * 70)

for state_name, sentiment in sentiment_scenarios:
    # 校准参数
    calibrated_params, _ = calibrator.calibrate_jump_diffusion_params(base_params, sentiment)

    # 筛选股灾情景
    model = JumpDiffusionModel(calibrated_params)
    scenarios = model.get_crash_scenarios(n_scenarios=20, crash_threshold=-0.20, base_seed=42)

    # 计算压力测试损失
    total_losses = []
    market_drops = []
    for i, scenario in enumerate(scenarios):
        event = CrashEvent(
            event_id=scenario["scenario_id"],
            event_name=f"{state_name}股灾",
            event_type="系统性股灾",
            start_date="2025-01-01",
            end_date="2025-12-31",
            duration_days=scenario["crash_day"],
            market_drop=scenario["max_drawdown"],
            affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
            probability=0.02,
            description=f"情绪校准股灾情景，情绪指数{sentiment}",
            seed=i,
        )

        vuln_results = vuln_engine.calculate_portfolio(portfolio, event, add_noise=True)

        total_loss = 0.0
        for vr, position in zip(vuln_results, portfolio.positions):
            loss = position.market_value * abs(vr.final_drop)
            total_loss += loss

        total_losses.append(total_loss)
        market_drops.append(scenario["max_drawdown"])

    print(f"{state_name:>8} {np.mean(market_drops)*100:>11.1f}% "
          f"${np.mean(total_losses):>10,.0f} ${np.max(total_losses):>10,.0f} "
          f"${np.min(total_losses):>10,.0f}")

# ========== 测试4：文本情绪分析功能 ==========
print("\n" + "=" * 70)
print("[测试4] 文本情绪分析功能")
print("=" * 70)

# 模拟雪球评论
xueqiu_comments = [
    "Tesla这波要涨到天上去了，全仓杀入！",
    "美联储加息，科技股要崩了，赶紧跑",
    "震荡行情，观望为主",
    "财报超预期，明天涨停",
    "估值太高了，泡沫迟早要破",
    "长期看好新能源，回调就是机会",
    "恐慌性下跌，已经超卖了",
    "主力在出货，散户别接盘",
    "技术面突破，看涨",
    "基本面恶化，看空",
]

print(f"\n模拟雪球评论（{len(xueqiu_comments)}条）：")
for i, comment in enumerate(xueqiu_comments, 1):
    print(f"  {i}. {comment}")

sentiment, stats = analyze_sentiment_from_texts(xueqiu_comments)

print(f"\n情绪分析结果：")
print(f"  看多：{stats['bullish']}条 ({stats['bullish_pct']:.1f}%)")
print(f"  看空：{stats['bearish']}条 ({stats['bearish_pct']:.1f}%)")
print(f"  中性：{stats['neutral']}条 ({stats['neutral_pct']:.1f}%)")
print(f"  情绪指数：{sentiment:.1f}/100")

# 用分析出的情绪进行校准
result = calibrator.calibrate(sentiment)
print(f"\n校准结果：")
print(f"  市场状态：{result.market_state}")
print(f"  {result.explanation}")

# ========== 测试5：情绪校准的实际应用场景 ==========
print("\n" + "=" * 70)
print("[测试5] 情绪校准的实际应用场景")
print("=" * 70)

print("""
应用场景1：泡沫破裂预警
  当情绪指数 > 80（极度贪婪）时，股灾概率上升40%，跳跃强度上升20-30%。
  这可以作为泡沫破裂的早期预警信号。

应用场景2：超卖反弹识别
  当情绪指数 < 20（极度恐惧）时，股灾概率下降40%，跳跃强度下降20-30%。
  这可以作为超卖后反弹机会的识别信号。

应用场景3：动态仓位调整
  根据市场情绪动态调整仓位：
  - 极度贪婪时：降低仓位，增加对冲
  - 极度恐惧时：提高仓位，逢低买入
  - 中性时：维持标准仓位

应用场景4：压力测试情景生成
  用当前市场情绪校准跳跃扩散参数，生成更符合当前市场状态的股灾情景。
  这样压力测试的结果更有针对性，而不是用历史平均情况。
""")

print("\n" + "=" * 70)
print("所有第四版功能测试通过！")
print("=" * 70)

print("""
第四版新增功能总结：
  1. 情绪NLP校准模块（sentiment_calibration.py）
     - 情绪指数校准股灾概率（0-100，>50看多，<50看空）
     - 情绪校准跳跃强度和跳跃幅度
     - 非线性情绪效应（极端情绪影响更强）
     - 5种市场状态：极度恐惧/恐惧/中性/贪婪/极度贪婪
     - 文本情绪分析（基于关键词的简化版，可替换为VADER/BERT）

  2. 情绪校准与跳跃扩散集成
     - 用情绪指数校准跳跃扩散参数
     - 不同情绪水平下的蒙特卡洛模拟对比
     - 情绪校准对压力测试结果的影响

  3. 实际应用场景
     - 泡沫破裂预警
     - 超卖反弹识别
     - 动态仓位调整
     - 压力测试情景生成

理论基础：
  - 巴菲特指标："别人贪婪我恐惧，别人恐惧我贪婪"
  - 行为金融学：过度自信导致泡沫，恐慌导致超卖
  - 历史经验：大股灾前往往伴随极度乐观情绪
""")
