#!/bin/bash
# 启动Streamlit应用

cd /home/erp/crash_simulator

# 先杀掉已有的streamlit进程
pkill -f "streamlit run" 2>/dev/null
sleep 1

# 启动新的streamlit
nohup /home/erp/crash_simulator/venv/bin/streamlit run /home/erp/crash_simulator/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    > /home/erp/crash_simulator/streamlit.log 2>&1 &

echo "Streamlit启动中..."
sleep 3

# 检查是否启动成功
if pgrep -f "streamlit run" > /dev/null; then
    echo "✓ Streamlit启动成功！"
    echo "  地址: http://localhost:8501"
    echo "  日志: /home/erp/crash_simulator/streamlit.log"
else
    echo "✗ Streamlit启动失败！"
    echo "日志内容:"
    cat /home/erp/crash_simulator/streamlit.log
fi
