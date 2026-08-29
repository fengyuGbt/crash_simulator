#!/bin/bash
# 股灾压力测试工具 - 安装脚本

set -e

cd /home/erp/crash_simulator

echo "=== 创建Python虚拟环境 ==="
python3 -m venv venv
source venv/bin/activate

echo "=== 升级pip ==="
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "=== 安装依赖 ==="
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "=== 安装完成 ==="
echo "虚拟环境: /home/erp/crash_simulator/venv"
echo "启动命令: source venv/bin/activate && streamlit run app.py"
echo ""

# 验证安装
echo "=== 验证安装 ==="
python -c "import streamlit, pandas, numpy, plotly; print('所有依赖安装成功')"
