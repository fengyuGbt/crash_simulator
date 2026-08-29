"""
暴露层(Exposure) - 投资组合数据结构

对应巨灾建模中的"暴露"：谁在承担风险，承担多少
"""

from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd
import numpy as np


@dataclass
class Position:
    """单个持仓"""
    ticker: str           # 股票代码，如 AAPL
    name: str = ""        # 公司名称
    sector: str = "其他"  # GICS一级行业
    shares: float = 0.0   # 持仓量（股）
    cost_price: float = 0.0  # 成本价
    current_price: float = 0.0  # 当前价（运行时获取）
    beta: float = 1.0     # 相对于大盘的beta
    downside_beta: float = 1.2  # 下行beta（下跌时通常更大）

    @property
    def market_value(self) -> float:
        """当前市值"""
        return self.shares * self.current_price

    @property
    def cost_value(self) -> float:
        """成本市值"""
        return self.shares * self.cost_price

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost_value


@dataclass
class Portfolio:
    """投资组合"""
    positions: List[Position] = field(default_factory=list)
    name: str = "我的投资组合"

    def add_position(self, position: Position):
        """添加持仓"""
        self.positions.append(position)

    def remove_position(self, ticker: str):
        """移除持仓"""
        self.positions = [p for p in self.positions if p.ticker != ticker]

    @property
    def total_value(self) -> float:
        """组合总市值"""
        return sum(p.market_value for p in self.positions)

    @property
    def total_cost(self) -> float:
        """组合总成本"""
        return sum(p.cost_value for p in self.positions)

    @property
    def total_pnl(self) -> float:
        """组合总盈亏"""
        return self.total_value - self.total_cost

    @property
    def weighted_beta(self) -> float:
        """加权平均beta"""
        if self.total_value == 0:
            return 1.0
        return sum(p.beta * p.market_value for p in self.positions) / self.total_value

    @property
    def sector_exposure(self) -> pd.Series:
        """行业暴露（各行业市值占比）"""
        if not self.positions:
            return pd.Series(dtype=float)
        data = {}
        for p in self.positions:
            data[p.sector] = data.get(p.sector, 0) + p.market_value
        total = sum(data.values())
        return pd.Series({k: v / total for k, v in data.items()})

    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        data = []
        for p in self.positions:
            data.append({
                "股票代码": p.ticker,
                "公司名称": p.name,
                "行业": p.sector,
                "持仓量": p.shares,
                "成本价": p.cost_price,
                "当前价": p.current_price,
                "市值": p.market_value,
                "仓位占比": p.market_value / self.total_value if self.total_value > 0 else 0,
                "beta": p.beta,
                "下行beta": p.downside_beta,
                "未实现盈亏": p.unrealized_pnl,
            })
        return pd.DataFrame(data)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, name: str = "我的投资组合") -> "Portfolio":
        """从DataFrame创建投资组合"""
        portfolio = cls(name=name)
        for _, row in df.iterrows():
            position = Position(
                ticker=str(row.get("股票代码", row.get("ticker", ""))),
                name=str(row.get("公司名称", row.get("name", ""))),
                sector=str(row.get("行业", row.get("sector", "其他"))),
                shares=float(row.get("持仓量", row.get("shares", 0))),
                cost_price=float(row.get("成本价", row.get("cost_price", 0))),
                current_price=float(row.get("当前价", row.get("current_price", 0))),
                beta=float(row.get("beta", 1.0)),
                downside_beta=float(row.get("下行beta", row.get("downside_beta", 1.2))),
            )
            portfolio.add_position(position)
        return portfolio


def create_sample_portfolio() -> Portfolio:
    """创建示例投资组合（美股科技+消费）"""
    portfolio = Portfolio(name="示例组合：科技+消费")
    sample_positions = [
        Position(ticker="AAPL", name="苹果", sector="科技", shares=10, cost_price=150.0, current_price=180.0, beta=1.2, downside_beta=1.3),
        Position(ticker="MSFT", name="微软", sector="科技", shares=5, cost_price=300.0, current_price=380.0, beta=0.9, downside_beta=1.0),
        Position(ticker="GOOGL", name="谷歌", sector="科技", shares=8, cost_price=120.0, current_price=140.0, beta=1.1, downside_beta=1.2),
        Position(ticker="AMZN", name="亚马逊", sector="消费", shares=6, cost_price=100.0, current_price=130.0, beta=1.3, downside_beta=1.5),
        Position(ticker="TSLA", name="特斯拉", sector="消费", shares=15, cost_price=200.0, current_price=220.0, beta=2.0, downside_beta=2.5),
        Position(ticker="JPM", name="摩根大通", sector="金融", shares=10, cost_price=140.0, current_price=160.0, beta=1.1, downside_beta=1.4),
        Position(ticker="JNJ", name="强生", sector="医疗", shares=8, cost_price=150.0, current_price=155.0, beta=0.5, downside_beta=0.6),
    ]
    for p in sample_positions:
        portfolio.add_position(p)
    return portfolio
