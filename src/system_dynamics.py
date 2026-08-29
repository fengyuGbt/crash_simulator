"""
系统动力学反馈回路模块 - 危险层升级

模拟股灾中的内生反馈机制：
  价格下跌 → 杠杆账户爆仓 → 强制卖出 → 价格更跌 → 更多爆仓
  价格下跌 → 情绪恐慌 → 散户抛售 → 价格更跌 → 更恐慌
  流动性枯竭 → 买卖价差飙升 → 被迫以更低价卖出 → 价格更跌

参考Stella/Vensim的系统动力学建模思路，用Python实现存量-流量模型。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class FeedbackParams:
    """反馈回路参数"""
    # 杠杆爆仓反馈
    leverage_ratio: float = 1.5          # 市场平均杠杆率（1.5倍）
    margin_call_threshold: float = 0.85   # 维持保证金比例（85%）
    forced_sell_ratio: float = 0.3        # 爆仓后强制卖出比例（30%仓位）

    # 情绪恐慌反馈
    sentiment_sensitivity: float = 2.0    # 情绪对价格下跌的敏感度
    panic_sell_ratio: float = 0.15        # 恐慌时散户抛售比例（15%）

    # 流动性枯竭反馈
    liquidity_sensitivity: float = 1.5    # 流动性对下跌的敏感度
    spread_widening: float = 0.02         # 买卖价差扩大幅度（2%）

    # 政策干预（可选）
    policy_intervention: bool = False      # 是否启用政策干预
    intervention_threshold: float = -0.20  # 干预触发阈值（跌20%）
    intervention_strength: float = 0.3     # 干预强度（托底30%）


@dataclass
class SimulationState:
    """模拟状态（存量）"""
    day: int = 0
    price: float = 100.0           # 价格指数（初始100）
    leverage_exposure: float = 50.0  # 杠杆敞口（初始50%）
    sentiment: float = 0.5         # 情绪指数（0-1，0.5中性）
    liquidity: float = 1.0          # 流动性指数（1=正常，0=枯竭）
    forced_selling: float = 0.0     # 当前强制卖出压力
    panic_selling: float = 0.0       # 当前恐慌卖出压力
    cumulative_drop: float = 0.0     # 累计跌幅


class SystemDynamicsEngine:
    """系统动力学引擎 - 模拟股灾反馈回路"""

    def __init__(self, params: Optional[FeedbackParams] = None):
        """
        初始化系统动力学引擎
        :param params: 反馈回路参数，None使用默认值
        """
        self.params = params or FeedbackParams()

    def simulate(
        self,
        initial_shock: float = -0.10,
        n_days: int = 60,
        random_seed: int = 42,
    ) -> pd.DataFrame:
        """
        运行系统动力学模拟

        :param initial_shock: 初始冲击（如-0.10表示初始跌10%）
        :param n_days: 模拟天数
        :param random_seed: 随机种子
        :return: 模拟结果DataFrame
        """
        np.random.seed(random_seed)
        params = self.params

        # 初始化状态
        state = SimulationState()
        state.price = 100.0
        state.leverage_exposure = 50.0
        state.sentiment = 0.5
        state.liquidity = 1.0

        results = []

        # 第0天：初始冲击
        state.price = 100 * (1 + initial_shock)
        state.cumulative_drop = initial_shock
        state.day = 0
        results.append(self._record_state(state))

        # 逐日模拟
        for day in range(1, n_days + 1):
            state.day = day

            # 1. 计算反馈回路产生的卖出压力
            forced_selling = self._calc_leverage_feedback(state, params)
            panic_selling = self._calc_sentiment_feedback(state, params)
            liquidity_pressure = self._calc_liquidity_feedback(state, params)

            # 2. 总卖出压力
            total_sell_pressure = forced_selling + panic_selling + liquidity_pressure

            # 3. 政策干预（如果启用）
            intervention = 0.0
            if params.policy_intervention and state.cumulative_drop < params.intervention_threshold:
                intervention = params.intervention_strength * abs(state.cumulative_drop)
                total_sell_pressure -= intervention

            # 4. 价格变化（卖出压力导致价格下跌，加上随机噪声）
            price_impact = -total_sell_pressure * 0.5  # 卖出压力对价格的影响
            random_noise = np.random.normal(0, 0.01)   # 随机噪声
            daily_return = price_impact + random_noise

            # 限制单日跌幅（最多-20%，模拟涨跌停或市场机制）
            daily_return = max(-0.20, daily_return)

            # 5. 更新状态
            old_price = state.price
            state.price = state.price * (1 + daily_return)
            state.cumulative_drop = state.price / 100 - 1

            # 更新杠杆敞口（价格下跌导致杠杆率上升，部分爆仓后敞口下降）
            if daily_return < 0:
                # 价格下跌，杠杆率上升
                state.leverage_exposure = min(100, state.leverage_exposure * (1 + abs(daily_return) * 0.5))
                # 爆仓部分被强平，敞口下降
                state.leverage_exposure -= forced_selling * 100
            else:
                # 价格回升，杠杆率下降
                state.leverage_exposure = max(10, state.leverage_exposure * (1 - daily_return * 0.3))

            # 更新情绪（价格下跌导致恐慌，回升缓解）
            sentiment_change = -daily_return * params.sentiment_sensitivity
            state.sentiment = max(0.0, min(1.0, state.sentiment + sentiment_change * 0.1))
            # 情绪有均值回归趋势
            state.sentiment = state.sentiment * 0.95 + 0.5 * 0.05

            # 更新流动性（下跌导致流动性枯竭）
            if daily_return < 0:
                state.liquidity = max(0.1, state.liquidity * (1 - abs(daily_return) * params.liquidity_sensitivity))
            else:
                state.liquidity = min(1.0, state.liquidity * (1 + daily_return * 0.5))

            # 记录卖出压力
            state.forced_selling = forced_selling
            state.panic_selling = panic_selling

            results.append(self._record_state(state))

        return pd.DataFrame(results)

    def _calc_leverage_feedback(self, state: SimulationState, params: FeedbackParams) -> float:
        """计算杠杆爆仓反馈产生的卖出压力"""
        # 杠杆率超过阈值时触发爆仓
        leverage_ratio = state.leverage_exposure / 50  # 相对初始杠杆率
        if leverage_ratio > params.margin_call_threshold:
            # 爆仓比例与杠杆超标程度成正比
            excess_leverage = (leverage_ratio - params.margin_call_threshold) / params.margin_call_threshold
            forced_sell = excess_leverage * params.forced_sell_ratio
            return min(0.5, forced_sell)  # 最多50%仓位被强平
        return 0.0

    def _calc_sentiment_feedback(self, state: SimulationState, params: FeedbackParams) -> float:
        """计算情绪恐慌反馈产生的卖出压力"""
        # 情绪低于阈值时触发恐慌卖出
        if state.sentiment < 0.3:
            panic_level = (0.3 - state.sentiment) / 0.3  # 0-1的恐慌程度
            panic_sell = panic_level * params.panic_sell_ratio
            return panic_sell
        return 0.0

    def _calc_liquidity_feedback(self, state: SimulationState, params: FeedbackParams) -> float:
        """计算流动性枯竭反馈产生的卖出压力"""
        # 流动性不足时，被迫以更低价卖出，放大下跌
        if state.liquidity < 0.5:
            liquidity_pressure = (0.5 - state.liquidity) * params.spread_widening * 10
            return liquidity_pressure
        return 0.0

    def _record_state(self, state: SimulationState) -> Dict:
        """记录当前状态"""
        return {
            "day": state.day,
            "price": round(state.price, 2),
            "cumulative_drop": round(state.cumulative_drop, 4),
            "leverage_exposure": round(state.leverage_exposure, 2),
            "sentiment": round(state.sentiment, 4),
            "liquidity": round(state.liquidity, 4),
            "forced_selling": round(state.forced_selling, 4),
            "panic_selling": round(state.panic_selling, 4),
        }

    def get_crash_summary(self, sim_df: pd.DataFrame) -> Dict:
        """
        获取股灾模拟摘要

        :param sim_df: 模拟结果DataFrame
        :return: 摘要字典
        """
        max_drop = sim_df["cumulative_drop"].min()
        max_drop_day = sim_df.loc[sim_df["cumulative_drop"].idxmin(), "day"]
        recovery_day = None
        for _, row in sim_df.iterrows():
            if row["day"] > max_drop_day and row["cumulative_drop"] > max_drop * 0.5:
                recovery_day = row["day"]
                break

        return {
            "初始价格": 100.0,
            "最低价格": round(sim_df["price"].min(), 2),
            "最大跌幅": round(max_drop, 4),
            "最大跌幅天数": int(max_drop_day),
            "恢复天数": recovery_day,
            "模拟天数": len(sim_df),
            "平均杠杆敞口": round(sim_df["leverage_exposure"].mean(), 2),
            "最低情绪": round(sim_df["sentiment"].min(), 4),
            "最低流动性": round(sim_df["liquidity"].min(), 4),
            "最大强制卖出": round(sim_df["forced_selling"].max(), 4),
            "最大恐慌卖出": round(sim_df["panic_selling"].max(), 4),
        }

    def generate_crash_scenarios(
        self,
        n_scenarios: int = 100,
        initial_shock_range: Tuple[float, float] = (-0.05, -0.20),
        n_days: int = 60,
        base_seed: int = 42,
    ) -> List[Dict]:
        """
        生成多个股灾情景（用于蒙特卡洛事件集）

        :param n_scenarios: 情景数量
        :param initial_shock_range: 初始冲击范围
        :param n_days: 模拟天数
        :param base_seed: 基础随机种子
        :return: 情景列表，每个包含最大跌幅、持续时间等
        """
        scenarios = []
        for i in range(n_scenarios):
            initial_shock = np.random.uniform(initial_shock_range[0], initial_shock_range[1])
            sim_df = self.simulate(
                initial_shock=initial_shock,
                n_days=n_days,
                random_seed=base_seed + i,
            )
            summary = self.get_crash_summary(sim_df)
            summary["initial_shock"] = round(initial_shock, 4)
            summary["scenario_id"] = f"SD_{i:04d}"
            scenarios.append(summary)

        return scenarios
