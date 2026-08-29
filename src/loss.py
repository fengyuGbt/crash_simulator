"""
损失计算层(Loss) - 蒙特卡洛模拟 + 风险度量

对应巨灾建模中的损失计算：危险×暴露×脆弱性 → 损失分布 → VaR/CVaR
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

from .exposure import Portfolio, Position
from .hazard import CrashEvent, HazardEngine
from .vulnerability import VulnerabilityEngine, VulnerabilityResult


@dataclass
class LossResult:
    """单次事件的损失计算结果"""
    event_id: str
    event_name: str
    market_drop: float
    portfolio_drop: float       # 投资组合加权跌幅
    total_loss: float           # 总损失金额
    total_loss_pct: float       # 总损失百分比（相对于组合总市值）
    position_losses: Dict[str, float] = field(default_factory=dict)  # 各股票损失金额
    position_drops: Dict[str, float] = field(default_factory=dict)   # 各股票跌幅


@dataclass
class RiskMetrics:
    """风险度量指标"""
    expected_loss: float         # 预期损失（概率加权平均）
    expected_loss_pct: float     # 预期损失百分比
    var_95: float                # 95% VaR（95%置信度下的最大损失）
    var_95_pct: float
    var_99: float                # 99% VaR
    var_99_pct: float
    cvar_95: float               # 95% CVaR（超过VaR后的平均损失，尾部期望）
    cvar_95_pct: float
    cvar_99: float               # 99% CVaR
    cvar_99_pct: float
    max_loss: float              # 最大损失（最坏情况）
    max_loss_pct: float
    min_loss: float              # 最小损失（最好情况，可能为正表示盈利）
    min_loss_pct: float
    loss_std: float              # 损失标准差
    loss_std_pct: float
    max_drawdown: float          # 最大回撤（近似，用最大损失代替）
    max_drawdown_pct: float


class LossEngine:
    """损失引擎 - 蒙特卡洛模拟 + 风险度量"""

    def __init__(
        self,
        hazard_engine: Optional[HazardEngine] = None,
        vulnerability_engine: Optional[VulnerabilityEngine] = None,
    ):
        """
        初始化损失引擎
        :param hazard_engine: 危险引擎，None则创建默认
        :param vulnerability_engine: 脆弱性引擎，None则创建默认
        """
        self.hazard_engine = hazard_engine or HazardEngine()
        self.vulnerability_engine = vulnerability_engine or VulnerabilityEngine()

    def calculate_single_event(
        self,
        portfolio: Portfolio,
        event: CrashEvent,
        add_noise: bool = True,
    ) -> LossResult:
        """
        计算单个股灾事件下的投资组合损失

        :param portfolio: 投资组合
        :param event: 股灾事件
        :param add_noise: 是否添加个股残差
        :return: 损失结果
        """
        if portfolio.total_value == 0:
            return LossResult(
                event_id=event.event_id,
                event_name=event.event_name,
                market_drop=event.market_drop,
                portfolio_drop=0.0,
                total_loss=0.0,
                total_loss_pct=0.0,
            )

        # 计算各股票的脆弱性（跌幅）
        vuln_results = self.vulnerability_engine.calculate_portfolio(
            portfolio, event, add_noise=add_noise
        )

        # 计算各股票损失
        position_losses = {}
        position_drops = {}
        total_loss = 0.0
        weighted_drop = 0.0

        for vuln, position in zip(vuln_results, portfolio.positions):
            loss = position.market_value * abs(vuln.final_drop)  # 损失金额（正数）
            position_losses[position.ticker] = loss
            position_drops[position.ticker] = vuln.final_drop
            total_loss += loss
            weight = position.market_value / portfolio.total_value
            weighted_drop += vuln.final_drop * weight

        total_loss_pct = total_loss / portfolio.total_value if portfolio.total_value > 0 else 0.0

        return LossResult(
            event_id=event.event_id,
            event_name=event.event_name,
            market_drop=event.market_drop,
            portfolio_drop=weighted_drop,
            total_loss=total_loss,
            total_loss_pct=total_loss_pct,
            position_losses=position_losses,
            position_drops=position_drops,
        )

    def run_monte_carlo(
        self,
        portfolio: Portfolio,
        selected_event_ids: Optional[List[str]] = None,
        n_simulations: int = 10000,
        intensity_noise: float = 0.2,
        duration_noise: float = 0.3,
        add_noise: bool = True,
        random_seed: int = 42,
    ) -> Tuple[List[LossResult], pd.DataFrame]:
        """
        运行蒙特卡洛模拟，生成损失分布

        :param portfolio: 投资组合
        :param selected_event_ids: 选择的历史股灾ID，None表示全部
        :param n_simulations: 模拟次数
        :param intensity_noise: 强度扰动
        :param duration_noise: 持续时间扰动
        :param add_noise: 是否添加个股残差
        :param random_seed: 随机种子
        :return: (损失结果列表, 损失数据DataFrame)
        """
        # 生成事件集
        events = self.hazard_engine.generate_event_set(
            selected_event_ids=selected_event_ids,
            n_simulations=n_simulations,
            intensity_noise=intensity_noise,
            duration_noise=duration_noise,
            random_seed=random_seed,
        )

        # 计算每个事件的损失
        results = []
        for event in events:
            result = self.calculate_single_event(portfolio, event, add_noise=add_noise)
            results.append(result)

        # 转换为DataFrame
        data = []
        for r in results:
            data.append({
                "event_id": r.event_id,
                "event_name": r.event_name,
                "market_drop": r.market_drop,
                "portfolio_drop": r.portfolio_drop,
                "total_loss": r.total_loss,
                "total_loss_pct": r.total_loss_pct,
            })
        df = pd.DataFrame(data)

        return results, df

    def calculate_risk_metrics(
        self,
        loss_df: pd.DataFrame,
        portfolio_value: float,
    ) -> RiskMetrics:
        """
        从损失分布计算风险度量指标

        :param loss_df: 损失数据DataFrame
        :param portfolio_value: 投资组合总市值
        :return: 风险度量指标
        """
        losses = loss_df["total_loss"].values
        losses_pct = loss_df["total_loss_pct"].values

        # 预期损失（概率加权平均，这里事件集已经按概率抽样）
        expected_loss = np.mean(losses)
        expected_loss_pct = np.mean(losses_pct)

        # VaR（分位数，注意损失是正数，越大越严重）
        var_95 = np.percentile(losses, 95)
        var_95_pct = np.percentile(losses_pct, 95)
        var_99 = np.percentile(losses, 99)
        var_99_pct = np.percentile(losses_pct, 99)

        # CVaR（条件VaR，超过VaR后的平均损失）
        cvar_95 = np.mean(losses[losses >= var_95])
        cvar_95_pct = np.mean(losses_pct[losses_pct >= var_95_pct])
        cvar_99 = np.mean(losses[losses >= var_99])
        cvar_99_pct = np.mean(losses_pct[losses_pct >= var_99_pct])

        # 极值
        max_loss = np.max(losses)
        max_loss_pct = np.max(losses_pct)
        min_loss = np.min(losses)
        min_loss_pct = np.min(losses_pct)

        # 标准差
        loss_std = np.std(losses)
        loss_std_pct = np.std(losses_pct)

        return RiskMetrics(
            expected_loss=expected_loss,
            expected_loss_pct=expected_loss_pct,
            var_95=var_95,
            var_95_pct=var_95_pct,
            var_99=var_99,
            var_99_pct=var_99_pct,
            cvar_95=cvar_95,
            cvar_95_pct=cvar_95_pct,
            cvar_99=cvar_99,
            cvar_99_pct=cvar_99_pct,
            max_loss=max_loss,
            max_loss_pct=max_loss_pct,
            min_loss=min_loss,
            min_loss_pct=min_loss_pct,
            loss_std=loss_std,
            loss_std_pct=loss_std_pct,
            max_drawdown=max_loss,  # 近似
            max_drawdown_pct=max_loss_pct,
        )

    def get_loss_exceedance_curve(
        self,
        loss_df: pd.DataFrame,
        n_points: int = 100,
    ) -> pd.DataFrame:
        """
        计算损失超越概率曲线（类似Oasis的EP曲线）

        :param loss_df: 损失数据
        :param n_points: 曲线点数
        :return: 超越概率曲线DataFrame
        """
        losses = loss_df["total_loss_pct"].values
        thresholds = np.linspace(0, np.max(losses), n_points)
        exceedance_probs = []
        for t in thresholds:
            prob = np.mean(losses >= t)
            exceedance_probs.append(prob)

        return pd.DataFrame({
            "loss_threshold_pct": thresholds,
            "exceedance_probability": exceedance_probs,
        })

    def get_sector_loss_contribution(
        self,
        results: List[LossResult],
        portfolio: Portfolio,
    ) -> pd.DataFrame:
        """
        计算各行业的损失贡献度

        :param results: 损失结果列表
        :param portfolio: 投资组合
        :return: 行业损失贡献DataFrame
        """
        sector_losses = {}
        sector_values = {}
        for position in portfolio.positions:
            sector_values[position.sector] = sector_values.get(position.sector, 0) + position.market_value

        for result in results:
            for ticker, loss in result.position_losses.items():
                # 找到该股票的行业
                for p in portfolio.positions:
                    if p.ticker == ticker:
                        sector = p.sector
                        break
                else:
                    sector = "其他"
                sector_losses[sector] = sector_losses.get(sector, 0) + loss

        # 计算平均损失（除以模拟次数）
        n_simulations = len(results)
        data = []
        total_avg_loss = sum(sector_losses.values()) / n_simulations if n_simulations > 0 else 0
        for sector, total_loss in sector_losses.items():
            avg_loss = total_loss / n_simulations if n_simulations > 0 else 0
            contribution = avg_loss / total_avg_loss if total_avg_loss > 0 else 0
            sector_value = sector_values.get(sector, 0)
            loss_rate = avg_loss / sector_value if sector_value > 0 else 0
            data.append({
                "行业": sector,
                "行业市值": sector_value,
                "平均损失": avg_loss,
                "损失率": loss_rate,
                "损失贡献度": contribution,
            })

        df = pd.DataFrame(data).sort_values("平均损失", ascending=False)
        return df
