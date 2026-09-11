"""
危险层(Hazard) - 市场冲击事件集生成

对应巨灾建模中的"危险"：可能发生什么极端事件，概率多大，强度多大
第一版：历史股灾重演 + 随机扰动

V9-P2: 内生危险（endogenous hazard）
    把 market_state（VIX/SKEW regime + hazard_multiplier，V9-P0）和
    dealer_gamma（做市商净伽马状态，V9-P1）接进事件强度生成：

        事件强度 = 历史强度扰动 × regime乘数 × 短伽马放大因子

    市场自身的状态（越紧张、做市商越做空伽马）会放大同样历史事件
    重演时的强度——危险不再只是外生的历史清单，而是市场状态的函数。
    这是对 Dean Lee 三条反馈（内生性 / 短伽马 / 隐含vs实现）的收官。

    默认关闭（use_state_calibration=False），保持与旧版本行为完全一致；
    显式开启后接入市场状态。离线时自动回退到中性状态（calm, 1.0, gamma=0）。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from pathlib import Path

# V9-P2: 短伽马状态对事件强度的放大权重（机制模型参数，非市场标定）
SHORT_GAMMA_INTENSITY_WEIGHT = 0.30
# 短伽马放大的文档化上限（防止单一极端状态把强度推到无界）
SHORT_GAMMA_INTENSITY_CAP = 1.50


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

    def __init__(self, data_path: Optional[str] = None,
                 market_state: Optional[dict] = None,
                 use_state_calibration: bool = False):
        """
        初始化危险引擎
        :param data_path: 历史股灾数据CSV路径，默认使用内置数据
        :param market_state: market_state.compute_state() 返回的状态字典；
                             为 None 时尝试实时拉取（失败则中性状态）
        :param use_state_calibration: 是否启用内生状态校准（默认 False，
                             保持与旧版本完全一致的向后兼容行为）
        """
        if data_path is None:
            # 默认使用包内数据
            data_path = Path(__file__).parent.parent / "data" / "historical_crashes.csv"
        self.data_path = Path(data_path)
        self.historical_crashes = self._load_historical_crashes()

        # ---- V9-P2: endogenous hazard state ----
        self.regime: str = "calm"
        self.hazard_multiplier: float = 1.0
        self.net_gamma: float = 0.0
        self.state_snapshot: Dict = {}
        self.use_state_calibration = use_state_calibration
        if use_state_calibration:
            self._calibrate_state(market_state)

    # ------------------------------------------------------------------
    # V9-P2: state calibration
    # ------------------------------------------------------------------
    def _calibrate_state(self, market_state: Optional[dict] = None):
        """加载 regime / hazard multiplier / dealer gamma 市场状态。

        market_state 为 None 时尝试从 Cboe 实时数据计算；任何失败都回退
        到中性状态（calm, multiplier 1.0, gamma 0），保证离线可用。
        """
        if market_state is None:
            try:
                import market_state as ms
                market_state = ms.compute_state()
            except Exception as exc:  # offline fallback: neutral state
                print(f"  [warn] market_state unavailable ({exc}); neutral state")
                market_state = {}
        self.state_snapshot = dict(market_state or {})
        self.regime = str(self.state_snapshot.get("regime", "calm"))
        self.hazard_multiplier = float(
            self.state_snapshot.get("hazard_multiplier", 1.0))
        try:
            import dealer_gamma as dg
            self.net_gamma = float(dg.estimate_net_gamma(self.state_snapshot))
        except Exception:
            self.net_gamma = 0.0
        return self

    def state_intensity_multiplier(self) -> float:
        """组合内生强度乘数，作用于每次事件重演的强度。

        = regime乘数（calm 1.0 / stressed 1.5 / panic 2.5）
          × 短伽马放大因子（1 + max(0, -net_gamma) × 权重，封顶 1.5）

        短伽马（net_gamma<0）时，做市商机械对冲会放大下跌，事件强度上调；
        长伽马（net_gamma>0）时不放大。单因子封顶防止极端状态失控。
        """
        gamma_amp = 1.0 + max(0.0, -self.net_gamma) * SHORT_GAMMA_INTENSITY_WEIGHT
        gamma_amp = min(gamma_amp, SHORT_GAMMA_INTENSITY_CAP)
        return round(self.hazard_multiplier * gamma_amp, 4)

    def _state_mult(self) -> float:
        """当前生效的内生强度乘数（未启用时恒为 1.0）。"""
        return self.state_intensity_multiplier() if self.use_state_calibration else 1.0

    # ------------------------------------------------------------------
    # original API (unchanged behavior unless calibration enabled)
    # ------------------------------------------------------------------
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
        state_mult = self._state_mult()

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
                # 随机扰动（V9-P2: 乘以内生状态乘数）
                intensity_mult = (1.0 + np.random.uniform(-intensity_noise, intensity_noise)) * state_mult
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
        state_mult = self._state_mult()
        total_intensity = intensity_multiplier * state_mult
        return CrashEvent(
            event_id=event_id,
            event_name=crash["event_name"],
            event_type=crash["event_type"],
            start_date=crash["start_date"],
            end_date=crash["end_date"],
            duration_days=int(crash["duration_days"] * duration_multiplier),
            market_drop=crash["market_drop"] * total_intensity,
            affected_sectors=crash["affected_sectors"],
            probability=crash["probability"],
            description=crash["description"],
            intensity_multiplier=total_intensity,
            duration_multiplier=duration_multiplier,
        )

    # ------------------------------------------------------------------
    # V9-P2: validation
    # ------------------------------------------------------------------
    def self_test(self) -> int:
        """验证 V9-P2 不变量（无需网络：状态以 dict 注入）。

        覆盖：中性状态乘数=1.0 / panic 放大 / 短伽马超额放大 /
        长伽马不放大 / 默认向后兼容 / 事件集均值随状态迁移。
        """
        print("== hazard V9-P2 self-test ==")
        neutral_state = {
            "regime": "calm", "hazard_multiplier": 1.0,
            "skew_pctile_5y": 0.5, "vix_pctile_5y": 0.5,
        }
        panic_state = {
            "regime": "panic", "hazard_multiplier": 2.5,
            "skew_pctile_5y": 0.9, "vix_pctile_5y": 0.95,
        }
        stressed_long_state = {
            "regime": "stressed", "hazard_multiplier": 1.5,
            "skew_pctile_5y": 0.3, "vix_pctile_5y": 0.5,  # long gamma
        }

        neutral = HazardEngine(self.data_path, market_state=neutral_state,
                               use_state_calibration=True)
        panic = HazardEngine(self.data_path, market_state=panic_state,
                             use_state_calibration=True)
        longg = HazardEngine(self.data_path, market_state=stressed_long_state,
                             use_state_calibration=True)
        plain = HazardEngine(self.data_path)  # default: backward compatible

        # 1. neutral state -> multiplier exactly 1.0
        assert neutral.state_intensity_multiplier() == 1.0, (
            f"neutral multiplier must be 1.0: {neutral.state_intensity_multiplier()}")
        # 2. panic regime multiplies intensity
        assert panic.state_intensity_multiplier() >= 2.5, (
            f"panic must multiply: {panic.state_intensity_multiplier()}")
        # 3. short gamma amplifies beyond the regime multiplier alone
        assert panic.state_intensity_multiplier() > 2.5 + 1e-9, (
            f"short gamma must add amplification: {panic.state_intensity_multiplier()}")
        # 4. long gamma does not amplify
        assert longg.state_intensity_multiplier() == 1.5, (
            f"long gamma must not amplify: {longg.state_intensity_multiplier()}")
        # 5. default (no calibration) keeps multiplier at 1.0
        assert plain.state_intensity_multiplier() == 1.0, (
            f"default must stay 1.0: {plain.state_intensity_multiplier()}")

        # 6. event-set mean |drop| shifts with state (same seed -> same noise)
        ev_panic = panic.generate_event_set(n_simulations=5000, random_seed=7)
        ev_plain = plain.generate_event_set(n_simulations=5000, random_seed=7)
        mean_panic = float(np.mean([abs(e.market_drop) for e in ev_panic]))
        mean_plain = float(np.mean([abs(e.market_drop) for e in ev_plain]))
        assert mean_panic > mean_plain * 1.5, (
            f"panic event set must be materially worse: {mean_panic:.4f} vs {mean_plain:.4f}")

        # 7. state snapshot is readable
        assert panic.regime == "panic" and panic.net_gamma < 0, (
            f"state snapshot wrong: {panic.regime}, {panic.net_gamma}")

        print(f"  neutral state multiplier      : {neutral.state_intensity_multiplier()}")
        print(f"  panic  state multiplier      : {panic.state_intensity_multiplier()}"
              f"  (regime 2.5 x gamma {panic.net_gamma})")
        print(f"  stressed+long-gamma multiplier: {longg.state_intensity_multiplier()}")
        print(f"  default (no calibration)      : {plain.state_intensity_multiplier()}")
        print(f"  mean |drop| panic/plain       : {mean_panic:.4f} / {mean_plain:.4f}")
        print("== self-test OK ==")
        return 0


def main() -> int:
    """CLI：--self-test 跑验证；否则打印当前市场状态校准结果 + 演示事件集。"""
    if "--self-test" in sys.argv:
        return HazardEngine().self_test()
    engine = HazardEngine(use_state_calibration=True)
    print("== V9-P2 endogenous hazard state (live Cboe data) ==")
    print(f"  regime: {engine.regime}")
    print(f"  hazard_multiplier: {engine.hazard_multiplier}")
    print(f"  estimated net dealer gamma: {engine.net_gamma}")
    print(f"  combined state intensity multiplier: {engine.state_intensity_multiplier()}")

    events = engine.generate_event_set(n_simulations=2000, random_seed=42)
    plain = HazardEngine(data_path=engine.data_path)
    plain_events = plain.generate_event_set(n_simulations=2000, random_seed=42)
    mean_state = float(np.mean([abs(e.market_drop) for e in events]))
    mean_plain = float(np.mean([abs(e.market_drop) for e in plain_events]))
    print(f"  mean |drop| (state-calibrated): {mean_state:.4f}")
    print(f"  mean |drop| (plain baseline)  : {mean_plain:.4f}")
    print("== demo OK ==")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
