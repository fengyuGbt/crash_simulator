"""
yuima R包集成模块

用yuima R包对SDE模型进行参数估计，然后将估计结果传递给Python的跳跃扩散模型。

核心功能：
1. fit_gbm_params: 用yuima拟合GBM模型（dX = mu*dt + sigma*dW）
2. fit_jump_diffusion_params: 用yuima拟合跳跃扩散模型（后续扩展）
3. estimate_from_prices: 从价格序列估计参数

依赖：
- yuima R包（1.15.34），安装在micromamba的r-yuima环境中
- jsonlite R包（用于JSON输出）
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class SDEEstimationResult:
    """SDE参数估计结果"""
    ticker: str
    n_observations: int
    mu_annual: float  # 年化对数漂移（趋势）
    sigma_annual: float  # 年化波动率（SDE估计）
    rv_annual: float  # 已实现波动率（收益率标准差）
    mu_se: Optional[float] = None  # mu的标准误
    sigma_se: Optional[float] = None  # sigma的标准误
    log_likelihood: Optional[float] = None  # 对数似然
    aic: Optional[float] = None  # AIC
    bic: Optional[float] = None  # BIC
    success: bool = True
    error_message: Optional[str] = None

    @property
    def sharpe_approx(self) -> float:
        """夏普比率近似（mu/sigma）"""
        if self.sigma_annual > 0:
            return self.mu_annual / self.sigma_annual
        return float('nan')

    @property
    def sigma_vs_rv_ratio(self) -> float:
        """SDE波动率与已实现波动率的比值"""
        if self.rv_annual > 0:
            return self.sigma_annual / self.rv_annual
        return float('nan')

    def summary(self) -> str:
        """生成摘要文本"""
        lines = [
            f"SDE参数估计结果（{self.ticker}）",
            f"  样本数: {self.n_observations}",
            f"  年化漂移 μ: {self.mu_annual:.4f} ({self.mu_annual*100:.2f}%)",
            f"  年化波动 σ(SDE): {self.sigma_annual:.4f} ({self.sigma_annual*100:.2f}%)",
            f"  已实现波动 σ(RV): {self.rv_annual:.4f} ({self.rv_annual*100:.2f}%)",
            f"  夏普近似: {self.sharpe_approx:.3f}",
            f"  SDE/RV比值: {self.sigma_vs_rv_ratio:.3f}",
        ]
        if self.log_likelihood is not None:
            lines.append(f"  对数似然: {self.log_likelihood:.2f}")
        if self.aic is not None:
            lines.append(f"  AIC: {self.aic:.2f}")
        if self.bic is not None:
            lines.append(f"  BIC: {self.bic:.2f}")
        if not self.success:
            lines.append(f"  错误: {self.error_message}")
        return "\n".join(lines)


class YuimaEstimator:
    """
    yuima R包参数估计器

    用法：
        estimator = YuimaEstimator()
        result = estimator.fit_gbm(prices, ticker="AAPL")
        print(result.summary())
    """

    def __init__(self, r_script_path: Optional[str] = None, timeout: int = 300):
        """
        初始化估计器

        :param r_script_path: fit_sde.R脚本的路径，默认为项目根目录下的fit_sde.R
        :param timeout: R脚本运行超时时间（秒）
        """
        if r_script_path is None:
            # 默认为项目根目录下的fit_sde.R
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            r_script_path = os.path.join(project_root, "fit_sde.R")
        self.r_script_path = r_script_path
        self.timeout = timeout

        # 自动探测micromamba的R环境路径
        self._r_cmd = self._detect_r_cmd()

    def _detect_r_cmd(self) -> str:
        """
        自动探测micromamba的R环境路径

        支持以下几种情况：
        1. ~/bin/micromamba run -n r-yuima Rscript（标准安装）
        2. ~/micromamba/envs/r-yuima/bin/Rscript（直接调用）
        3. 系统路径中的Rscript（备用）
        """
        # 方案1：用micromamba run
        micromamba_path = os.path.expanduser("~/bin/micromamba")
        if os.path.exists(micromamba_path):
            return f"MAMBA_ROOT_PREFIX={os.path.expanduser('~/micromamba')} {micromamba_path} run -n r-yuima Rscript"

        # 方案2：直接调用环境中的Rscript
        rscript_path = os.path.expanduser("~/micromamba/envs/r-yuima/bin/Rscript")
        if os.path.exists(rscript_path):
            return rscript_path

        # 方案3：系统路径中的Rscript
        return "Rscript"

    def fit_gbm(self, prices: pd.Series, ticker: str = "UNKNOWN") -> SDEEstimationResult:
        """
        用yuima拟合GBM模型（对数价格的带漂移布朗运动）

        模型：dX = mu*dt + sigma*dW，其中X = log(price)

        :param prices: 价格序列（pd.Series，索引为日期）
        :param ticker: 股票代码
        :return: SDEEstimationResult
        """
        # 准备数据
        if isinstance(prices, pd.Series):
            df = pd.DataFrame({
                'date': prices.index,
                'close': prices.values
            })
        else:
            df = pd.DataFrame({
                'date': range(len(prices)),
                'close': prices
            })

        # 过滤无效数据
        df = df.dropna()
        df = df[df['close'] > 0]
        df = df.sort_values('date')

        if len(df) < 10:
            return SDEEstimationResult(
                ticker=ticker,
                n_observations=len(df),
                mu_annual=0.0,
                sigma_annual=0.0,
                rv_annual=0.0,
                success=False,
                error_message=f"数据点太少（{len(df)}个），至少需要10个"
            )

        # 创建临时文件
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, f"{ticker}_px.csv")
            out_path = os.path.join(tmpdir, f"{ticker}_sde.json")

            # 保存CSV
            df.to_csv(csv_path, index=False)

            # 调用R脚本
            cmd = f"{self._r_cmd} {self.r_script_path} {csv_path} {out_path} {ticker}"
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
            except subprocess.TimeoutExpired:
                return SDEEstimationResult(
                    ticker=ticker,
                    n_observations=len(df),
                    mu_annual=0.0,
                    sigma_annual=0.0,
                    rv_annual=0.0,
                    success=False,
                    error_message=f"R脚本运行超时（{self.timeout}秒）"
                )

            if proc.returncode != 0:
                return SDEEstimationResult(
                    ticker=ticker,
                    n_observations=len(df),
                    mu_annual=0.0,
                    sigma_annual=0.0,
                    rv_annual=0.0,
                    success=False,
                    error_message=f"R脚本运行失败: {proc.stderr[-500:]}"
                )

            # 读取结果
            if not os.path.exists(out_path):
                return SDEEstimationResult(
                    ticker=ticker,
                    n_observations=len(df),
                    mu_annual=0.0,
                    sigma_annual=0.0,
                    rv_annual=0.0,
                    success=False,
                    error_message="R脚本未生成输出文件"
                )

            with open(out_path, 'r') as f:
                result_data = json.load(f)

        # 解析结果
        mu_annual = result_data.get('mu_annual', 0.0)
        sigma_annual = result_data.get('sigma_annual', 0.0)
        rv_annual = result_data.get('rv_annual', 0.0)
        log_likelihood = result_data.get('loglik', None)

        # 计算AIC和BIC（如果有对数似然）
        aic = None
        bic = None
        if log_likelihood is not None:
            k = 2  # 参数个数（mu, sigma）
            n = result_data.get('n', len(df))
            aic = -2 * log_likelihood + 2 * k
            bic = -2 * log_likelihood + k * np.log(n)

        return SDEEstimationResult(
            ticker=ticker,
            n_observations=result_data.get('n', len(df)),
            mu_annual=mu_annual if not np.isnan(mu_annual) else 0.0,
            sigma_annual=sigma_annual if not np.isnan(sigma_annual) else 0.0,
            rv_annual=rv_annual if not np.isnan(rv_annual) else 0.0,
            mu_se=result_data.get('mu_se_annual', None),
            sigma_se=result_data.get('sigma_se_annual', None),
            log_likelihood=log_likelihood,
            aic=aic,
            bic=bic,
            success=True
        )

    def fit_gbm_from_returns(self, returns: np.ndarray, ticker: str = "UNKNOWN") -> SDEEstimationResult:
        """
        从收益率序列拟合GBM模型

        :param returns: 日收益率序列（对数收益率）
        :param ticker: 股票代码
        :return: SDEEstimationResult
        """
        # 将收益率转换为价格序列（从1开始）
        prices = np.exp(np.cumsum(returns))
        prices = pd.Series(prices, index=range(len(prices)))
        return self.fit_gbm(prices, ticker)


def generate_test_prices(n_days: int = 252, mu: float = 0.08, sigma: float = 0.25,
                         initial_price: float = 100.0, random_seed: int = 42) -> pd.Series:
    """
    生成测试用的GBM价格序列

    :param n_days: 天数
    :param mu: 年化漂移
    :param sigma: 年化波动率
    :param initial_price: 初始价格
    :param random_seed: 随机种子
    :return: 价格序列
    """
    np.random.seed(random_seed)
    dt = 1 / 252
    returns = np.random.normal(mu * dt, sigma * np.sqrt(dt), n_days)
    prices = initial_price * np.exp(np.cumsum(returns))
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='B')
    return pd.Series(prices, index=dates, name='close')


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("yuima R包集成测试")
    print("=" * 60)

    # 生成测试数据
    print("\n生成测试数据（GBM, mu=8%, sigma=25%）...")
    test_prices = generate_test_prices(n_days=504, mu=0.08, sigma=0.25)
    print(f"  数据点数: {len(test_prices)}")
    print(f"  初始价格: {test_prices.iloc[0]:.2f}")
    print(f"  最终价格: {test_prices.iloc[-1]:.2f}")

    # 用yuima估计参数
    print("\n用yuima估计SDE参数...")
    estimator = YuimaEstimator()
    print(f"  R命令: {estimator._r_cmd}")
    result = estimator.fit_gbm(test_prices, ticker="TEST")

    if result.success:
        print("\n" + result.summary())
        print(f"\n参数对比:")
        print(f"  真实 μ: 8.00%, 估计 μ: {result.mu_annual*100:.2f}%")
        print(f"  真实 σ: 25.00%, 估计 σ(SDE): {result.sigma_annual*100:.2f}%")
        print(f"  真实 σ: 25.00%, 估计 σ(RV): {result.rv_annual*100:.2f}%")
    else:
        print(f"\n估计失败: {result.error_message}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
