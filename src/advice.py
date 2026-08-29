"""
仓位建议模块 - 基于风险预算的仓位管理

核心原则：风险预算固定 → 波动越大，止损距离越宽 → 能买的仓位越小
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

from .exposure import Portfolio, Position
from .loss import RiskMetrics


@dataclass
class PositionAdvice:
    """单只股票的仓位建议"""
    ticker: str
    name: str
    sector: str
    current_position_value: float   # 当前持仓市值
    current_weight: float           # 当前仓位占比
    volatility: float               # 波动率（年化）
    stop_loss_distance: float       # 建议止损距离（百分比）
    risk_budget: float              # 分配给该股的风险预算（金额）
    suggested_position_value: float # 建议持仓市值
    suggested_weight: float         # 建议仓位占比
    adjustment: float               # 调整金额（正数=加仓，负数=减仓）
    adjustment_pct: float           # 调整比例


@dataclass
class PortfolioAdvice:
    """投资组合的仓位建议"""
    total_capital: float            # 总本金
    total_risk_budget: float        # 总风险预算（单笔最大亏损金额）
    total_risk_budget_pct: float    # 总风险预算比例（如2%）
    current_total_value: float      # 当前持仓总市值
    suggested_total_value: float    # 建议持仓总市值
    suggested_cash: float           # 建议持有现金
    current_leverage: float         # 当前仓位（持仓/本金）
    suggested_leverage: float       # 建议仓位
    position_advices: List[PositionAdvice] = field(default_factory=list)


class PositionAdvisor:
    """仓位建议器 - 基于风险预算的仓位管理"""

    def __init__(
        self,
        total_risk_budget_pct: float = 0.02,  # 单笔最大亏损2%
        default_stop_loss_atr_multiple: float = 2.0,  # 止损距离=2倍ATR
        min_position_pct: float = 0.05,  # 最小仓位5%
        max_single_position_pct: float = 0.30,  # 单只股票最大仓位30%
    ):
        """
        初始化仓位建议器

        :param total_risk_budget_pct: 总风险预算比例（单笔最大亏损占本金比例）
        :param default_stop_loss_atr_multiple: 默认止损距离的ATR倍数
        :param min_position_pct: 最小仓位比例
        :param max_single_position_pct: 单只股票最大仓位比例
        """
        self.total_risk_budget_pct = total_risk_budget_pct
        self.default_stop_loss_atr_multiple = default_stop_loss_atr_multiple
        self.min_position_pct = min_position_pct
        self.max_single_position_pct = max_single_position_pct

    def calculate_stop_loss_distance(
        self,
        volatility: float,
        atr_multiple: Optional[float] = None,
    ) -> float:
        """
        计算建议止损距离

        原理：波动越大，止损距离需要越宽，否则容易被正常波动震出来
        简化：止损距离 = ATR倍数 × 波动率（年化转日度）

        :param volatility: 年化波动率
        :param atr_multiple: ATR倍数，None使用默认值
        :return: 止损距离（百分比，如0.15表示15%）
        """
        if atr_multiple is None:
            atr_multiple = self.default_stop_loss_atr_multiple

        # 年化波动率转日度波动率（假设252个交易日）
        daily_vol = volatility / np.sqrt(252)
        # 止损距离 = ATR倍数 × 日度波动率 × 根号(持仓天数)
        # 简化：假设持仓20天，止损距离 = atr_multiple × daily_vol × sqrt(20)
        stop_loss = atr_multiple * daily_vol * np.sqrt(20)

        # 限制在5%到50%之间
        return max(0.05, min(0.50, stop_loss))

    def calculate_position_advice(
        self,
        position: Position,
        total_capital: float,
        risk_budget_per_position: float,
        volatility: Optional[float] = None,
    ) -> PositionAdvice:
        """
        计算单只股票的仓位建议

        公式：建议仓位 = 风险预算 / 止损距离
        （因为如果跌到止损线，亏损 = 仓位 × 止损距离 = 风险预算）

        :param position: 持仓
        :param total_capital: 总本金
        :param risk_budget_per_position: 分配给该股的风险预算（金额）
        :param volatility: 年化波动率，None则用beta估算
        :return: 仓位建议
        """
        # 估算波动率（如果没提供）
        if volatility is None:
            # 简化：用beta × 大盘年化波动率（假设20%）
            volatility = position.beta * 0.20

        # 计算止损距离
        stop_loss_distance = self.calculate_stop_loss_distance(volatility)

        # 建议仓位 = 风险预算 / 止损距离
        suggested_value = risk_budget_per_position / stop_loss_distance

        # 限制单只股票最大仓位
        max_value = total_capital * self.max_single_position_pct
        suggested_value = min(suggested_value, max_value)

        # 计算当前仓位
        current_value = position.market_value
        current_weight = current_value / total_capital if total_capital > 0 else 0
        suggested_weight = suggested_value / total_capital if total_capital > 0 else 0

        # 调整金额
        adjustment = suggested_value - current_value
        adjustment_pct = adjustment / current_value if current_value > 0 else float('inf')

        return PositionAdvice(
            ticker=position.ticker,
            name=position.name,
            sector=position.sector,
            current_position_value=current_value,
            current_weight=current_weight,
            volatility=volatility,
            stop_loss_distance=stop_loss_distance,
            risk_budget=risk_budget_per_position,
            suggested_position_value=suggested_value,
            suggested_weight=suggested_weight,
            adjustment=adjustment,
            adjustment_pct=adjustment_pct,
        )

    def calculate_portfolio_advice(
        self,
        portfolio: Portfolio,
        total_capital: float,
        volatilities: Optional[Dict[str, float]] = None,
        risk_budget_pct: Optional[float] = None,
    ) -> PortfolioAdvice:
        """
        计算投资组合的仓位建议

        原理：
        1. 总风险预算 = 本金 × 风险预算比例（如2%）
        2. 平均分配给每只股票（或按风险贡献分配）
        3. 每只股票的建议仓位 = 分配的风险预算 / 止损距离
        4. 波动大的股票，止损距离宽，建议仓位小

        :param portfolio: 投资组合
        :param total_capital: 总本金
        :param volatilities: 各股票的年化波动率字典，None则用beta估算
        :param risk_budget_pct: 风险预算比例，None使用默认值
        :return: 投资组合仓位建议
        """
        if risk_budget_pct is not None:
            self.total_risk_budget_pct = risk_budget_pct

        total_risk_budget = total_capital * self.total_risk_budget_pct
        n_positions = len(portfolio.positions)

        if n_positions == 0:
            return PortfolioAdvice(
                total_capital=total_capital,
                total_risk_budget=total_risk_budget,
                total_risk_budget_pct=self.total_risk_budget_pct,
                current_total_value=0,
                suggested_total_value=0,
                suggested_cash=total_capital,
                current_leverage=0,
                suggested_leverage=0,
            )

        # 平均分配风险预算（简化版，后面可以按风险贡献分配）
        risk_budget_per_position = total_risk_budget / n_positions

        # 计算每只股票的建议
        position_advices = []
        total_suggested_value = 0.0
        for position in portfolio.positions:
            vol = volatilities.get(position.ticker) if volatilities else None
            advice = self.calculate_position_advice(
                position, total_capital, risk_budget_per_position, vol
            )
            position_advices.append(advice)
            total_suggested_value += advice.suggested_position_value

        # 组合层面
        current_total_value = portfolio.total_value
        suggested_cash = total_capital - total_suggested_value
        current_leverage = current_total_value / total_capital if total_capital > 0 else 0
        suggested_leverage = total_suggested_value / total_capital if total_capital > 0 else 0

        return PortfolioAdvice(
            total_capital=total_capital,
            total_risk_budget=total_risk_budget,
            total_risk_budget_pct=self.total_risk_budget_pct,
            current_total_value=current_total_value,
            suggested_total_value=total_suggested_value,
            suggested_cash=max(0, suggested_cash),
            current_leverage=current_leverage,
            suggested_leverage=suggested_leverage,
            position_advices=position_advices,
        )

    def advice_to_dataframe(self, advice: PortfolioAdvice) -> pd.DataFrame:
        """将仓位建议转换为DataFrame"""
        data = []
        for pa in advice.position_advices:
            data.append({
                "股票代码": pa.ticker,
                "公司名称": pa.name,
                "行业": pa.sector,
                "当前市值": pa.current_position_value,
                "当前仓位": pa.current_weight,
                "年化波动率": pa.volatility,
                "建议止损距离": pa.stop_loss_distance,
                "风险预算": pa.risk_budget,
                "建议市值": pa.suggested_position_value,
                "建议仓位": pa.suggested_weight,
                "调整金额": pa.adjustment,
                "调整方向": "加仓" if pa.adjustment > 0 else "减仓" if pa.adjustment < 0 else "持有",
            })
        return pd.DataFrame(data)
