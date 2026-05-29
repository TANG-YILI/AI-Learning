import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

from litellm import completion


@dataclass
class IPOInputs:
    company_name: str
    sector: str
    listing_market: str
    equity_story: str
    risks: list[str]
    financials: list[dict[str, Any]]
    peer_multiples: list[dict[str, Any]]
    proceeds_usage: list[str]
    industry_overview: str = ""
    listing_plan: str = ""
    key_issues_and_solutions: str = ""
    candidate_highlights: str = ""
    report_standard: str = "终稿"


def parse_inputs(raw_text: str) -> IPOInputs:
    payload = json.loads(raw_text)
    required = [
        "company_name",
        "sector",
        "listing_market",
        "equity_story",
        "risks",
        "financials",
        "peer_multiples",
        "proceeds_usage",
    ]
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"缺少字段: {', '.join(missing)}")

    return IPOInputs(
        company_name=payload["company_name"],
        sector=payload["sector"],
        listing_market=payload["listing_market"],
        equity_story=payload["equity_story"],
        risks=payload["risks"],
        financials=payload["financials"],
        peer_multiples=payload["peer_multiples"],
        proceeds_usage=payload["proceeds_usage"],
        industry_overview=payload.get("industry_overview", ""),
        listing_plan=payload.get("listing_plan", ""),
        key_issues_and_solutions=payload.get("key_issues_and_solutions", ""),
        candidate_highlights=payload.get("candidate_highlights", ""),
        report_standard=payload.get("report_standard", "终稿"),
    )


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_financial_summary(financials: list[dict[str, Any]]) -> dict[str, Any]:
    if len(financials) < 2:
        raise ValueError("financials 至少需要 2 年数据")

    financials_sorted = sorted(financials, key=lambda x: str(x.get("year", "")))
    first = financials_sorted[0]
    last = financials_sorted[-1]

    rev_first = _safe_float(first.get("revenue"))
    rev_last = _safe_float(last.get("revenue"))
    net_last = _safe_float(last.get("net_profit"))
    ebitda_last = _safe_float(last.get("ebitda"))
    years = max(len(financials_sorted) - 1, 1)

    cagr = ((rev_last / rev_first) ** (1 / years) - 1) if rev_first > 0 else 0.0
    net_margin = (net_last / rev_last) if rev_last > 0 else 0.0
    ebitda_margin = (ebitda_last / rev_last) if rev_last > 0 else 0.0

    return {
        "latest_year": str(last.get("year", "")),
        "latest_revenue": rev_last,
        "latest_net_profit": net_last,
        "latest_ebitda": ebitda_last,
        "revenue_cagr": cagr,
        "net_margin": net_margin,
        "ebitda_margin": ebitda_margin,
    }


def estimate_valuation(
    latest_net_profit: float, latest_revenue: float, peer_multiples: list[dict[str, Any]]
) -> dict[str, float]:
    if not peer_multiples:
        return {"pe_mid": 0.0, "ps_mid": 0.0, "equity_value_mid": 0.0}

    pe_values = [_safe_float(x.get("pe")) for x in peer_multiples if x.get("pe") is not None]
    ps_values = [_safe_float(x.get("ps")) for x in peer_multiples if x.get("ps") is not None]

    pe_mid = sum(pe_values) / len(pe_values) if pe_values else 0.0
    ps_mid = sum(ps_values) / len(ps_values) if ps_values else 0.0

    val_by_pe = latest_net_profit * pe_mid if latest_net_profit > 0 and pe_mid > 0 else 0.0
    val_by_ps = latest_revenue * ps_mid if latest_revenue > 0 and ps_mid > 0 else 0.0

    candidates = [v for v in [val_by_pe, val_by_ps] if v > 0]
    equity_value_mid = sum(candidates) / len(candidates) if candidates else 0.0
    return {
        "pe_mid": pe_mid,
        "ps_mid": ps_mid,
        "val_by_pe": val_by_pe,
        "val_by_ps": val_by_ps,
        "equity_value_mid": equity_value_mid,
    }


def _build_fact_sheet(inputs: IPOInputs, metrics: dict[str, Any], valuation: dict[str, float]) -> str:
    valuation_candidates = [v for v in [valuation["val_by_pe"], valuation["val_by_ps"]] if v > 0]
    if valuation_candidates:
        low = min(valuation_candidates) * 0.9
        high = max(valuation_candidates) * 1.1
    else:
        low = high = 0.0

    return (
        f"- 公司：{inputs.company_name}\n"
        f"- 行业：{inputs.sector}\n"
        f"- 拟上市地：{inputs.listing_market}\n"
        f"- 最新年度：{metrics['latest_year']}\n"
        f"- 最新收入：{metrics['latest_revenue']:.2f}\n"
        f"- 最新净利润：{metrics['latest_net_profit']:.2f}\n"
        f"- 最新EBITDA：{metrics['latest_ebitda']:.2f}\n"
        f"- 收入CAGR：{metrics['revenue_cagr'] * 100:.2f}%\n"
        f"- 净利率：{metrics['net_margin'] * 100:.2f}%\n"
        f"- EBITDA Margin：{metrics['ebitda_margin'] * 100:.2f}%\n"
        f"- 可比平均PE：{valuation['pe_mid']:.2f}x（PE法估值：{valuation['val_by_pe']:.2f}）\n"
        f"- 可比平均PS：{valuation['ps_mid']:.2f}x（PS法估值：{valuation['val_by_ps']:.2f}）\n"
        f"- 估值区间建议：{low:.2f} - {high:.2f}\n"
        f"- 估值中枢：{valuation['equity_value_mid']:.2f}\n"
    )


def _quality_check(report: str, standard: str) -> dict[str, Any]:
    required_sections = [
        "一、公司亮点",
        "二、行业分析",
        "三、估值参考",
        "四、上市方案设计",
        "五、重点关注事项",
        "六、执行路径与时间安排",
        "七、终稿复核清单",
    ]
    must_have_keywords = ["PE法", "PS法", "估值区间", "风险", "解决思路"]
    min_len = 1800 if standard == "终稿" else 1000

    missing_sections = [s for s in required_sections if s not in report]
    missing_keywords = [k for k in must_have_keywords if k not in report]
    length_ok = len(report) >= min_len
    score = 100
    score -= len(missing_sections) * 10
    score -= len(missing_keywords) * 8
    if not length_ok:
        score -= 20
    score = max(score, 0)

    return {
        "score": score,
        "length": len(report),
        "min_length_required": min_len,
        "missing_sections": missing_sections,
        "missing_keywords": missing_keywords,
        "length_ok": length_ok,
        "pass": score >= 75 and length_ok and not missing_sections,
    }


def _deterministic_report(inputs: IPOInputs, metrics: dict[str, Any], valuation: dict[str, float]) -> str:
    proceeds = "\n".join([f"- {x}" for x in inputs.proceeds_usage]) or "- 智算中心扩建\n- 液冷技术改造\n- 补充流动资金"
    risks = "\n".join([f"- {x}" for x in inputs.risks]) or "- 客户集中风险\n- 能耗与指标约束风险"

    valuation_candidates = [v for v in [valuation["val_by_pe"], valuation["val_by_ps"]] if v > 0]
    if valuation_candidates:
        low = min(valuation_candidates) * 0.9
        high = max(valuation_candidates) * 1.1
    else:
        low = high = 0.0

    industry_text = inputs.industry_overview or (
        f"{inputs.sector}受AI算力与数字化升级驱动，行业需求延续增长，但能耗约束、资本开支与客户结构对盈利质量形成分化。"
    )
    listing_plan_text = inputs.listing_plan or (
        f"建议以{inputs.listing_market}为主要申报路径，采取“规范整改-申报反馈-询价路演”三阶段推进，"
        "在发行前重点强化持续经营能力与风险披露的一致性。"
    )
    issue_solution_text = inputs.key_issues_and_solutions or (
        "1) 客户集中：通过新增行业客户与区域拓展优化收入结构；\n"
        "2) 负债与资本开支压力：明确募资用途并优化债务期限结构；\n"
        "3) 能耗指标与电力保障：提前锁定重点基地电力资源与节能改造方案。"
    )

    return f"""# {inputs.company_name} IPO 项目建议书（{inputs.report_standard}）

> 生成日期：{date.today().isoformat()} ｜ 行业：{inputs.sector} ｜ 拟上市地：{inputs.listing_market}

## 一、公司亮点
- 围绕核心能力形成差异化竞争：{inputs.equity_story}
- 最新年度经营表现：
  - 营业收入：{metrics['latest_revenue']:.2f}
  - 归母净利润：{metrics['latest_net_profit']:.2f}
  - EBITDA：{metrics['latest_ebitda']:.2f}
  - 收入CAGR：{metrics['revenue_cagr'] * 100:.2f}%

## 二、行业分析
{industry_text}

## 三、估值参考（至少两种方法）
- 方法1（PE法）：可比平均PE为 {valuation['pe_mid']:.2f}x，对应估值约 {valuation['val_by_pe']:.2f}
- 方法2（PS法）：可比平均PS为 {valuation['ps_mid']:.2f}x，对应估值约 {valuation['val_by_ps']:.2f}
- 估值区间建议：{low:.2f} - {high:.2f}
- 估值中枢（两法均值）：{valuation['equity_value_mid']:.2f}

## 四、上市方案设计
{listing_plan_text}

建议募资用途：
{proceeds}

## 五、重点关注事项（含解决思路）
主要风险：
{risks}

对应解决思路：
{issue_solution_text}

## 六、执行路径与时间安排（终稿化补充）
1) T-6至T-4月：完成财务规范、内控整改、法律税务尽调和问题清单闭环  
2) T-4至T-2月：申报材料定稿、问询问题演练、核心风险表述统一  
3) T-2至T-1月：投资者沟通、询价区间预设、发行条件压力测试  
4) T月：发行与挂牌执行，并开展上市后市值管理与信息披露准备

## 七、终稿复核清单（供投行团队内部使用）
- 口径一致性：财务数据、业务描述、估值口径在全文保持一致  
- 风险充分性：已覆盖客户集中、资本开支、能耗指标、技术迭代等关键风险  
- 估值可解释性：PE/PS两法参数、可比样本、区间形成逻辑可复核  
- 合规边界：无收益承诺、无上市结果承诺、措辞符合审慎披露要求

---
备注：本建议书为自动生成稿，仅用于内部讨论与承做准备，不构成投资建议或上市结果承诺。
"""


def _llm_report(
    inputs: IPOInputs, metrics: dict[str, Any], valuation: dict[str, float], model: str
) -> str:
    facts = _build_fact_sheet(inputs, metrics, valuation)
    prompt_draft = f"""
你是华泰证券投行股权承做的资深保荐代表人。请根据以下结构化信息，输出中文IPO项目建议书（Markdown），目标是“可直接用于内部评审会的终稿风格”，严格按以下7个一级标题输出：
1) 一、公司亮点
2) 二、行业分析
3) 三、估值参考（至少两种方法，给出估值区间）
4) 四、上市方案设计
5) 五、重点关注事项（含解决思路）
6) 六、执行路径与时间安排
7) 七、终稿复核清单

要求：
- 用投行语境，专业、严谨、可执行，避免泛泛而谈；
- 必须体现两种估值方法（PE与PS）及估值区间；
- 风险表述审慎，不承诺上市成功；
- 不输出多余花哨格式，不要英文界面化表达；
- 每个一级标题下至少给出3条以上要点；
- 文本总长度建议在1800字以上，避免“初稿感”。
- 数字必须优先引用事实表，不要编造额外财务数据。

[公司输入]
{json.dumps(inputs.__dict__, ensure_ascii=False, indent=2)}

[测算摘要]
{json.dumps(metrics, ensure_ascii=False, indent=2)}

[估值摘要]
{json.dumps(valuation, ensure_ascii=False, indent=2)}

[事实表（必须优先引用）]
{facts}
"""

    draft_response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt_draft}],
        stream=False,
        timeout=45,
    )
    draft = draft_response.choices[0].message.content or ""

    prompt_polish = f"""
你现在是投行质控总审校。请对以下“IPO建议书草稿”进行终稿化重写，要求：
1) 保留原有7个一级标题，不可新增或删除；
2) 补强逻辑链：结论 -> 依据 -> 执行动作；
3) 每章不少于3条实质要点，避免空话；
4) 三、估值参考必须同时写PE法、PS法与估值区间；
5) 五、重点关注事项必须“风险+解决思路”一一对应；
6) 全文专业、克制、可执行，不承诺上市成功；
7) 输出Markdown正文，不要解释过程。

[事实表]
{facts}

[草稿]
{draft}
"""
    final_response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt_polish}],
        stream=False,
        timeout=45,
    )
    return final_response.choices[0].message.content or draft


def generate_ipo_report(raw_json: str, model: str | None = None) -> tuple[str, str, dict[str, Any]]:
    inputs = parse_inputs(raw_json)
    metrics = build_financial_summary(inputs.financials)
    valuation = estimate_valuation(
        latest_net_profit=metrics["latest_net_profit"],
        latest_revenue=metrics["latest_revenue"],
        peer_multiples=inputs.peer_multiples,
    )

    selected_model = model or os.environ.get("MODEL")
    if selected_model:
        try:
            llm_report = _llm_report(inputs, metrics, valuation, selected_model)
            quality = _quality_check(llm_report, inputs.report_standard)
            if quality["pass"]:
                return llm_report, "llm", quality
            # 质量不足时，自动退回到确定性模板确保结构完备
            fallback_report = _deterministic_report(inputs, metrics, valuation)
            fallback_quality = _quality_check(fallback_report, inputs.report_standard)
            return fallback_report, "fallback_quality", fallback_quality
        except Exception:
            # Fallback to deterministic report to guarantee demo can run.
            fallback_report = _deterministic_report(inputs, metrics, valuation)
            fallback_quality = _quality_check(fallback_report, inputs.report_standard)
            return fallback_report, "fallback_error", fallback_quality

    deterministic_report = _deterministic_report(inputs, metrics, valuation)
    deterministic_quality = _quality_check(deterministic_report, inputs.report_standard)
    return deterministic_report, "deterministic", deterministic_quality
