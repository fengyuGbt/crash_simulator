"""
危险层(Hazard) - 市场冲击事件集生成

对应巨灾建模中的"危险"：可能发生什么极端事件，概率多大，强度多大
第一版：历史股灾重演 + 随机扰动
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from pathlib import Path


@dataclass
class CrashEvent:
    """单个股灾事件"""
    event_id: str
    event_name: str
    event_type: str  # 系统性股灾/行业危机/政策突变/黑天鹅/流动性危机
    start_date: str
    end_date: str
    duration_days: int
    market_drop: float  # 大盘跌幅，如-0.568表示-56.8%
    affected_sectors: List[str]  # 受影响行业列表
    probability: float  # 年化发生概率
    description: str = ""

    # 运行时生成的参数
    intensity_multiplier: float = 1.0  # 强度扰动系数
    duration_multiplier: float = 1.0   # 持续时间扰动系数
    seed: int = 0  # 随机种子


class HazardEngine:
    """危险引擎 - 生成股灾事件集"""

    def __init__(self, data_path: Optional[str] = None):
        """
        初始化危险引擎
        :param data_path: 历史股灾数据CSV路径，默认使用内置数据
        """
        if data_path is None:
            # 默认使用包内数据
            data_path = Path(__file__).parent.parent / "data" / "historical_crashes.csv"
        self.data_path = Path(data_path)
        self.historical_crashes = self._load_historical_crashes()

    def _load_historical_crashes(self) -> pd.DataFrame:
        """加载历史股灾数据"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"历史股灾数据文件不存在: {self.data_path}")
        df = pd.read_csv(self.data_path)
        # 解析受影响行业
        df["affected_sectors"] = df["affected_sectors"].apply(
            lambda x: [s.strip() for s in str(x).split(",")]
        )
        return df

    def get_available_crashes(self) -> List[Dict]:
        """获取可用的历史股灾列表"""
        result = []
        for _, row in self.historical_crashes.iterrows():
            result.append({
                "event_id": row["event_id"],
                "event_name": row["event_name"],
                "event_type": row["event_type"],
                "market_drop": row["market_drop"],
                "duration_days": row["duration_days"],
                "probability": row["probability"],
                "description": row["description"],
            })
        return result

    def generate_event_set(
        self,
        selected_event_ids: Optional[List[str]] = None,
        n_simulations: int = 10000,
        intensity_noise: float = 0.2,
        duration_noise: float = 0.3,
        random_seed: int = 42,
    ) -> List[CrashEvent]:
        """
        生成股灾事件集（蒙特卡洛）

        :param selected_event_ids: 选择的历史股灾ID列表，None表示全部
        :param n_simulations: 总模拟次数（事件数）
        :param intensity_noise: 强度扰动比例（0.2表示±20%）
        :param duration_noise: 持续时间扰动比例
        :param random_seed: 随机种子
        :return: 股灾事件列表
        """
        np.random.seed(random_seed)

        # 筛选历史股灾
        if selected_event_ids is None:
            crashes = self.historical_crashes.copy()
        else:
            crashes = self.historical_crashes[
                self.historical_crashes["event_id"].isin(selected_event_ids)
            ].copy()

        if len(crashes) == 0:
            raise ValueError("没有选择任何历史股灾事件")

        # 按概率加权分配模拟次数
        probabilities = crashes["probability"].values
        probabilities = probabilities / probabilities.sum()  # 归一化
        n_per_event = np.random.multinomial(n_simulations, probabilities)

        # 生成事件集
        events = []
        event_counter = 0
        for idx, (_, crash) in enumerate(crashes.iterrows()):
            n = n_per_event[idx]
            for i in range(n):
                # 随机扰动
                intensity_mult = 1.0 + np.random.uniform(-intensity_noise, intensity_noise)
                duration_mult = 1.0 + np.random.uniform(-duration_noise, duration_noise)

                event = CrashEvent(
                    event_id=f"{crash['event_id']}_{event_counter}",
                    event_name=crash["event_name"],
                    event_type=crash["event_type"],
                    start_date=crash["start_date"],
                    end_date=crash["end_date"],
                    duration_days=int(crash["duration_days"] * duration_mult),
                    market_drop=crash["market_drop"] * intensity_mult,
                    affected_sectors=crash["affected_sectors"],
                    probability=crash["probability"] / n,  # 单个事件的概率
                    description=crash["description"],
                    intensity_multiplier=intensity_mult,
                    duration_multiplier=duration_mult,
                    seed=event_counter,
                )
                events.append(event)
                event_counter += 1

        return events

    def generate_single_event(
        self,
        event_id: str,
        intensity_multiplier: float = 1.0,
        duration_multiplier: float = 1.0,
    ) -> CrashEvent:
        """
        生成单个股灾事件（用于情景分析）

        :param event_id: 历史股灾ID
        :param intensity_multiplier: 强度倍数
        :param duration_multiplier: 持续时间倍数
        :return: 单个股灾事件
        """
        crash = self.historical_crashes[
            self.historical_crashes["event_id"] == event_id
        ]
        if len(crash) == 0:
            raise ValueError(f"找不到股灾事件: {event_id}")

        crash = crash.iloc[0]
        return CrashEvent(
            event_id=event_id,
            event_name=crash["event_name"],
            event_type=crash["event_type"],
            start_date=crash["start_date"],
            end_date=crash["end_date"],
            duration_days=int(crash["duration_days"] * duration_multiplier),
            market_drop=crash["market_drop"] * intensity_multiplier,
            affected_sectors=crash["affected_sectors"],
            probability=crash["probability"],
            description=crash["description"],
            intensity_multiplier=intensity_multiplier,
            duration_multiplier=duration_multiplier,
        )
