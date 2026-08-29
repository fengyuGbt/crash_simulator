#!/usr/bin/env python3
"""探索pyvinecopulib的正确API用法"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

import numpy as np
import pyvinecopulib as pv

print("=" * 60)
print("pyvinecopulib API探索")
print("=" * 60)

print(f"\n版本: {pv.__version__ if hasattr(pv, '__version__') else 'unknown'}")
print(f"\n模块内容:")
for attr in dir(pv):
    if not attr.startswith('_'):
        print(f"  {attr}")

# 生成测试数据
np.random.seed(42)
n = 200
d = 3
data = np.random.normal(size=(n, d))
# 转换为均匀分布
from scipy.stats import norm
u = np.zeros_like(data)
for j in range(d):
    ranks = np.argsort(np.argsort(data[:, j])) + 1
    u[:, j] = ranks / (n + 1)

print(f"\n测试数据形状: {u.shape}")
print(f"数据范围: [{u.min():.3f}, {u.max():.3f}]")

# 探索Vinecop
print("\n" + "=" * 60)
print("Vinecop类探索")
print("=" * 60)

print(f"\nVinecop.__init__ 签名:")
import inspect
try:
    sig = inspect.signature(pv.Vinecop.__init__)
    print(f"  {sig}")
except Exception as e:
    print(f"  获取签名失败: {e}")

print(f"\nVinecop方法:")
for attr in dir(pv.Vinecop):
    if not attr.startswith('_'):
        print(f"  {attr}")

# 尝试不同的拟合方式
print("\n" + "=" * 60)
print("尝试拟合方式1: Vinecop(d) + fit方法")
print("=" * 60)
try:
    vc = pv.Vinecop(d=d)
    print(f"创建成功: {vc}")
    print(f"维度: {vc.dim if hasattr(vc, 'dim') else 'unknown'}")

    # 看看有没有fit方法
    if hasattr(vc, 'fit'):
        print("有fit方法，尝试调用...")
        try:
            vc.fit(u)
            print("fit成功!")
            print(f"对数似然: {vc.loglik(u)}")
        except Exception as e:
            print(f"fit失败: {e}")
    else:
        print("没有fit方法")

    # 看看有没有select方法
    if hasattr(vc, 'select'):
        print("有select方法，尝试调用...")
        try:
            vc.select(u)
            print("select成功!")
        except Exception as e:
            print(f"select失败: {e}")

except Exception as e:
    print(f"创建失败: {e}")

# 尝试方式2: 静态fit方法
print("\n" + "=" * 60)
print("尝试拟合方式2: 静态方法")
print("=" * 60)
try:
    if hasattr(pv.Vinecop, 'fit'):
        print("Vinecop有静态fit方法")
        try:
            vc = pv.Vinecop.fit(u)
            print(f"静态fit成功: {vc}")
        except Exception as e:
            print(f"静态fit失败: {e}")
    else:
        print("Vinecop没有静态fit方法")
except Exception as e:
    print(f"检查失败: {e}")

# 尝试方式3: FitControlsVinecop + 某种fit函数
print("\n" + "=" * 60)
print("尝试拟合方式3: FitControlsVinecop")
print("=" * 60)
try:
    controls = pv.FitControlsVinecop()
    print(f"创建controls成功: {controls}")
    print(f"controls属性:")
    for attr in dir(controls):
        if not attr.startswith('_'):
            print(f"  {attr}")
except Exception as e:
    print(f"创建controls失败: {e}")

# 尝试方式4: 看看有没有fit函数
print("\n" + "=" * 60)
print("尝试拟合方式4: 模块级fit函数")
print("=" * 60)
for name in ['fit', 'fit_vinecop', 'vinecop', 'VinecopFit']:
    if hasattr(pv, name):
        print(f"pv.{name} 存在")
        try:
            obj = getattr(pv, name)
            if callable(obj):
                print(f"  是可调用对象")
                try:
                    sig = inspect.signature(obj)
                    print(f"  签名: {sig}")
                except:
                    pass
        except Exception as e:
            print(f"  检查失败: {e}")

# 尝试Bicop（双变量copula）
print("\n" + "=" * 60)
print("Bicop类探索（双变量copula）")
print("=" * 60)
try:
    print(f"Bicop方法:")
    for attr in dir(pv.Bicop):
        if not attr.startswith('_'):
            print(f"  {attr}")

    # 尝试拟合双变量copula
    print(f"\n尝试拟合双变量copula...")
    u2 = u[:, :2]
    bc = pv.Bicop()
    print(f"创建Bicop成功")
    if hasattr(bc, 'fit'):
        bc.fit(u2)
        print(f"fit成功")
        print(f"族: {bc.family}")
        print(f"参数: {bc.parameters}")
        print(f"tau: {bc.tau()}")
except Exception as e:
    print(f"Bicop探索失败: {e}")

print("\n" + "=" * 60)
print("探索完成")
print("=" * 60)
