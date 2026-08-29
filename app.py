"""
股灾压力测试工具 - Streamlit Web界面

基于巨灾建模框架的事件驱动型股灾压力测试平台
核心框架：危险(Hazard) -> 暴露(Exposure) -> 脆弱性(Vulnerability) -> 损失(Loss)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# 添加src到路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.exposure import Portfolio, Position, create_sample_portfolio
from src.hazard import HazardEngine
from src.vulnerability import VulnerabilityEngine
from src.loss import LossEngine
from src.advice import PositionAdvisor


# 页面配置
st.set_page_config(
    page_title="股灾压力测试工具",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 标题
st.title("📉 股灾压力测试工具")
st.caption("基于巨灾建模框架的事件驱动型股灾压力测试平台 | 危险→暴露→脆弱性→损失")

# 初始化引擎（缓存）
@st.cache_resource
def get_engines():
    hazard_engine = HazardEngine()
    vulnerability_engine = VulnerabilityEngine()
    loss_engine = LossEngine(hazard_engine, vulnerability_engine)
    advisor = PositionAdvisor()
    return hazard_engine, vulnerability_engine, loss_engine, advisor

hazard_engine, vulnerability_engine, loss_engine, advisor = get_engines()

# 侧边栏：参数配置
with st.sidebar:
    st.header("⚙️ 参数配置")

    # 模拟参数
    st.subheader("蒙特卡洛模拟")
    n_simulations = st.slider("模拟次数", min_value=1000, max_value=50000, value=10000, step=1000)
    intensity_noise = st.slider("强度扰动范围", min_value=0.0, max_value=0.5, value=0.2, step=0.05,
                                  help="股灾强度的随机扰动比例，0.2表示±20%")
    add_noise = st.checkbox("添加个股残差", value=True, help="为每只股票添加随机扰动，模拟个股特异性风险")

    # 仓位建议参数
    st.subheader("仓位建议")
    risk_budget_pct = st.slider("单笔风险预算比例", min_value=0.01, max_value=0.05, value=0.02, step=0.005,
                                  format="%.1f%%", help="单笔交易最大可接受亏损占总本金比例")
    total_capital = st.number_input("总本金（元）", min_value=10000, value=100000, step=10000)

    st.divider()
    st.caption("💡 波动越大，止损距离越宽，能买的仓位越小")


# 主区域：分三个步骤
tab1, tab2, tab3 = st.tabs(["① 投资组合", "② 股灾情景", "③ 压力测试结果"])

# ========== Tab 1: 投资组合 ==========
with tab1:
    st.header("① 投资组合（暴露层）")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("快速开始")
        if st.button("📋 加载示例组合", use_container_width=True):
            st.session_state.portfolio = create_sample_portfolio()
            st.success("已加载示例组合：科技+消费+金融+医疗")

        if st.button("🗑️ 清空组合", use_container_width=True):
            st.session_state.portfolio = Portfolio(name="空组合")
            st.info("已清空组合")

        # 手动添加股票
        st.subheader("手动添加股票")
        with st.form("add_stock"):
            ticker = st.text_input("股票代码", placeholder="如 AAPL")
            name = st.text_input("公司名称", placeholder="如 苹果")
            sector = st.selectbox("行业", ["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产", "通信", "材料", "其他"])
            shares = st.number_input("持仓量（股）", min_value=0, value=10)
            cost_price = st.number_input("成本价", min_value=0.0, value=100.0)
            current_price = st.number_input("当前价", min_value=0.0, value=120.0)
            beta = st.number_input("Beta", min_value=0.0, value=1.0, step=0.1)
            downside_beta = st.number_input("下行Beta", min_value=0.0, value=1.2, step=0.1)

            submitted = st.form_submit_button("添加到组合", use_container_width=True)
            if submitted and ticker:
                if "portfolio" not in st.session_state:
                    st.session_state.portfolio = Portfolio()
                position = Position(
                    ticker=ticker.upper(), name=name, sector=sector,
                    shares=shares, cost_price=cost_price, current_price=current_price,
                    beta=beta, downside_beta=downside_beta,
                )
                st.session_state.portfolio.add_position(position)
                st.success(f"已添加 {ticker.upper()}")

    with col2:
        st.subheader("当前持仓")
        if "portfolio" not in st.session_state:
            st.session_state.portfolio = create_sample_portfolio()

        portfolio = st.session_state.portfolio

        if len(portfolio.positions) == 0:
            st.warning("组合为空，请添加股票或加载示例组合")
        else:
            df = portfolio.to_dataframe()
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 组合概览
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("总市值", f"${portfolio.total_value:,.0f}")
            with col_b:
                st.metric("总成本", f"${portfolio.total_cost:,.0f}")
            with col_c:
                st.metric("总盈亏", f"${portfolio.total_pnl:,.0f}",
                          delta=f"{portfolio.total_pnl/portfolio.total_cost*100:.1f}%" if portfolio.total_cost > 0 else None)
            with col_d:
                st.metric("加权Beta", f"{portfolio.weighted_beta:.2f}")

            # 行业分布饼图
            st.subheader("行业分布")
            sector_exp = portfolio.sector_exposure
            fig = px.pie(values=sector_exp.values, names=sector_exp.index, title="行业市值占比")
            st.plotly_chart(fig, use_container_width=True)


# ========== Tab 2: 股灾情景 ==========
with tab2:
    st.header("② 股灾情景（危险层）")

    available_crashes = hazard_engine.get_available_crashes()

    st.subheader("可用历史股灾")
    crash_df = pd.DataFrame(available_crashes)
    crash_df_display = crash_df.rename(columns={
        "event_id": "事件ID", "event_name": "事件名称", "event_type": "类型",
        "market_drop": "大盘跌幅", "duration_days": "持续天数",
        "probability": "年化概率", "description": "描述"
    })
    crash_df_display["大盘跌幅"] = crash_df_display["大盘跌幅"].apply(lambda x: f"{x*100:.1f}%")
    crash_df_display["年化概率"] = crash_df_display["年化概率"].apply(lambda x: f"{x*100:.1f}%")
    st.dataframe(crash_df_display, use_container_width=True, hide_index=True)

    st.subheader("选择股灾情景")
    selected_names = st.multiselect(
        "选择用于模拟的股灾事件（不选则使用全部）",
        options=[c["event_name"] for c in available_crashes],
        default=[c["event_name"] for c in available_crashes],
    )

    # 映射名称到ID
    name_to_id = {c["event_name"]: c["event_id"] for c in available_crashes}
    selected_ids = [name_to_id[name] for name in selected_names] if selected_names else None

    # 单情景预览
    st.subheader("单情景预览")
    preview_name = st.selectbox("选择一个股灾查看详情", options=[c["event_name"] for c in available_crashes])
    preview_id = name_to_id[preview_name]
    preview_event = hazard_engine.generate_single_event(preview_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("大盘跌幅", f"{preview_event.market_drop*100:.1f}%")
    with col2:
        st.metric("持续时间", f"{preview_event.duration_days}天")
    with col3:
        st.metric("事件类型", preview_event.event_type)
    with col4:
        st.metric("年化概率", f"{preview_event.probability*100:.1f}%")

    st.info(f"**事件描述**：{preview_event.description}")
    st.info(f"**受影响行业**：{', '.join(preview_event.affected_sectors)}")


# ========== Tab 3: 压力测试结果 ==========
with tab3:
    st.header("③ 压力测试结果（损失层）")

    if "portfolio" not in st.session_state or len(st.session_state.portfolio.positions) == 0:
        st.warning("请先在「投资组合」标签页添加股票")
    else:
        portfolio = st.session_state.portfolio

        if st.button("🚀 运行压力测试", type="primary", use_container_width=True):
            with st.spinner("正在运行蒙特卡洛模拟..."):
                # 运行模拟
                results, loss_df = loss_engine.run_monte_carlo(
                    portfolio=portfolio,
                    selected_event_ids=selected_ids,
                    n_simulations=n_simulations,
                    intensity_noise=intensity_noise,
                    add_noise=add_noise,
                    random_seed=42,
                )

                # 计算风险度量
                risk_metrics = loss_engine.calculate_risk_metrics(loss_df, portfolio.total_value)

                # 损失超越概率曲线
                ep_curve = loss_engine.get_loss_exceedance_curve(loss_df)

                # 行业损失贡献
                sector_contribution = loss_engine.get_sector_loss_contribution(results, portfolio)

                # 仓位建议
                portfolio_advice = advisor.calculate_portfolio_advice(
                    portfolio, total_capital, risk_budget_pct=risk_budget_pct
                )

                # 保存到session
                st.session_state.results = results
                st.session_state.loss_df = loss_df
                st.session_state.risk_metrics = risk_metrics
                st.session_state.ep_curve = ep_curve
                st.session_state.sector_contribution = sector_contribution
                st.session_state.portfolio_advice = portfolio_advice

                st.success(f"模拟完成！共 {n_simulations} 次模拟")

        # 显示结果
        if "risk_metrics" in st.session_state:
            risk_metrics = st.session_state.risk_metrics
            loss_df = st.session_state.loss_df
            ep_curve = st.session_state.ep_curve
            sector_contribution = st.session_state.sector_contribution
            portfolio_advice = st.session_state.portfolio_advice

            # 风险度量概览
            st.subheader("📊 风险度量概览")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("预期损失", f"${risk_metrics.expected_loss:,.0f}",
                          f"{risk_metrics.expected_loss_pct*100:.1f}%")
            with col2:
                st.metric("95% VaR", f"${risk_metrics.var_95:,.0f}",
                          f"{risk_metrics.var_95_pct*100:.1f}%",
                          help="95%置信度下的最大损失")
            with col3:
                st.metric("95% CVaR", f"${risk_metrics.cvar_95:,.0f}",
                          f"{risk_metrics.cvar_95_pct*100:.1f}%",
                          help="超过VaR后的平均损失（尾部期望）")
            with col4:
                st.metric("最坏情况损失", f"${risk_metrics.max_loss:,.0f}",
                          f"{risk_metrics.max_loss_pct*100:.1f}%")

            # 详细风险度量表
            with st.expander("📋 详细风险度量"):
                metrics_data = {
                    "指标": ["预期损失", "95% VaR", "99% VaR", "95% CVaR", "99% CVaR",
                             "最大损失", "最小损失", "损失标准差", "最大回撤（近似）"],
                    "金额": [
                        f"${risk_metrics.expected_loss:,.0f}",
                        f"${risk_metrics.var_95:,.0f}",
                        f"${risk_metrics.var_99:,.0f}",
                        f"${risk_metrics.cvar_95:,.0f}",
                        f"${risk_metrics.cvar_99:,.0f}",
                        f"${risk_metrics.max_loss:,.0f}",
                        f"${risk_metrics.min_loss:,.0f}",
                        f"${risk_metrics.loss_std:,.0f}",
                        f"${risk_metrics.max_drawdown:,.0f}",
                    ],
                    "百分比": [
                        f"{risk_metrics.expected_loss_pct*100:.1f}%",
                        f"{risk_metrics.var_95_pct*100:.1f}%",
                        f"{risk_metrics.var_99_pct*100:.1f}%",
                        f"{risk_metrics.cvar_95_pct*100:.1f}%",
                        f"{risk_metrics.cvar_99_pct*100:.1f}%",
                        f"{risk_metrics.max_loss_pct*100:.1f}%",
                        f"{risk_metrics.min_loss_pct*100:.1f}%",
                        f"{risk_metrics.loss_std_pct*100:.1f}%",
                        f"{risk_metrics.max_drawdown_pct*100:.1f}%",
                    ],
                }
                st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)

            # 损失分布直方图
            st.subheader("📉 损失分布")
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=loss_df["total_loss_pct"] * 100,
                nbinsx=50,
                name="损失分布",
                marker_color="rgba(255, 100, 100, 0.7)",
            ))
            # 添加VaR线
            fig.add_vline(x=risk_metrics.var_95_pct * 100, line_dash="dash", line_color="orange",
                          annotation_text=f"95% VaR: {risk_metrics.var_95_pct*100:.1f}%")
            fig.add_vline(x=risk_metrics.var_99_pct * 100, line_dash="dash", line_color="red",
                          annotation_text=f"99% VaR: {risk_metrics.var_99_pct*100:.1f}%")
            fig.update_layout(
                title="投资组合损失分布（蒙特卡洛模拟）",
                xaxis_title="损失百分比 (%)",
                yaxis_title="模拟次数",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            # 损失超越概率曲线
            st.subheader("📈 损失超越概率曲线（EP曲线）")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ep_curve["loss_threshold_pct"] * 100,
                y=ep_curve["exceedance_probability"] * 100,
                mode="lines",
                name="超越概率",
                line=dict(color="blue", width=2),
                fill="tozeroy",
                fillcolor="rgba(100, 149, 237, 0.2)",
            ))
            fig.update_layout(
                title="损失超越概率曲线（类似保险巨灾模型的EP曲线）",
                xaxis_title="损失阈值 (%)",
                yaxis_title="超越概率 (%)",
                yaxis_type="log",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("💡 EP曲线解读：曲线上任意一点(x,y)表示「损失超过x%的概率是y%」。曲线越陡，尾部风险越大。")

            # 行业损失贡献
            st.subheader("🏭 行业损失贡献")
            fig = px.bar(
                sector_contribution,
                x="行业",
                y="平均损失",
                color="损失率",
                title="各行业平均损失及损失率",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 行业损失贡献详情"):
                sector_display = sector_contribution.copy()
                sector_display["行业市值"] = sector_display["行业市值"].apply(lambda x: f"${x:,.0f}")
                sector_display["平均损失"] = sector_display["平均损失"].apply(lambda x: f"${x:,.0f}")
                sector_display["损失率"] = sector_display["损失率"].apply(lambda x: f"{x*100:.1f}%")
                sector_display["损失贡献度"] = sector_display["损失贡献度"].apply(lambda x: f"{x*100:.1f}%")
                st.dataframe(sector_display, use_container_width=True, hide_index=True)

            # 仓位建议
            st.subheader("💼 仓位建议（基于风险预算）")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总本金", f"${portfolio_advice.total_capital:,.0f}")
            with col2:
                st.metric("总风险预算", f"${portfolio_advice.total_risk_budget:,.0f}",
                          f"{portfolio_advice.total_risk_budget_pct*100:.1f}%")
            with col3:
                st.metric("建议总仓位", f"${portfolio_advice.suggested_total_value:,.0f}",
                          f"{portfolio_advice.suggested_leverage*100:.0f}%")
            with col4:
                st.metric("建议持有现金", f"${portfolio_advice.suggested_cash:,.0f}")

            advice_df = advisor.advice_to_dataframe(portfolio_advice)
            st.dataframe(advice_df, use_container_width=True, hide_index=True)

            st.info("""
            **仓位建议原理**：波动越大 → 止损距离越宽 → 同样的风险预算能买的仓位越小。
            这不是经验之谈，是止损纪律的数学必然。
            """)

            # 下载结果
            st.subheader("📥 下载结果")
            col1, col2 = st.columns(2)
            with col1:
                csv = loss_df.to_csv(index=False).encode('utf-8')
                st.download_button("下载损失分布CSV", csv, "loss_distribution.csv", "text/csv")
            with col2:
                # 生成简单的报告文本
                report = f"""
股灾压力测试报告
================
生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

投资组合：{portfolio.name}
总市值：${portfolio.total_value:,.0f}
股票数量：{len(portfolio.positions)}

模拟参数：
- 模拟次数：{n_simulations}
- 强度扰动：±{intensity_noise*100:.0f}%
- 股灾情景：{', '.join(selected_names) if selected_names else '全部'}

风险度量：
- 预期损失：${risk_metrics.expected_loss:,.0f} ({risk_metrics.expected_loss_pct*100:.1f}%)
- 95% VaR：${risk_metrics.var_95:,.0f} ({risk_metrics.var_95_pct*100:.1f}%)
- 99% VaR：${risk_metrics.var_99:,.0f} ({risk_metrics.var_99_pct*100:.1f}%)
- 95% CVaR：${risk_metrics.cvar_95:,.0f} ({risk_metrics.cvar_95_pct*100:.1f}%)
- 最坏情况：${risk_metrics.max_loss:,.0f} ({risk_metrics.max_loss_pct*100:.1f}%)

仓位建议：
- 建议总仓位：${portfolio_advice.suggested_total_value:,.0f} ({portfolio_advice.suggested_leverage*100:.0f}%)
- 建议持有现金：${portfolio_advice.suggested_cash:,.0f}

免责声明：本工具仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
                """
                st.download_button("下载测试报告TXT", report.encode('utf-8'), "stress_test_report.txt", "text/plain")


# 页脚
st.divider()
st.caption("""
⚠️ **免责声明**：本工具仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。
📚 **方法论**：基于保险行业巨灾建模框架（危险-暴露-脆弱性-损失），将股灾视为"金融自然灾害"进行压力测试。
""")
