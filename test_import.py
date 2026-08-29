#!/usr/bin/env python3
"""测试app.py的导入"""

import sys
sys.path.insert(0, '/home/erp/crash_simulator')

print("测试模块导入...")

try:
    from src.exposure import Portfolio, Position, create_sample_portfolio
    print("✓ exposure 导入成功")
except Exception as e:
    print(f"✗ exposure 导入失败: {e}")

try:
    from src.hazard import HazardEngine, CrashEvent
    print("✓ hazard 导入成功")
except Exception as e:
    print(f"✗ hazard 导入失败: {e}")

try:
    from src.vulnerability import VulnerabilityEngine, VineCopulaVulnerability
    print("✓ vulnerability 导入成功")
except Exception as e:
    print(f"✗ vulnerability 导入失败: {e}")

try:
    from src.loss import LossEngine
    print("✓ loss 导入成功")
except Exception as e:
    print(f"✗ loss 导入失败: {e}")

try:
    from src.advice import PositionAdvisor
    print("✓ advice 导入成功")
except Exception as e:
    print(f"✗ advice 导入失败: {e}")

try:
    from src.system_dynamics import SystemDynamicsEngine, FeedbackParams
    print("✓ system_dynamics 导入成功")
except Exception as e:
    print(f"✗ system_dynamics 导入失败: {e}")

try:
    from src.vine_copula import VineCopulaModel, generate_sample_returns
    print("✓ vine_copula 导入成功")
except Exception as e:
    print(f"✗ vine_copula 导入失败: {e}")

print("\n所有模块导入测试完成！")
