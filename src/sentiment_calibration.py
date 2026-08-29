"""
情绪NLP校准模块

用市场情绪（从雪球/Reddit/评论区等来源分析得到）校准股灾概率和跳跃扩散参数。

核心思想：
- 情绪极度乐观（>80）→ 泡沫破裂风险增加，股灾概率和跳跃强度上升
- 情绪极度悲观（<20）→ 恐慌可能已经过度，反弹概率增加，股灾概率下降
- 情绪中性（40-60）→ 正常概率

情绪与股灾的关系参考：
- 巴菲特指标："别人贪婪我恐惧，别人恐惧我贪婪"
- 行为金融学：过度自信导致泡沫，恐慌导致超卖
- 历史经验：大股灾前往往伴随极度乐观情绪
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class SentimentParams:
    """情绪校准参数"""
    # 情绪指数（0-100，>50看多，<50看空）
    sentiment_index: float = 50.0

    # 情绪对股灾概率的影响强度
    sentiment_prob_sensitivity: float = 0.5  # 0=无影响，1=强影响

    # 情绪对跳跃强度的影响强度
    sentiment_jump_sensitivity: float = 0.3

    # 情绪阈值
    extreme_greed_threshold: float = 80.0  # 极度贪婪阈值
    extreme_fear_threshold: float = 20.0    # 极度恐惧阈值

    # 基础股灾概率（情绪中性时的年化概率）
    base_crash_probability: float = 0.05  # 5%年化概率


@dataclass
class CalibratedHazardParams:
    """校准后的危险参数"""
    # 校准后的股灾年化概率
    crash_probability: float

    # 校准后的跳跃扩散参数调整因子
    jump_intensity_multiplier: float  # 跳跃强度乘数
    jump_size_multiplier: float        # 跳跃幅度乘数

    # 市场状态描述
    market_state: str  # "极度贪婪"、"贪婪"、"中性"、"恐惧"、"极度恐惧"

    # 校准说明
    explanation: str


class SentimentCalibrator:
    """
    情绪校准器

    用法：
        calibrator = SentimentCalibrator()
        calibrated = calibrator.calibrate(sentiment_index=75)
        print(f"校准后的股灾概率: {calibrated.crash_probability*100:.1f}%")
    """

    def __init__(self, params: Optional[SentimentParams] = None):
        self.params = params or SentimentParams()

    def calibrate(self, sentiment_index: float) -> CalibratedHazardParams:
        """
        根据情绪指数校准危险参数

        参数：
            sentiment_index: 情绪指数（0-100，>50看多，<50看空）

        返回：
            校准后的危险参数
        """
        p = self.params

        # 限制情绪指数在0-100之间
        sentiment = np.clip(sentiment_index, 0, 100)

        # 判断市场状态
        if sentiment >= p.extreme_greed_threshold:
            market_state = "极度贪婪"
        elif sentiment >= 65:
            market_state = "贪婪"
        elif sentiment >= 35:
            market_state = "中性"
        elif sentiment >= p.extreme_fear_threshold:
            market_state = "恐惧"
        else:
            market_state = "极度恐惧"

        # 计算情绪偏离度（相对于中性50）
        # 正偏离=乐观，负偏离=悲观
        sentiment_deviation = (sentiment - 50) / 50  # 归一化到[-1, 1]

        # 校准股灾概率
        # 核心逻辑：
        # - 极度乐观 → 股灾概率上升（泡沫破裂风险）
        # - 极度悲观 → 股灾概率下降（恐慌可能已过度，反弹概率增加）
        # - 用非线性函数，极端情绪的影响更强
        prob_adjustment = self._nonlinear_sentiment_effect(
            sentiment_deviation,
            strength=p.sentiment_prob_sensitivity,
        )
        calibrated_prob = p.base_crash_probability * (1 + prob_adjustment)
        calibrated_prob = np.clip(calibrated_prob, 0.001, 0.5)  # 限制在合理范围

        # 校准跳跃强度
        # 极度乐观 → 跳跃强度增加（泡沫破裂时的跳跃更剧烈）
        # 极度悲观 → 跳跃强度可能已经释放，下降
        jump_intensity_mult = 1 + self._nonlinear_sentiment_effect(
            sentiment_deviation,
            strength=p.sentiment_jump_sensitivity,
        )
        jump_intensity_mult = np.clip(jump_intensity_mult, 0.3, 3.0)

        # 校准跳跃幅度
        # 极度乐观 → 向下跳跃幅度增加（泡沫破裂时跌得更狠）
        # 极度悲观 → 向下跳跃幅度可能减少（已经跌了很多）
        jump_size_mult = 1 + self._nonlinear_sentiment_effect(
            sentiment_deviation,
            strength=p.sentiment_jump_sensitivity * 0.8,
        )
        jump_size_mult = np.clip(jump_size_mult, 0.3, 3.0)

        # 生成校准说明
        explanation = self._generate_explanation(
            sentiment=sentiment,
            market_state=market_state,
            base_prob=p.base_crash_probability,
            calibrated_prob=calibrated_prob,
            jump_intensity_mult=jump_intensity_mult,
            jump_size_mult=jump_size_mult,
        )

        return CalibratedHazardParams(
            crash_probability=calibrated_prob,
            jump_intensity_multiplier=jump_intensity_mult,
            jump_size_multiplier=jump_size_mult,
            market_state=market_state,
            explanation=explanation,
        )

    def _nonlinear_sentiment_effect(self, deviation: float, strength: float) -> float:
        """
        非线性情绪效应函数

        用三次函数使得极端情绪的影响更强：
        effect = strength * (deviation + 0.3 * deviation^3)

        这样：
        - 中性情绪（deviation≈0）→ 影响很小
        - 极端情绪（deviation≈±1）→ 影响被放大
        """
        return strength * (deviation + 0.3 * deviation ** 3)

    def _generate_explanation(
        self,
        sentiment: float,
        market_state: str,
        base_prob: float,
        calibrated_prob: float,
        jump_intensity_mult: float,
        jump_size_mult: float,
    ) -> str:
        """生成校准说明"""
        prob_change = (calibrated_prob / base_prob - 1) * 100

        if sentiment >= 80:
            state_desc = "市场处于极度贪婪状态，泡沫破裂风险显著上升"
        elif sentiment >= 65:
            state_desc = "市场偏乐观，需警惕回调风险"
        elif sentiment >= 35:
            state_desc = "市场情绪中性，股灾概率维持基础水平"
        elif sentiment >= 20:
            state_desc = "市场偏悲观，恐慌可能已部分释放"
        else:
            state_desc = "市场处于极度恐惧状态，超卖后反弹概率上升，股灾概率下降"

        return (
            f"情绪指数 {sentiment:.0f}/100（{market_state}）。{state_desc}。"
            f"股灾年化概率从 {base_prob*100:.1f}% 校准为 {calibrated_prob*100:.1f}%"
            f"（变化 {prob_change:+.1f}%）。"
            f"跳跃强度乘数 {jump_intensity_mult:.2f}x，跳跃幅度乘数 {jump_size_mult:.2f}x。"
        )

    def calibrate_jump_diffusion_params(
        self,
        base_params,
        sentiment_index: float,
    ):
        """
        校准跳跃扩散参数

        参数：
            base_params: 基础跳跃扩散参数（JumpDiffusionParams对象）
            sentiment_index: 情绪指数

        返回：
            校准后的跳跃扩散参数（新的JumpDiffusionParams对象）
        """
        calibrated = self.calibrate(sentiment_index)

        # 复制基础参数并应用校准
        from src.jump_diffusion import JumpDiffusionParams

        calibrated_params = JumpDiffusionParams(
            mu=base_params.mu,
            sigma=base_params.sigma,
            jump_lambda=base_params.jump_lambda * calibrated.jump_intensity_multiplier,
            jump_mu=base_params.jump_mu * calibrated.jump_size_multiplier,
            jump_sigma=base_params.jump_sigma * calibrated.jump_size_multiplier,
            initial_price=base_params.initial_price,
            n_days=base_params.n_days,
            dt=base_params.dt,
        )

        return calibrated_params, calibrated


def analyze_sentiment_from_texts(texts: list) -> Tuple[float, dict]:
    """
    从文本列表分析情绪指数（简化版）

    这个函数提供了一个简单的基于关键词的情绪分析，
    实际使用时可以替换为更复杂的NLP模型（如VADER、BERT等）。

    参数：
        texts: 评论文本列表

    返回：
        (情绪指数, 详细统计)
    """
    # 看多关键词
    bullish_words = [
        "涨", "升", "多", "买", "利好", "突破", "反弹", "牛市",
        "看好", "乐观", "上涨", "拉升", "走强", "抄底", "加仓",
        "to the moon", "bull", "buy", "long", "rally", "surge",
        "breakout", "undervalued", "growth", "profit",
    ]

    # 看空关键词
    bearish_words = [
        "跌", "降", "空", "卖", "利空", "跌破", "崩盘", "熊市",
        "看空", "悲观", "下跌", "跳水", "走弱", "割肉", "减仓",
        "crash", "bear", "sell", "short", "dump", "plunge",
        "breakdown", "overvalued", "decline", "loss", "bubble",
    ]

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for text in texts:
        text_lower = str(text).lower()
        is_bullish = any(word in text_lower for word in bullish_words)
        is_bearish = any(word in text_lower for word in bearish_words)

        if is_bullish and not is_bearish:
            bullish_count += 1
        elif is_bearish and not is_bullish:
            bearish_count += 1
        else:
            neutral_count += 1

    total = len(texts)
    if total == 0:
        return 50.0, {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0}

    # 计算情绪指数（0-100）
    # 50 = 中性，>50 = 看多，<50 = 看空
    sentiment_index = 50 + (bullish_count - bearish_count) / total * 50
    sentiment_index = np.clip(sentiment_index, 0, 100)

    stats = {
        "bullish": bullish_count,
        "bearish": bearish_count,
        "neutral": neutral_count,
        "total": total,
        "bullish_pct": bullish_count / total * 100,
        "bearish_pct": bearish_count / total * 100,
        "neutral_pct": neutral_count / total * 100,
    }

    return sentiment_index, stats


if __name__ == "__main__":
    # 简单测试
    print("=" * 60)
    print("情绪NLP校准模块测试")
    print("=" * 60)

    calibrator = SentimentCalibrator()

    # 测试不同情绪水平
    test_sentiments = [10, 20, 30, 40, 50, 60, 70, 80, 90]

    print("\n不同情绪指数的校准结果：")
    print(f"{'情绪指数':>8} {'市场状态':>8} {'股灾概率':>10} {'跳跃强度乘数':>12} {'跳跃幅度乘数':>12}")
    print("-" * 60)

    for sentiment in test_sentiments:
        result = calibrator.calibrate(sentiment)
        print(f"{sentiment:>8.0f} {result.market_state:>8} "
              f"{result.crash_probability*100:>9.1f}% "
              f"{result.jump_intensity_multiplier:>11.2f}x "
              f"{result.jump_size_multiplier:>11.2f}x")

    # 详细说明
    print("\n" + "=" * 60)
    print("详细校准说明：")
    print("=" * 60)

    for sentiment in [15, 50, 85]:
        result = calibrator.calibrate(sentiment)
        print(f"\n情绪指数 {sentiment}：")
        print(f"  {result.explanation}")

    # 测试文本情绪分析
    print("\n" + "=" * 60)
    print("文本情绪分析测试：")
    print("=" * 60)

    test_texts = [
        "这只股票要涨了，赶紧买入",
        "市场崩盘了，快跑",
        "今天震荡整理，观望为主",
        "利好消息，突破在即",
        "利空出尽，反弹可期",
        "泡沫太大了，迟早要跌",
        "估值合理，长期看好",
        "恐慌性抛售，已经超卖",
    ]

    sentiment, stats = analyze_sentiment_from_texts(test_texts)
    print(f"\n测试文本数：{stats['total']}")
    print(f"看多：{stats['bullish']} ({stats['bullish_pct']:.1f}%)")
    print(f"看空：{stats['bearish']} ({stats['bearish_pct']:.1f}%)")
    print(f"中性：{stats['neutral']} ({stats['neutral_pct']:.1f}%)")
    print(f"情绪指数：{sentiment:.1f}/100")

    # 用分析出的情绪进行校准
    result = calibrator.calibrate(sentiment)
    print(f"\n校准结果：")
    print(f"  {result.explanation}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
