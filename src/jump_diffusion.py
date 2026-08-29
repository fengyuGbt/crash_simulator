"""
SDE跳跃扩散模型（Jump-Diffusion Model）

将股价建模为连续扩散过程 + 跳跃过程：
    dS/S = μdt + σdW + JdN

其中：
- μdt：漂移项（长期趋势）
- σdW：扩散项（布朗运动，正常波动）
- JdN：跳跃项（泊松过程驱动，黑天鹅事件）

跳跃扩散模型的优势：
1. 能捕捉股价的不连续跳跃（财报、黑天鹅、政策突变）
2. 比纯几何布朗运动更符合实际市场的"尖峰厚尾"特征
3. 可以单独校准跳跃强度和幅度，模拟不同严重程度的股灾

参考：Merton (1976) 跳跃扩散模型
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class JumpDiffusionParams:
    """跳跃扩散模型参数"""
    # 扩散部分参数
    mu: float = 0.08          # 年化漂移率（默认8%，美股长期平均）
    sigma: float = 0.20       # 年化波动率（默认20%，美股长期平均）

    # 跳跃部分参数
    jump_lambda: float = 1.0  # 跳跃强度（每年跳跃次数，默认1次/年）
    jump_mu: float = -0.05    # 跳跃幅度均值（默认-5%，向下跳跃为主）
    jump_sigma: float = 0.10  # 跳跃幅度标准差（默认10%）

    # 模拟参数
    initial_price: float = 100.0  # 初始价格
    n_days: int = 252              # 模拟天数（默认1年交易日）
    dt: float = 1.0 / 252          # 时间步长（1个交易日）


@dataclass
class JumpDiffusionResult:
    """跳跃扩散模拟结果"""
    prices: np.ndarray              # 价格序列
    returns: np.ndarray             # 日收益率序列
    diffusion_returns: np.ndarray   # 扩散部分收益率
    jump_returns: np.ndarray        # 跳跃部分收益率
    jump_times: List[int]           # 跳跃发生的时间点
    jump_sizes: List[float]         # 每次跳跃的幅度
    n_jumps: int                    # 跳跃总次数
    max_drawdown: float             # 最大回撤
    total_return: float             # 总收益率
    annualized_vol: float           # 年化波动率
    params: JumpDiffusionParams     # 使用的参数


class JumpDiffusionModel:
    """
    跳跃扩散模型

    用法：
        model = JumpDiffusionModel()
        result = model.simulate(n_simulations=1000)
    """

    def __init__(self, params: Optional[JumpDiffusionParams] = None):
        self.params = params or JumpDiffusionParams()

    def simulate_single(
        self,
        params: Optional[JumpDiffusionParams] = None,
        random_seed: Optional[int] = None,
    ) -> JumpDiffusionResult:
        """
        模拟单条价格路径

        算法：
        1. 模拟泊松过程，确定跳跃发生的时间和次数
        2. 对每个时间步，模拟扩散部分（几何布朗运动）
        3. 如果有跳跃发生，加上跳跃幅度（正态分布）
        """
        if random_seed is not None:
            np.random.seed(random_seed)

        p = params or self.params
        n = p.n_days
        dt = p.dt

        # 1. 模拟泊松过程：确定跳跃发生的时间
        # 跳跃强度λ，在dt时间内发生跳跃的概率 = λ * dt
        jump_prob = p.jump_lambda * dt
        jump_indicators = np.random.binomial(1, jump_prob, n)
        jump_times = np.where(jump_indicators == 1)[0].tolist()
        n_jumps = len(jump_times)

        # 2. 模拟扩散部分（几何布朗运动）
        # dS/S = (μ - 0.5σ²)dt + σdW
        diffusion_shocks = np.random.normal(0, 1, n)
        diffusion_log_returns = (p.mu - 0.5 * p.sigma**2) * dt + p.sigma * np.sqrt(dt) * diffusion_shocks

        # 3. 模拟跳跃部分
        # 跳跃幅度服从正态分布 N(μ_J, σ_J²)
        jump_log_returns = np.zeros(n)
        jump_sizes = []
        for t in jump_times:
            jump_size = np.random.normal(p.jump_mu, p.jump_sigma)
            jump_log_returns[t] = jump_size
            jump_sizes.append(jump_size)

        # 4. 合并扩散和跳跃部分
        total_log_returns = diffusion_log_returns + jump_log_returns

        # 5. 计算价格序列
        prices = np.zeros(n + 1)
        prices[0] = p.initial_price
        for i in range(n):
            prices[i + 1] = prices[i] * np.exp(total_log_returns[i])

        # 6. 计算统计指标
        returns = np.diff(prices) / prices[:-1]
        total_return = prices[-1] / prices[0] - 1

        # 最大回撤
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak
        max_drawdown = np.min(drawdown)

        # 年化波动率
        annualized_vol = np.std(returns) * np.sqrt(252)

        return JumpDiffusionResult(
            prices=prices,
            returns=returns,
            diffusion_returns=np.exp(diffusion_log_returns) - 1,
            jump_returns=np.exp(jump_log_returns) - 1,
            jump_times=jump_times,
            jump_sizes=jump_sizes,
            n_jumps=n_jumps,
            max_drawdown=max_drawdown,
            total_return=total_return,
            annualized_vol=annualized_vol,
            params=p,
        )

    def simulate(
        self,
        n_simulations: int = 1000,
        params: Optional[JumpDiffusionParams] = None,
        base_seed: int = 42,
    ) -> List[JumpDiffusionResult]:
        """
        模拟多条价格路径（蒙特卡洛）
        """
        results = []
        for i in range(n_simulations):
            result = self.simulate_single(params=params, random_seed=base_seed + i)
            results.append(result)
        return results

    def get_crash_scenarios(
        self,
        n_scenarios: int = 100,
        crash_threshold: float = -0.20,
        params: Optional[JumpDiffusionParams] = None,
        base_seed: int = 42,
    ) -> List[dict]:
        """
        从模拟中筛选股灾情景（最大回撤超过阈值）

        参数：
            crash_threshold: 股灾阈值，默认-20%（最大回撤超过20%视为股灾）

        返回：
            股灾情景列表，每个情景包含：
            - scenario_id: 情景ID
            - max_drawdown: 最大回撤
            - crash_day: 见底天数
            - n_jumps: 跳跃次数
            - total_return: 总收益率
            - price_path: 价格路径
        """
        # 模拟足够多的路径，然后筛选股灾
        n_total = max(n_scenarios * 10, 1000)
        results = self.simulate(n_simulations=n_total, params=params, base_seed=base_seed)

        # 筛选股灾情景
        crash_results = [r for r in results if r.max_drawdown <= crash_threshold]

        # 如果股灾情景不够，降低阈值
        if len(crash_results) < n_scenarios:
            crash_results = sorted(results, key=lambda x: x.max_drawdown)[:n_scenarios]

        # 取前n_scenarios个
        crash_results = crash_results[:n_scenarios]

        # 转换为字典
        scenarios = []
        for i, r in enumerate(crash_results):
            # 找到见底天数
            peak = np.maximum.accumulate(r.prices)
            drawdown = (r.prices - peak) / peak
            crash_day = int(np.argmin(drawdown))

            scenarios.append({
                "scenario_id": f"JD_{i:04d}",
                "max_drawdown": float(r.max_drawdown),
                "crash_day": crash_day,
                "n_jumps": r.n_jumps,
                "total_return": float(r.total_return),
                "annualized_vol": float(r.annualized_vol),
                "jump_times": r.jump_times,
                "jump_sizes": r.jump_sizes,
                "price_path": r.prices.tolist(),
            })

        return scenarios

    def calibrate_from_returns(
        self,
        returns: np.ndarray,
        trading_days: int = 252,
    ) -> JumpDiffusionParams:
        """
        从历史收益率数据校准跳跃扩散参数

        简化校准方法：
        1. 用整体均值和标准差估计μ和σ
        2. 用极端收益率（超过2倍标准差）识别跳跃
        3. 用跳跃的频率和幅度估计λ、μ_J、σ_J

        注意：这是简化校准，精确校准需要用MCMC或极大似然估计
        """
        # 日收益率统计
        daily_mu = np.mean(returns)
        daily_sigma = np.std(returns)

        # 年化
        mu = daily_mu * trading_days
        sigma = daily_sigma * np.sqrt(trading_days)

        # 识别跳跃：收益率超过2倍标准差的视为跳跃
        threshold = 2 * daily_sigma
        jump_returns = returns[np.abs(returns) > threshold]
        n_jumps = len(jump_returns)
        n_total = len(returns)

        # 跳跃强度（年化）
        jump_lambda = n_jumps / n_total * trading_days

        # 跳跃幅度统计
        if n_jumps > 0:
            jump_mu = np.mean(jump_returns)
            jump_sigma = np.std(jump_returns)
        else:
            jump_mu = -0.05
            jump_sigma = 0.10

        return JumpDiffusionParams(
            mu=mu,
            sigma=sigma,
            jump_lambda=max(jump_lambda, 0.1),  # 至少0.1次/年
            jump_mu=jump_mu,
            jump_sigma=max(jump_sigma, 0.05),  # 至少5%
        )


def generate_crash_jump_params(
    severity: str = "moderate",
) -> JumpDiffusionParams:
    """
    生成不同严重程度的股灾跳跃参数

    参数：
        severity: 严重程度
            - "mild": 轻度（类似正常调整）
            - "moderate": 中度（类似2022熊市）
            - "severe": 重度（类似2008金融危机）
            - "extreme": 极端（类似1929大萧条）
    """
    params_map = {
        "mild": JumpDiffusionParams(
            mu=0.05, sigma=0.25,
            jump_lambda=2.0, jump_mu=-0.03, jump_sigma=0.05,
            n_days=126,
        ),
        "moderate": JumpDiffusionParams(
            mu=0.0, sigma=0.35,
            jump_lambda=4.0, jump_mu=-0.08, jump_sigma=0.12,
            n_days=180,
        ),
        "severe": JumpDiffusionParams(
            mu=-0.10, sigma=0.50,
            jump_lambda=8.0, jump_mu=-0.15, jump_sigma=0.20,
            n_days=252,
        ),
        "extreme": JumpDiffusionParams(
            mu=-0.20, sigma=0.70,
            jump_lambda=15.0, jump_mu=-0.25, jump_sigma=0.30,
            n_days=365,
        ),
    }
    return params_map.get(severity, params_map["moderate"])


if __name__ == "__main__":
    # 简单测试
    print("=" * 60)
    print("跳跃扩散模型测试")
    print("=" * 60)

    model = JumpDiffusionModel()

    # 单条路径模拟
    print("\n单条路径模拟...")
    result = model.simulate_single(random_seed=42)
    print(f"  初始价格: {result.params.initial_price}")
    print(f"  最终价格: {result.prices[-1]:.2f}")
    print(f"  总收益率: {result.total_return*100:.1f}%")
    print(f"  最大回撤: {result.max_drawdown*100:.1f}%")
    print(f"  跳跃次数: {result.n_jumps}")
    print(f"  跳跃时间: {result.jump_times}")
    print(f"  跳跃幅度: {[f'{s*100:.1f}%' for s in result.jump_sizes]}")
    print(f"  年化波动率: {result.annualized_vol*100:.1f}%")

    # 蒙特卡洛模拟
    print("\n蒙特卡洛模拟（1000次）...")
    results = model.simulate(n_simulations=1000, base_seed=42)
    max_drawdowns = [r.max_drawdown for r in results]
    total_returns = [r.total_return for r in results]

    print(f"  平均最大回撤: {np.mean(max_drawdowns)*100:.1f}%")
    print(f"  5%分位最大回撤: {np.percentile(max_drawdowns, 5)*100:.1f}%")
    print(f"  最坏最大回撤: {np.min(max_drawdowns)*100:.1f}%")
    print(f"  平均总收益率: {np.mean(total_returns)*100:.1f}%")
    print(f"  股灾概率(回撤>20%): {sum(1 for d in max_drawdowns if d < -0.20)/len(max_drawdowns)*100:.1f}%")

    # 股灾情景筛选
    print("\n股灾情景筛选（回撤>20%）...")
    scenarios = model.get_crash_scenarios(n_scenarios=5, crash_threshold=-0.20)
    for s in scenarios:
        print(f"  {s['scenario_id']}: 最大回撤{s['max_drawdown']*100:.1f}%, "
              f"第{s['crash_day']}天见底, 跳跃{s['n_jumps']}次")

    # 不同严重程度
    print("\n不同严重程度的股灾参数...")
    for severity in ["mild", "moderate", "severe", "extreme"]:
        p = generate_crash_jump_params(severity)
        print(f"  {severity}: μ={p.mu*100:.0f}%, σ={p.sigma*100:.0f}%, "
              f"λ={p.jump_lambda:.0f}次/年, 跳跃均值={p.jump_mu*100:.0f}%, "
              f"跳跃σ={p.jump_sigma*100:.0f}%")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
