# 股灾压力测试工具

基于巨灾建模框架的事件驱动型股灾压力测试平台。

## 核心理念

将股灾视为"金融自然灾害"，借鉴保险行业30年成熟的巨灾建模方法论（Oasis LMF），用"危险-暴露-脆弱性→损失"的框架分析股票市场风险。

## 架构设计

```
危险层(Hazard)    →  暴露层(Exposure)  →  脆弱性层(Vulnerability)  →  损失计算层(Loss)
历史股灾重演          投资组合持仓            下行beta+行业效应            蒙特卡洛模拟
SDE跳跃扩散(规划)     行业/市值分布           Vine copula(规划)           VaR/CVaR/最大回撤
系统动力学(规划)      跨市场/跨资产(规划)     财务脆弱性(规划)            损失超越概率曲线
情绪NLP校准(规划)                                              仓位建议
```

## 第一版功能

- ✅ 投资组合管理（手动添加/示例组合）
- ✅ 历史股灾事件库（2008金融危机、2020新冠、2022中概股、2023硅谷银行、1987黑色星期五、2000互联网泡沫）
- ✅ 蒙特卡洛模拟（10000+事件，带强度扰动和个股残差）
- ✅ 脆弱性模型（下行beta + 行业固定效应）
- ✅ 风险度量（预期损失、VaR 95%/99%、CVaR、最大回撤）
- ✅ 损失超越概率曲线（EP曲线，类似保险巨灾模型）
- ✅ 行业损失贡献分析
- ✅ 仓位建议（基于风险预算：波动越大，仓位越小）
- ✅ Streamlit Web界面
- ✅ 结果下载（CSV/TXT报告）

## 快速开始

### 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 运行

```bash
streamlit run app.py
```

浏览器自动打开 http://localhost:8501

## 使用流程

1. **投资组合**：加载示例组合或手动添加股票
2. **股灾情景**：选择用于模拟的历史股灾事件
3. **压力测试**：点击运行，查看损失分布、VaR/CVaR、仓位建议

## 项目结构

```
crash_simulator/
├── app.py                    # Streamlit Web界面
├── requirements.txt          # Python依赖
├── README.md                 # 项目说明
├── .gitignore                # Git忽略文件
├── data/
│   └── historical_crashes.csv  # 历史股灾数据
└── src/
    ├── __init__.py
    ├── exposure.py           # 暴露层：投资组合数据结构
    ├── hazard.py             # 危险层：股灾事件集生成
    ├── vulnerability.py      # 脆弱性层：beta+行业效应
    ├── loss.py               # 损失计算层：蒙特卡洛+风险度量
    └── advice.py             # 仓位建议模块
```

## 技术栈

- **Python 3.12** - 主开发语言
- **pandas/numpy** - 数据处理和向量化计算
- **Streamlit** - Web界面
- **Plotly** - 可视化
- **yfinance** - 市场数据（第二版）

## 后续规划

### 第二版（2-4周）
- Vine copula尾部依赖建模
- 系统动力学反馈回路（杠杆爆仓→强制卖出→更跌）
- SDE跳跃扩散事件生成（yuima R包）
- 行业传导矩阵
- 对冲方案建议

### 第三版（长期）
- 情绪NLP校准（雪球/评论数据）
- XBRL财务脆弱性（美股SEC数据）
- 政策效果模拟
- 批量回测和模型验证
- 插件式模型架构
- C++核心计算引擎（pybind11，参考Oasis ktools）

## 免责声明

本工具仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

## 参考文献

- Oasis LMF: https://oasislmf.org/ - 开源巨灾建模框架
- CLIMADA: https://climada.ethz.ch/ - ETH Zurich气候风险评估平台
- 巴塞尔协议III - 银行风险资本要求
- Solvency II - 欧盟保险偿付能力监管
