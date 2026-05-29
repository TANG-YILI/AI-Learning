# IPO Deal Agent Demo

面向投行股权承做场景的可运行 AI Agent 作品集项目。  
输入公司结构化信息（业务、财务、可比估值、风险），自动输出 IPO 项目建议书，并支持网页演示与 PDF 导出。

## 为什么这个项目适合面试展示

- 不是“单纯文案生成”，而是完整承做工作流建模
- 有可复核的财务与估值逻辑（CAGR、利润率、可比倍数中枢）
- 有风控边界（审慎表述、不承诺上市成功）
- 有可视化交付（Web 页面对外展示）

## 核心能力

- **IPO 场景输出**：项目概览、投资逻辑、财务诊断、估值建议、风险披露、执行时间表
- **双模式生成**：
  - `LLM 模式`（配置模型后）：文本更专业
  - `Deterministic 模式`（无 key 也能跑）：演示保底
- **导出能力**：自动输出 Markdown + PDF（可直接邮件附件）
- **候选人展示卡片**：网页内展示你的实习方向、AI定位、交付价值

## 项目结构

- `app.py`：Streamlit 网页入口
- `src/minimal_agent/ipo_workflow.py`：IPO 核心工作流
- `src/minimal_agent/exporters.py`：Markdown -> PDF 导出
- `run_agent.py`：命令行演示
- `docs/EMAIL_TEMPLATE_CN.md`：可直接发送的补充邮件模板
- `docs/EMAIL_READY_TO_SEND_CN.txt`：已填个人信息的即发邮件
- `docs/INTERVIEW_TALK_TRACK_CN.md`：3 分钟面试讲解稿
- `docs/GITHUB_PROFILE_README_CN.md`：GitHub 项目展示文案
- `docs/FOLLOWUP_48H_EMAIL_CN.txt`：48 小时跟进邮件模板
- `docs/WECHAT_HR_30S_SCRIPT_CN.txt`：微信联系 HR 30 秒话术
- `docs/老师使用说明_3分钟上手.md`：金融老师可直接使用的说明
- `docs/专业版参考项目清单.md`：终稿级系统的开源参考路径
- `docs/FINAL_EMAIL_TO_SEND_CN.txt`：最终可发送邮件正文
- `docs/GITHUB_UPLOAD_CHECKLIST_CN.md`：GitHub 上传与发件检查清单

## 快速开始

### 1) 安装依赖

```bash
uv sync
```

### 2) （可选）配置 LLM

在 `.env` 中添加：
```bash
MODEL="gemini/gemini-2.0-flash"
GEMINI_API_KEY=<YOUR-API-KEY>
```

不配置也可运行（自动 fallback 到 deterministic 模式）。

### 3) 启动 Web 演示

```bash
uv run streamlit run app.py
```

打开页面后点击“生成IPO建议书”，可下载：
- `ipo_report.md`
- `ipo_report.pdf`

### 4) 命令行演示

```bash
uv run run_agent.py
```

## GitHub 展示建议

发布仓库时建议附上：

1. 首页截图（输入区 + 报告区）  
2. 1 分钟操作录屏 GIF  
3. 样例输出（可放 `examples/sample_ipo_report.md`）  
4. 你的补充邮件链接和演示说明

## 合规说明

本项目仅用于学习与面试展示，不构成投资建议，也不构成对上市结果的任何保证。
