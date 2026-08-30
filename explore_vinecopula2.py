#!/usr/bin/env python3
"""探索pyvinecopulib的pair-copula API"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pyvinecopulib as pv
from src.vine_copula import VineCopulaModel, generate_sample_returns

print("=" * 60)
print("pyvinecopulib pair-copula API探索")
print("=" * 60)

# 生成示例数据并拟合
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
returns = generate_sample_returns(tickers, n_days=500, correlation=0.6, tail_dependence=0.5)

model = VineCopulaModel(tickers)
result = model.fit(returns)

print(f"\n拟合成功，参数数={model.model.npars}")
print(f"树的数量: {model.model.dim - 1}")

# 探索families属性
print(f"\n=== families属性 ===")
families = model.model.families
print(f"类型: {type(families)}")
print(f"长度: {len(families)}")
for i, tree in enumerate(families):
    print(f"  树{i}: {len(tree)}个pair-copula")
    for j, fam in enumerate(tree):
        print(f"    边{j}: {fam}")

# 探索parameters属性
print(f"\n=== parameters属性 ===")
parameters = model.model.parameters
print(f"类型: {type(parameters)}")
print(f"长度: {len(parameters)}")
for i, tree in enumerate(parameters):
    print(f"  树{i}: {len(tree)}个参数集")
    for j, params in enumerate(tree):
        print(f"    边{j}: {params}")

# 探索taus属性
print(f"\n=== taus属性 ===")
taus = model.model.taus
print(f"类型: {type(taus)}")
print(f"长度: {len(taus)}")
for i, tree in enumerate(taus):
    print(f"  树{i}: {len(tree)}个tau")
    for j, tau in enumerate(tree):
        print(f"    边{j}: {tau}")

# 探索matrix属性
print(f"\n=== matrix属性 ===")
matrix = model.model.matrix
print(f"类型: {type(matrix)}")
print(f"形状: {matrix.shape}")
print(f"矩阵:")
print(matrix)

# 探索get_pair_copula方法
print(f"\n=== get_pair_copula方法 ===")
print(f"尝试调用 get_pair_copula(0, 0)...")
try:
    pc = model.model.get_pair_copula(0, 0)
    print(f"  成功! 类型: {type(pc)}")
    print(f"  family: {pc.family}")
    print(f"  parameters: {pc.parameters}")
    print(f"  tau: {pc.tau}")
    print(f"  rotation: {pc.rotation}")
except Exception as e:
    print(f"  失败: {e}")

print(f"\n尝试调用 get_pair_copula(0, 1)...")
try:
    pc = model.model.get_pair_copula(0, 1)
    print(f"  成功! family: {pc.family}, parameters: {pc.parameters}, tau: {pc.tau}")
except Exception as e:
    print(f"  失败: {e}")

# 探索BicopFamily枚举
print(f"\n=== BicopFamily枚举 ===")
print(f"所有copula族:")
for fam in pv.BicopFamily:
    print(f"  {fam.name}: {fam}")

# 计算尾部依赖
print(f"\n=== 尾部依赖计算 ===")
from scipy.stats import t as t_dist

def calc_tail_dependence(family, params):
    """根据copula族和参数计算尾部依赖"""
    family_name = str(family).split('.')[-1].lower() if hasattr(family, 'name') else str(family).lower()

    if family_name in ['indep', 'gaussian', 'frank']:
        return 0.0, 0.0
    elif family_name == 'clayton':
        theta = params[0] if len(params) > 0 else 1.0
        lower = 2 ** (-1.0 / theta) if theta > 0 else 0.0
        return lower, 0.0
    elif family_name == 'gumbel':
        theta = params[0] if len(params) > 0 else 1.0
        upper = 2 - 2 ** (1.0 / theta) if theta >= 1 else 0.0
        return 0.0, upper
    elif family_name == 'joe':
        theta = params[0] if len(params) > 0 else 1.0
        upper = 2 - 2 ** (1.0 / theta) if theta >= 1 else 0.0
        return 0.0, upper
    elif family_name == 'student':
        rho = params[0] if len(params) > 0 else 0.0
        nu = params[1] if len(params) > 1 else 5.0
        # Student t copula的尾部依赖
        t_val = np.sqrt((nu + 1) * (1 - rho) / (1 + rho))
        tail = 2 * t_dist.cdf(-t_val, nu + 1)
        return tail, tail
    elif family_name == 'bb1':
        theta = params[0] if len(params) > 0 else 1.0
        kappa = params[1] if len(params) > 1 else 1.0
        lower = 2 ** (-1.0 / (theta * kappa)) if theta > 0 and kappa > 0 else 0.0
        upper = 2 - 2 ** (1.0 / theta) if theta >= 1 else 0.0
        return lower, upper
    elif family_name == 'bb6':
        theta = params[0] if len(params) > 0 else 1.0
        kappa = params[1] if len(params) > 1 else 1.0
        upper = 2 - 2 ** (1.0 / (theta * kappa)) if theta >= 1 and kappa >= 1 else 0.0
        return 0.0, upper
    elif family_name == 'bb7':
        theta = params[0] if len(params) > 0 else 1.0
        kappa = params[1] if len(params) > 1 else 1.0
        lower = 2 ** (-1.0 / kappa) if kappa > 0 else 0.0
        upper = 2 - 2 ** (1.0 / theta) if theta >= 1 else 0.0
        return lower, upper
    elif family_name == 'bb8':
        theta = params[0] if len(params) > 0 else 1.0
        delta = params[1] if len(params) > 1 else 1.0
        upper = 2 - 2 ** (1.0 / theta) if theta >= 1 and delta >= 1 else 0.0
        return 0.0, upper
    else:
        return 0.0, 0.0

# 计算第一棵树中所有pair-copula的尾部依赖
print(f"\n第一棵树中所有pair-copula的尾部依赖:")
print(f"{'边':<4} {'copula族':<12} {'参数':<20} {'tau':<8} {'下尾':<8} {'上尾':<8}")
print("-" * 65)

for j in range(len(families[0])):
    fam = families[0][j]
    params = parameters[0][j]
    tau = taus[0][j]
    lower, upper = calc_tail_dependence(fam, params)
    print(f"{j:<4} {str(fam).split('.')[-1]:<12} {str(params):<20} {tau:<8.3f} {lower:<8.3f} {upper:<8.3f}")

print("\n" + "=" * 60)
print("探索完成")
print("=" * 60)
