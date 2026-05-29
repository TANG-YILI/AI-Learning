import json
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from minimal_agent import generate_ipo_report
from minimal_agent.exporters import markdown_to_pdf_bytes

load_dotenv()

st.set_page_config(page_title="IPO承做智能Agent", layout="wide")
st.title("IPO项目建议书智能生成")
st.caption("给老师用的简化版：加载样例 -> 补充信息 -> 一键生成 -> 下载PDF")


DEFAULT_PAYLOAD = {
    "company_name": "某新能源设备公司",
    "sector": "高端装备制造",
    "listing_market": "上交所主板",
    "equity_story": "公司深耕动力系统核心零部件，具备技术壁垒与客户粘性，受益于行业升级与国产替代。",
    "risks": [
        "下游需求波动导致订单不及预期",
        "原材料价格上涨压缩利润空间",
        "核心技术迭代不及预期",
        "客户集中度较高带来议价风险",
    ],
    "financials": [
        {"year": 2022, "revenue": 21.5, "net_profit": 1.8, "ebitda": 3.2},
        {"year": 2023, "revenue": 28.9, "net_profit": 2.6, "ebitda": 4.4},
        {"year": 2024, "revenue": 36.7, "net_profit": 3.4, "ebitda": 5.6},
    ],
    "peer_multiples": [
        {"name": "可比公司A", "pe": 26, "ps": 3.8},
        {"name": "可比公司B", "pe": 30, "ps": 4.2},
        {"name": "可比公司C", "pe": 24, "ps": 3.5},
    ],
    "proceeds_usage": ["扩产及产线自动化", "研发平台升级", "补充流动资金"],
    "candidate_highlights": "本人曾在券商投行实习，参与招股书底稿整理、可比公司估值、行业数据校验，并用AI将信息披露草稿效率提升约40%。",
}

HUATAI_SAMPLE_PAYLOAD = {
    "company_name": "A公司（IDC园区级数据中心服务商）",
    "sector": "IDC基础设施与运营",
    "listing_market": "上交所主板（建议）",
    "equity_story": (
        "公司聚焦园区级IDC投资、建设与运营，受益于AI算力需求增长与高功率机柜升级趋势，"
        "并在液冷与跨区域节点布局方面形成差异化能力。"
    ),
    "risks": [
        "客户集中度较高，第一大客户收入占比较高",
        "重资产投入导致折旧及资本开支压力较大",
        "电力资源与能耗指标约束可能影响扩张节奏",
        "液冷技术与PUE目标落地不及预期",
        "股东股权质押比例较高，需关注流动性与治理风险",
    ],
    "financials": [
        {"year": 2023, "revenue": 315000, "net_profit": 87000, "ebitda": 102000},
        {"year": 2024, "revenue": 472000, "net_profit": 142000, "ebitda": 167000},
        {"year": 2025, "revenue": 708000, "net_profit": 239000, "ebitda": 281000},
    ],
    "peer_multiples": [
        {"name": "B公司（数据型IDC）", "pe": 30, "ps": 10.5},
        {"name": "C公司（零售型IDC）", "pe": 25, "ps": 8.0},
        {"name": "D公司（IDC+云计算）", "pe": 27, "ps": 15.0},
        {"name": "E公司（第三方IDC）", "pe": 23, "ps": 5.5},
    ],
    "proceeds_usage": ["智算中心扩建", "液冷技术研发与改造", "偿还部分银行借款"],
    "candidate_highlights": "本人在投行股权承做实习中参与招股书底稿、可比公司估值、数据交叉核验，并搭建AI工具提升初稿效率。",
    "industry_overview": "数据中心作为数字经济基础设施，受AI训练与推理需求驱动，行业正向高功率、液冷、低PUE方向升级。",
    "listing_plan": "建议主板申报路径，先完成财务与内控规范，再推进申报与反馈，发行阶段重点强调长期订单与区域布局稳定性。",
    "key_issues_and_solutions": "客户集中：拓展腰部客户并优化收入结构；负债压力：优化债务期限并匹配募资用途；能耗约束：优先布局电力指标明确区域。",
}


def _save_outputs(report: str) -> tuple[Path, Path]:
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    md_path = out_dir / "ipo_report.md"
    pdf_path = out_dir / "ipo_report.pdf"
    md_path.write_text(report, encoding="utf-8")
    pdf_path.write_bytes(markdown_to_pdf_bytes(report))
    return md_path, pdf_path


def _build_payload_from_form() -> dict:
    financials_df = st.session_state.form_financials_df
    peers_df = st.session_state.form_peers_df

    financials = []
    for _, row in financials_df.iterrows():
        year = int(row.get("year", 0))
        if year <= 0:
            continue
        financials.append(
            {
                "year": year,
                "revenue": float(row.get("revenue", 0) or 0),
                "net_profit": float(row.get("net_profit", 0) or 0),
                "ebitda": float(row.get("ebitda", 0) or 0),
            }
        )

    peer_multiples = []
    for _, row in peers_df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        peer_multiples.append(
            {
                "name": name,
                "pe": float(row.get("pe", 0) or 0),
                "ps": float(row.get("ps", 0) or 0),
            }
        )

    risks = [x.strip() for x in st.session_state.form_risks.split("\n") if x.strip()]
    proceeds_usage = [
        x.strip() for x in st.session_state.form_proceeds_usage.split("\n") if x.strip()
    ]

    return {
        "company_name": st.session_state.form_company_name.strip(),
        "sector": st.session_state.form_sector.strip(),
        "listing_market": st.session_state.form_listing_market.strip(),
        "equity_story": st.session_state.form_equity_story.strip(),
        "industry_overview": st.session_state.form_industry_overview.strip(),
        "listing_plan": st.session_state.form_listing_plan.strip(),
        "key_issues_and_solutions": st.session_state.form_key_issues_and_solutions.strip(),
        "risks": risks,
        "financials": financials,
        "peer_multiples": peer_multiples,
        "proceeds_usage": proceeds_usage,
        "report_standard": st.session_state.form_report_standard,
        "candidate_highlights": st.session_state.get("form_candidate_highlights", "").strip(),
    }


def _load_payload_to_form(payload: dict) -> None:
    st.session_state.form_company_name = payload.get("company_name", "")
    st.session_state.form_sector = payload.get("sector", "")
    st.session_state.form_listing_market = payload.get("listing_market", "")
    st.session_state.form_equity_story = payload.get("equity_story", "")
    st.session_state.form_risks = "\n".join(payload.get("risks", []))
    st.session_state.form_proceeds_usage = "\n".join(payload.get("proceeds_usage", []))
    st.session_state.form_candidate_highlights = payload.get("candidate_highlights", "")
    st.session_state.form_industry_overview = payload.get("industry_overview", "")
    st.session_state.form_listing_plan = payload.get("listing_plan", "")
    st.session_state.form_key_issues_and_solutions = payload.get(
        "key_issues_and_solutions", ""
    )
    st.session_state.form_report_standard = payload.get("report_standard", "终稿")
    st.session_state.form_financials_df = pd.DataFrame(payload.get("financials", []))
    st.session_state.form_peers_df = pd.DataFrame(payload.get("peer_multiples", []))


st.info("使用步骤：1) 点击“加载华泰题目样例” 2) 微调信息 3) 点击“生成建议书” 4) 下载PDF")

col_left, col_right = st.columns([1, 1])

if "input_mode" not in st.session_state:
    st.session_state.input_mode = "表单输入（推荐）"
if "form_company_name" not in st.session_state:
    _load_payload_to_form(HUATAI_SAMPLE_PAYLOAD)

with col_left:
    st.subheader("输入区")
    st.radio(
        "输入方式",
        options=["表单输入（推荐）", "JSON输入（高级）"],
        key="input_mode",
        horizontal=True,
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("加载华泰题目样例", width="stretch"):
            _load_payload_to_form(HUATAI_SAMPLE_PAYLOAD)
            st.success("已加载华泰题目样例数据。")
    with btn_col2:
        if st.button("加载基础演示样例", width="stretch"):
            _load_payload_to_form(DEFAULT_PAYLOAD)
            st.success("已加载基础演示样例。")

    payload_text = ""
    if st.session_state.input_mode == "表单输入（推荐）":
        st.text_input("公司名称", key="form_company_name")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("行业", key="form_sector")
        with c2:
            st.text_input("拟上市地", key="form_listing_market")
        st.selectbox("报告标准", options=["终稿", "初稿"], key="form_report_standard")
        st.text_area("公司亮点", key="form_equity_story", height=90)
        st.text_area("行业分析", key="form_industry_overview", height=90)
        st.text_area("上市方案设计", key="form_listing_plan", height=90)
        st.text_area("主要风险（每行一条）", key="form_risks", height=120)
        st.text_area("重点关注事项对应解决思路", key="form_key_issues_and_solutions", height=100)
        st.text_area("募资用途（每行一条）", key="form_proceeds_usage", height=100)

        st.markdown("**财务数据（单位可在演示时口头说明：例如万元）**")
        edited_financials_df = st.data_editor(
            st.session_state.form_financials_df,
            num_rows="dynamic",
            width="stretch",
            key="financials_editor",
        )
        st.session_state.form_financials_df = edited_financials_df

        st.markdown("**可比公司估值（至少2家）**")
        edited_peers_df = st.data_editor(
            st.session_state.form_peers_df,
            num_rows="dynamic",
            width="stretch",
            key="peers_editor",
        )
        st.session_state.form_peers_df = edited_peers_df

        payload = _build_payload_from_form()
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        payload_text = st.text_area(
            "请粘贴公司信息JSON",
            value=json.dumps(HUATAI_SAMPLE_PAYLOAD, ensure_ascii=False, indent=2),
            height=520,
        )

    with st.expander("高级：当前JSON（可复制）", expanded=False):
        st.code(payload_text, language="json")

    use_llm = st.checkbox("使用大模型润色（可选）", value=True)
    clicked = st.button("生成项目建议书", type="primary")

with col_right:
    st.subheader("输出区")
    output_slot = st.empty()

if "latest_report" not in st.session_state:
    st.session_state.latest_report = ""

if clicked:
    try:
        with st.spinner("正在生成中（首次可能需要10-45秒）..."):
            report, mode, quality = generate_ipo_report(payload_text, model=None if use_llm else "")
        st.session_state.latest_report = report
        output_slot.markdown(report)
        md_path, pdf_path = _save_outputs(report)
        if mode == "llm":
            st.success("已使用大模型终稿模式生成。")
        elif mode == "fallback_quality":
            st.warning("大模型结果未达到终稿质量门槛，已自动切换为结构化终稿模板。")
        elif mode == "fallback_error":
            st.warning("大模型调用失败，已自动切换为结构化终稿模板。")
        else:
            st.info("当前为本地模板生成（未启用大模型）。")

        st.markdown("### 终稿质量评分")
        st.metric("质量分", quality["score"])
        st.caption(f"报告长度：{quality['length']}（终稿建议不低于 {quality['min_length_required']}）")
        if quality["missing_sections"]:
            st.warning(f"缺少章节：{', '.join(quality['missing_sections'])}")
        if quality["missing_keywords"]:
            st.warning(f"缺少关键项：{', '.join(quality['missing_keywords'])}")
        if quality["pass"]:
            st.success("已通过终稿结构与完整性校验。")
        st.success(f"报告已保存：`{md_path}` 和 `{pdf_path}`")
    except Exception as exc:
        st.error(f"生成失败：{exc}")

if st.session_state.latest_report:
    st.divider()
    st.subheader("下载区")
    report_text = st.session_state.latest_report
    st.download_button(
        "下载Markdown",
        data=report_text.encode("utf-8"),
        file_name="ipo_report.md",
        mime="text/markdown",
    )
    st.download_button(
        "下载PDF（建议发老师）",
        data=markdown_to_pdf_bytes(report_text),
        file_name="ipo_report.pdf",
        mime="application/pdf",
    )
