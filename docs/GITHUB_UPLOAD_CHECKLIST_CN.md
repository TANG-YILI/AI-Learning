# GitHub 上传前检查清单

## 必须上传

- `app.py`
- `src/`
- `docs/`
- `.streamlit/`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `LICENSE`

## 绝对不要上传

- `.env`（里面有 API Key）
- `.venv/`
- `outputs/`
- `__pycache__/`
- `Untitled`

以上内容已写入 `.gitignore`，正常执行 `git add .` 不会上传。

## 上传命令

在 PowerShell 执行：

```powershell
cd E:\project1\minimal-agent-main
git init
git branch -M main
git add .
git status
git commit -m "feat: build IPO final-report agent"
git remote add origin https://github.com/你的用户名/ipo-deal-agent.git
git push -u origin main
```

如果提示 `origin already exists`，改用：

```powershell
git remote set-url origin https://github.com/你的用户名/ipo-deal-agent.git
git push -u origin main
```

## 发老师前需要准备

1. 生成并下载 `ipo_report.pdf`；
2. 打开 `docs/FINAL_EMAIL_TO_SEND_CN.txt`，填入 GitHub 链接；
3. 邮件附件放 `ipo_report.pdf`；
4. 正文复制 `docs/FINAL_EMAIL_TO_SEND_CN.txt`。
