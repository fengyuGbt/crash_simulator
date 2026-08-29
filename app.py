"""
股灾压力测试工具 - Streamlit Web界面（第二版）

基于巨灾建模框架的事件驱动型股灾压力测试平台
核心框架：危险(Hazard) -> 暴露(Exposure) -> 脆弱性(Vulnerability) -> 损失(Loss)

第二版新增：
- 系统动力学反馈回路（杠杆爆仓→强制卖出→更跌）
- Vine copula尾部依赖（危机时相关性飙升）
- 政策干预模拟（限制杠杆/救市）
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
from src.hazard import HazardEngine, CrashEvent
from src.vulnerability import VulnerabilityEngine, VineCopulaVulnerability
from src.loss import LossEngine
from src.advice import PositionAdvisor
from src.system_dynamics import SystemDynamicsEngine, FeedbackParams
from src.vine_copula import VineCopulaModel, generate_sample_returns
from src.jump_diffusion import JumpDiffusionModel, JumpDiffusionParams, generate_crash_jump_params

# 页面配置
st.set_page_config(
    page_title="股灾压力测试工具 v2",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 标题
st.title("📉 股灾压力测试工具 v2")
st.caption("基于巨灾建模框架 | 系统动力学反馈回路 | Vine copula尾部依赖 | 政策干预模拟")

# 初始化引擎（缓存）
@st.cache_resource
def get_engines():
    hazard_engine = HazardEngine()
    vulnerability_engine = VulnerabilityEngine()
    loss_engine = LossEngine(hazard_engine, vulnerability_engine)
    advisor = PositionAdvisor()
    sd_engine = SystemDynamicsEngine()
    return hazard_engine, vulnerability_engine, loss_engine, advisor, sd_engine

hazard_engine, vulnerability_engine, loss_engine, advisor, sd_engine = get_engines()

# 侧边栏：参数配置
with st.sidebar:
    st.header("⚙️ 参数配置")

    # 危险模型选择
    st.subheader("危险模型（Hazard）")
    hazard_model = st.radio(
        "选择危险模型",
        ["历史股灾重演", "系统动力学反馈", "SDE跳跃扩散"],
        help="历史股灾重演：用真实历史股灾数据；系统动力学：模拟杠杆爆仓→强制卖出→更跌的反馈回路；SDE跳跃扩散：连续扩散+泊松跳跃，模拟黑天鹅事件"
    )

    if hazard_model == "历史股灾重演":
        available_crashes = hazard_engine.get_available_crashes()
        selected_names = st.multiselect(
            "选择股灾事件",
            options=[c["event_name"] for c in available_crashes],
            default=[c["event_name"] for c in available_crashes],
        )
        name_to_id = {c["event_name"]: c["event_id"] for c in available_crashes}
        selected_ids = [name_to_id[name] for name in selected_names] if selected_names else None
    elif hazard_model == "系统动力学反馈":
        # 系统动力学参数
        st.markdown("**系统动力学参数**")
        initial_shock = st.slider("初始冲击", min_value=-0.30, max_value=-0.05, value=-0.10, step=0.01,
                                   format="%.0f%%", help="股灾开始时的初始跌幅")
        n_days = st.slider("模拟天数", min_value=30, max_value=120, value=60, step=10)

        st.markdown("**反馈回路参数**")
        leverage_ratio = st.slider("市场平均杠杆率", min_value=1.0, max_value=3.0, value=1.5, step=0.1,
                                    help="杠杆率越高，爆仓反馈越强")
        sentiment_sensitivity = st.slider("情绪敏感度", min_value=0.5, max_value=5.0, value=2.0, step=0.5,
                                            help="价格下跌对情绪的影响程度")
        liquidity_sensitivity = st.slider("流动性敏感度", min_value=0.5, max_value=3.0, value=1.5, step=0.5,
                                           help="价格下跌对流动性的影响程度")

        st.markdown("**政策干预**")
        policy_intervention = st.checkbox("启用政策干预", value=False,
                                            help="模拟政府救市/限制杠杆等政策对股灾的影响")
        if policy_intervention:
            intervention_threshold = st.slider("干预触发阈值", min_value=-0.30, max_value=-0.10, value=-0.15,
                                                step=0.01, format="%.0f%%")
            intervention_strength = st.slider("干预强度", min_value=0.1, max_value=1.0, value=0.5, step=0.1,
                                                help="政策托底的强度")

    else:  # SDE跳跃扩散
        st.markdown("**SDE跳跃扩散参数**")
        jd_severity = st.selectbox(
            "股灾严重程度",
            ["mild（轻度）", "moderate（中度）", "severe（重度）", "extreme（极端）", "自定义"],
            index=1,
            help="mild: 正常调整；moderate: 类似2022熊市；severe: 类似2008金融危机；extreme: 类似1929大萧条"
        )

        if jd_severity == "自定义":
            st.markdown("**扩散部分**")
            jd_mu = st.slider("年化漂移率 μ", min_value=-0.20, max_value=0.20, value=0.0, step=0.01,
                               format="%.0f%%", help="长期趋势收益率")
            jd_sigma = st.slider("年化波动率 σ", min_value=0.10, max_value=0.80, value=0.35, step=0.05,
                                  format="%.0f%%", help="正常波动幅度")

            st.markdown("**跳跃部分**")
            jd_lambda = st.slider("跳跃强度 λ（次/年）", min_value=0.0, max_value=20.0, value=4.0, step=1.0,
                                   help="每年发生跳跃的期望次数")
            jd_jump_mu = st.slider("跳跃幅度均值", min_value=-0.30, max_value=0.10, value=-0.08, step=0.01,
                                    format="%.0f%%", help="跳跃的平均幅度（负数表示向下跳）")
            jd_jump_sigma = st.slider("跳跃幅度标准差", min_value=0.02, max_value=0.40, value=0.12, step=0.02,
                                       format="%.0f%%", help="跳跃幅度的波动程度")

            jd_n_days = st.slider("模拟天数", min_value=60, max_value=365, value=180, step=30)
        else:
            # 使用预设参数，只显示摘要
            severity_map = {
                "mild（轻度）": "mild",
                "moderate（中度）": "moderate",
                "severe（重度）": "severe",
                "extreme（极端）": "extreme",
            }
            jd_severity_key = severity_map[jd_severity]
            from src.jump_diffusion import generate_crash_jump_params
            _jd_params = generate_crash_jump_params(jd_severity_key)
            st.info(f"""
            **当前参数（{jd_severity}）**：
            - 漂移率 μ: {_jd_params.mu*100:.0f}%
            - 波动率 σ: {_jd_params.sigma*100:.0f}%
            - 跳跃强度 λ: {_jd_params.jump_lambda:.0f}次/年
            - 跳跃幅度均值: {_jd_params.jump_mu*100:.0f}%
            - 跳跃幅度标准差: {_jd_params.jump_sigma*100:.0f}%
            - 模拟天数: {_jd_params.n_days}天
            """)

        st.markdown("**股灾筛选**")
        jd_crash_threshold = st.slider("股灾阈值（最大回撤）", min_value=-0.40, max_value=-0.10, value=-0.20,
                                        step=0.05, format="%.0f%%",
                                        help="最大回撤超过此阈值的情景才被视为股灾")
        jd_n_scenarios = st.slider("股灾情景数量", min_value=10, max_value=200, value=50, step=10,
                                    help="从模拟中筛选出的股灾情景数量")

    # 脆弱性模型选择
    st.subheader("脆弱性模型（Vulnerability）")
    vulnerability_model = st.radio(
        "选择脆弱性模型",
        ["Beta + 行业效应", "Vine copula尾部依赖"],
        help="Beta模型：简单线性；Vine copula：捕捉危机时股票间相关性飙升"
    )

    # 蒙特卡洛参数
    st.subheader("蒙特卡洛模拟")
    n_simulations = st.slider("模拟次数", min_value=1000, max_value=50000, value=10000, step=1000)
    intensity_noise = st.slider("强度扰动范围", min_value=0.0, max_value=0.5, value=0.2, step=0.05,
                                  help="股灾强度的随机扰动比例")
    add_noise = st.checkbox("添加个股残差", value=True)

    # 仓位建议参数
    st.subheader("仓位建议")
    risk_budget_pct = st.slider("单笔风险预算比例", min_value=0.01, max_value=0.05, value=0.02, step=0.005,
                                  format="%.1f%%")
    total_capital = st.number_input("总本金（元）", min_value=10000, value=100000, step=10000)

    st.divider()
    st.caption("💡 波动越大，止损距离越宽，能买的仓位越小")

# 主区域：分四个步骤
tab1, tab2, tab3, tab4 = st.tabs(["① 投资组合", "② 股灾情景", "③ 系统动力学", "④ 压力测试结果"])

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

    if hazard_model == "历史股灾重演":
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

    elif hazard_model == "系统动力学反馈":
        st.subheader("系统动力学股灾模拟")
        st.info("系统动力学模拟股灾中的内生反馈回路：杠杆爆仓→强制卖出→更跌，情绪恐慌→抛售→更跌，流动性枯竭→价差扩大→更跌")

        # 运行系统动力学模拟
        params = FeedbackParams(
            leverage_ratio=leverage_ratio,
            sentiment_sensitivity=sentiment_sensitivity,
            liquidity_sensitivity=liquidity_sensitivity,
            policy_intervention=policy_intervention,
            intervention_threshold=intervention_threshold if policy_intervention else -0.20,
            intervention_strength=intervention_strength if policy_intervention else 0.3,
        )
        sd_engine_local = SystemDynamicsEngine(params)
        sim_df = sd_engine_local.simulate(initial_shock=initial_shock, n_days=n_days, random_seed=42)
        summary = sd_engine_local.get_crash_summary(sim_df)

        # 显示摘要
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("初始冲击", f"{initial_shock*100:.0f}%")
        with col2:
            st.metric("最大跌幅", f"{summary['最大跌幅']*100:.1f}%")
        with col3:
            st.metric("见底天数", f"第{summary['最大跌幅天数']}天")
        with col4:
            st.metric("放大倍数", f"{summary['最大跌幅']/initial_shock:.1f}x")

        # 价格路径图
        st.subheader("价格路径")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["price"], mode="lines", name="价格指数",
                                  line=dict(color="red", width=2)))
        fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="初始价格=100")
        fig.update_layout(title="股灾价格路径（系统动力学模拟）", xaxis_title="天数", yaxis_title="价格指数")
        st.plotly_chart(fig, use_container_width=True)

        # 反馈回路指标
        st.subheader("反馈回路指标")
        col1, col2 = st.columns(2)
        with col1:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["leverage_exposure"], mode="lines", name="杠杆敞口", line=dict(color="orange")))
            fig1.update_layout(title="杠杆敞口变化（爆仓反馈）", xaxis_title="天数", yaxis_title="杠杆敞口")
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["liquidity"], mode="lines", name="流动性", line=dict(color="blue")))
            fig2.update_layout(title="流动性变化（流动性枯竭反馈）", xaxis_title="天数", yaxis_title="流动性指数")
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["sentiment"], mode="lines", name="情绪指数", line=dict(color="purple")))
            fig3.update_layout(title="情绪变化（恐慌反馈）", xaxis_title="天数", yaxis_title="情绪指数（0=极度恐慌，1=极度乐观）")
            st.plotly_chart(fig3, use_container_width=True)

            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["forced_selling"], mode="lines", name="强制卖出", line=dict(color="red")))
            fig4.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["panic_selling"], mode="lines", name="恐慌卖出", line=dict(color="darkred")))
            fig4.update_layout(title="卖出压力（强制+恐慌）", xaxis_title="天数", yaxis_title="卖出压力")
            st.plotly_chart(fig4, use_container_width=True)

        # 政策干预对比
        if policy_intervention:
            st.subheader("政策干预效果对比")
            params_no_int = FeedbackParams(
                leverage_ratio=leverage_ratio,
                sentiment_sensitivity=sentiment_sensitivity,
                liquidity_sensitivity=liquidity_sensitivity,
                policy_intervention=False,
            )
            sd_no_int = SystemDynamicsEngine(params_no_int)
            sim_no_int = sd_no_int.simulate(initial_shock=initial_shock, n_days=n_days, random_seed=42)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sim_no_int["day"], y=sim_no_int["price"], mode="lines", name="无干预", line=dict(color="red", width=2)))
            fig.add_trace(go.Scatter(x=sim_df["day"], y=sim_df["price"], mode="lines", name="有干预", line=dict(color="green", width=2)))
            fig.update_layout(title="政策干预对股灾的影响", xaxis_title="天数", yaxis_title="价格指数")
            st.plotly_chart(fig, use_container_width=True)

            max_drop_no = sim_no_int["cumulative_drop"].min()
            max_drop_with = sim_df["cumulative_drop"].min()
            st.info(f"**干预效果**：无干预最大跌幅{max_drop_no*100:.1f}%，有干预最大跌幅{max_drop_with*100:.1f}%，"
                    f"减少跌幅{(max_drop_no-max_drop_with)*100:.1f}个百分点")

    else:  # SDE跳跃扩散
        st.subheader("SDE跳跃扩散股灾模拟")
        st.info("""
        **跳跃扩散模型**：dS/S = μdt + σdW + JdN
        - 连续扩散部分（μdt + σdW）：模拟正常市场波动
        - 跳跃部分（JdN）：泊松过程驱动，模拟黑天鹅事件、财报突变、政策冲击
        - 优势：比纯几何布朗运动更符合实际市场的"尖峰厚尾"特征
        """)

        # 构建参数
        if jd_severity == "自定义":
            jd_params = JumpDiffusionParams(
                mu=jd_mu, sigma=jd_sigma,
                jump_lambda=jd_lambda, jump_mu=jd_jump_mu, jump_sigma=jd_jump_sigma,
                n_days=jd_n_days,
            )
        else:
            severity_map = {
                "mild（轻度）": "mild",
                "moderate（中度）": "moderate",
                "severe（重度）": "severe",
                "extreme（极端）": "extreme",
            }
            jd_params = generate_crash_jump_params(severity_map[jd_severity])

        # 创建模型并运行蒙特卡洛模拟
        jd_model = JumpDiffusionModel(jd_params)

        with st.spinner("正在运行跳跃扩散蒙特卡洛模拟..."):
            jd_results = jd_model.simulate(n_simulations=2000, base_seed=42)

        # 统计结果
        jd_max_dds = [r.max_drawdown for r in jd_results]
        jd_total_returns = [r.total_return for r in jd_results]
        jd_n_jumps = [r.n_jumps for r in jd_results]

        # 显示摘要
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("平均最大回撤", f"{np.mean(jd_max_dds)*100:.1f}%")
        with col2:
            st.metric("5%分位回撤", f"{np.percentile(jd_max_dds, 5)*100:.1f}%")
        with col3:
            st.metric("最坏回撤", f"{np.min(jd_max_dds)*100:.1f}%")
        with col4:
            crash_prob = sum(1 for d in jd_max_dds if d < jd_crash_threshold) / len(jd_max_dds)
            st.metric("股灾概率", f"{crash_prob*100:.1f}%")

        # 价格路径图（显示几条代表性路径）
        st.subheader("价格路径（10条代表性模拟）")
        fig = go.Figure()
        for i in range(min(10, len(jd_results))):
            r = jd_results[i]
            fig.add_trace(go.Scatter(
                x=list(range(len(r.prices))),
                y=r.prices,
                mode="lines",
                name=f"路径{i+1}",
                opacity=0.7,
            ))
        fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="初始价格=100")
        fig.update_layout(
            title="跳跃扩散价格路径（红色标记为发生跳跃的路径）",
            xaxis_title="天数", yaxis_title="价格指数",
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 最大回撤分布
        st.subheader("最大回撤分布")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=[d*100 for d in jd_max_dds],
            nbinsx=50,
            name="最大回撤分布",
            marker_color="rgba(255, 100, 100, 0.7)",
        ))
        fig.add_vline(x=jd_crash_threshold*100, line_dash="dash", line_color="red",
                      annotation_text=f"股灾阈值: {jd_crash_threshold*100:.0f}%")
        fig.update_layout(
            title="最大回撤分布（2000次蒙特卡洛模拟）",
            xaxis_title="最大回撤 (%)", yaxis_title="模拟次数",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 跳跃次数分布
        st.subheader("跳跃次数分布")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=jd_n_jumps,
            nbinsx=20,
            name="跳跃次数分布",
            marker_color="rgba(100, 149, 237, 0.7)",
        ))
        fig.update_layout(
            title=f"跳跃次数分布（期望λ={jd_params.jump_lambda:.1f}次/年）",
            xaxis_title="跳跃次数", yaxis_title="模拟次数",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 筛选股灾情景
        st.subheader(f"股灾情景列表（筛选{jd_n_scenarios}个，回撤>{jd_crash_threshold*100:.0f}%）")
        with st.spinner("正在筛选股灾情景..."):
            jd_scenarios = jd_model.get_crash_scenarios(
                n_scenarios=jd_n_scenarios,
                crash_threshold=jd_crash_threshold,
                params=jd_params,
                base_seed=42,
            )

        scenario_df = pd.DataFrame([{
            "情景ID": s["scenario_id"],
            "最大回撤": f"{s['max_drawdown']*100:.1f}%",
            "见底天数": f"第{s['crash_day']}天",
            "跳跃次数": s["n_jumps"],
            "总收益率": f"{s['total_return']*100:.1f}%",
        } for s in jd_scenarios])
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

        # 股灾情景价格路径对比
        st.subheader("股灾情景价格路径对比")
        fig = go.Figure()
        for s in jd_scenarios[:5]:
            fig.add_trace(go.Scatter(
                x=list(range(len(s["price_path"]))),
                y=s["price_path"],
                mode="lines",
                name=f"{s['scenario_id']} (回撤{s['max_drawdown']*100:.0f}%)",
            ))
        fig.add_hline(y=100, line_dash="dash", line_color="gray")
        fig.update_layout(
            title="前5个股灾情景的价格路径",
            xaxis_title="天数", yaxis_title="价格指数",
        )
        st.plotly_chart(fig, use_container_width=True)

# ========== Tab 3: 系统动力学（独立展示） ==========
with tab3:
    st.header("③ 系统动力学深度分析")

    st.subheader("不同初始冲击的放大效应")
    shocks = [-0.05, -0.10, -0.15, -0.20, -0.25]
    shock_results = []
    for shock in shocks:
        sim = sd_engine.simulate(initial_shock=shock, n_days=60, random_seed=42)
        max_drop = sim["cumulative_drop"].min()
        shock_results.append({
            "初始冲击": f"{shock*100:.0f}%",
            "最大跌幅": f"{max_drop*100:.1f}%",
            "放大倍数": f"{max_drop/shock:.1f}x",
            "见底天数": int(sim.loc[sim["cumulative_drop"].idxmin(), "day"]),
        })
    st.dataframe(pd.DataFrame(shock_results), use_container_width=True, hide_index=True)

    st.subheader("反馈回路原理")
    st.markdown("""
    **杠杆爆仓反馈**：
    价格下跌 → 杠杆账户维持保证金不足 → 强制平仓卖出 → 价格更跌 → 更多账户爆仓

    **情绪恐慌反馈**：
    价格下跌 → 投资者恐慌 → 散户抛售 → 价格更跌 → 更恐慌

    **流动性枯竭反馈**：
    价格下跌 → 市场流动性下降 → 买卖价差扩大 → 被迫以更低价卖出 → 价格更跌

    **政策干预**：
    价格跌到阈值 → 政府注入流动性/限制做空/国家队买入 → 切断反馈回路 → 跌幅收窄
    """)

# ========== Tab 4: 压力测试结果 ==========
with tab4:
    st.header("④ 压力测试结果（损失层）")

    if "portfolio" not in st.session_state or len(st.session_state.portfolio.positions) == 0:
        st.warning("请先在「投资组合」标签页添加股票")
    else:
        portfolio = st.session_state.portfolio

        if st.button("🚀 运行压力测试", type="primary", use_container_width=True):
            with st.spinner("正在运行蒙特卡洛模拟..."):
                # 根据选择的危险模型生成事件集
                if hazard_model == "历史股灾重演":
                    results, loss_df = loss_engine.run_monte_carlo(
                        portfolio=portfolio,
                        selected_event_ids=selected_ids,
                        n_simulations=n_simulations,
                        intensity_noise=intensity_noise,
                        add_noise=add_noise,
                        random_seed=42,
                    )
                elif hazard_model == "系统动力学反馈":
                    # 系统动力学：生成多个股灾情景
                    scenarios = sd_engine.generate_crash_scenarios(
                        n_scenarios=min(n_simulations // 10, 5000),
                        initial_shock_range=(initial_shock - 0.05, initial_shock + 0.05),
                        n_days=n_days,
                        base_seed=42,
                    )
                    # 转换为CrashEvent并计算损失
                    results = []
                    loss_data = []
                    for i, scenario in enumerate(scenarios):
                        event = CrashEvent(
                            event_id=f"SD_{i:04d}",
                            event_name="系统动力学股灾",
                            event_type="系统性股灾",
                            start_date="2025-01-01",
                            end_date="2025-03-01",
                            duration_days=int(scenario["最大跌幅天数"]),
                            market_drop=scenario["最大跌幅"],
                            affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
                            probability=0.02,
                            description="系统动力学模拟的股灾情景",
                            seed=i,
                        )

                        # 根据脆弱性模型计算损失
                        if vulnerability_model == "Vine copula尾部依赖":
                            vine_vuln = VineCopulaVulnerability(use_sample_data=True)
                            vuln_results = vine_vuln.calculate_portfolio(portfolio, event, n_simulations=50)
                        else:
                            vuln_results = vulnerability_engine.calculate_portfolio(portfolio, event, add_noise=add_noise)

                        total_loss = 0.0
                        position_losses = {}
                        for vr, position in zip(vuln_results, portfolio.positions):
                            loss = position.market_value * abs(vr.final_drop)
                            position_losses[position.ticker] = loss
                            total_loss += loss

                        total_loss_pct = total_loss / portfolio.total_value if portfolio.total_value > 0 else 0
                        from src.loss import LossResult
                        result = LossResult(
                            event_id=event.event_id,
                            event_name=event.event_name,
                            market_drop=event.market_drop,
                            portfolio_drop=total_loss_pct,
                            total_loss=total_loss,
                            total_loss_pct=total_loss_pct,
                            position_losses=position_losses,
                        )
                        results.append(result)
                        loss_data.append({
                            "event_id": event.event_id,
                            "event_name": event.event_name,
                            "market_drop": event.market_drop,
                            "portfolio_drop": total_loss_pct,
                            "total_loss": total_loss,
                            "total_loss_pct": total_loss_pct,
                        })

                    loss_df = pd.DataFrame(loss_data)

                else:  # SDE跳跃扩散
                    # 构建参数
                    if jd_severity == "自定义":
                        jd_params_test = JumpDiffusionParams(
                            mu=jd_mu, sigma=jd_sigma,
                            jump_lambda=jd_lambda, jump_mu=jd_jump_mu, jump_sigma=jd_jump_sigma,
                            n_days=jd_n_days,
                        )
                    else:
                        severity_map = {
                            "mild（轻度）": "mild",
                            "moderate（中度）": "moderate",
                            "severe（重度）": "severe",
                            "extreme（极端）": "extreme",
                        }
                        jd_params_test = generate_crash_jump_params(severity_map[jd_severity])

                    # 创建模型并筛选股灾情景
                    jd_model_test = JumpDiffusionModel(jd_params_test)
                    jd_scenarios = jd_model_test.get_crash_scenarios(
                        n_scenarios=min(jd_n_scenarios, n_simulations // 10),
                        crash_threshold=jd_crash_threshold,
                        params=jd_params_test,
                        base_seed=42,
                    )

                    # 转换为CrashEvent并计算损失
                    results = []
                    loss_data = []
                    for i, scenario in enumerate(jd_scenarios):
                        event = CrashEvent(
                            event_id=scenario["scenario_id"],
                            event_name="跳跃扩散股灾",
                            event_type="系统性股灾",
                            start_date="2025-01-01",
                            end_date="2025-12-31",
                            duration_days=scenario["crash_day"],
                            market_drop=scenario["max_drawdown"],
                            affected_sectors=["科技", "消费", "金融", "医疗", "能源", "工业", "公用事业", "地产"],
                            probability=0.02,
                            description=f"SDE跳跃扩散模型生成的股灾情景，跳跃{scenario['n_jumps']}次",
                            seed=i,
                        )

                        # 根据脆弱性模型计算损失
                        if vulnerability_model == "Vine copula尾部依赖":
                            vine_vuln = VineCopulaVulnerability(use_sample_data=True)
                            vuln_results = vine_vuln.calculate_portfolio(portfolio, event, n_simulations=50)
                        else:
                            vuln_results = vulnerability_engine.calculate_portfolio(portfolio, event, add_noise=add_noise)

                        total_loss = 0.0
                        position_losses = {}
                        for vr, position in zip(vuln_results, portfolio.positions):
                            loss = position.market_value * abs(vr.final_drop)
                            position_losses[position.ticker] = loss
                            total_loss += loss

                        total_loss_pct = total_loss / portfolio.total_value if portfolio.total_value > 0 else 0
                        from src.loss import LossResult
                        result = LossResult(
                            event_id=event.event_id,
                            event_name=event.event_name,
                            market_drop=event.market_drop,
                            portfolio_drop=total_loss_pct,
                            total_loss=total_loss,
                            total_loss_pct=total_loss_pct,
                            position_losses=position_losses,
                        )
                        results.append(result)
                        loss_data.append({
                            "event_id": event.event_id,
                            "event_name": event.event_name,
                            "market_drop": event.market_drop,
                            "portfolio_drop": total_loss_pct,
                            "total_loss": total_loss,
                            "total_loss_pct": total_loss_pct,
                        })

                    loss_df = pd.DataFrame(loss_data)

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

                st.success(f"模拟完成！共 {len(results)} 次模拟")

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
                report = f"""
股灾压力测试报告
================
生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

投资组合：{portfolio.name}
总市值：${portfolio.total_value:,.0f}
股票数量：{len(portfolio.positions)}

危险模型：{hazard_model}
脆弱性模型：{vulnerability_model}
模拟次数：{n_simulations}

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
🔬 **第二版特性**：系统动力学反馈回路 + Vine copula尾部依赖 + 政策干预模拟
""")
