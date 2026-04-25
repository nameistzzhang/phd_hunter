# PhD Hunter 🎓

**PhD 导师套磁筛选助手** - 自动化收集 CS 教授信息，智能分析匹配度，辅助生成套磁信

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-v0.1-green.svg)

## ✨ 功能概览

### 数据采集
- 📊 **CSRankings 爬取** - 自动获取各大学 CS 领域教授排名和名单
- 📝 **arXiv 论文获取** - 按作者搜索并保存最新论文元数据
- 🏠 **个人主页抓取** - 抓取教授主页内容并 AI 摘要分析
- 💾 **SQLite 存储** - 所有数据本地持久化

### AI 分析
- 🤖 **教授匹配度打分** - 基于 LLM 对教授方向匹配度和录取难度评分（1-5分）
- 💬 **智能对话分析** - 一键生成教授分析报告 + 套磁信草稿
- 🎯 **个性化套磁信** - 基于你的 Profile（CV/PS/论文）生成定制化 cold email

### Web 前端
- 🌐 **现代化界面** - 基于 Flask 的 SPA 交互式界面
- 🏷️ **优先级管理** - 冲刺/匹配/稳妥/保底/不考虑 五级标记
- 🔍 **多维筛选** - 按优先级、研究领域、大学、分数筛选
- 👤 **Profile 管理** - 上传 CV/PS、管理 arXiv 论文、设置研究偏好
- ⚙️ **LLM 配置** - 可配置 API Key、模型、温度、迭代次数等参数

## 🚀 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- Chrome/Chromium 浏览器（用于 Selenium 爬取主页）

### 安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd phd-hunter

# 2. 安装依赖
uv sync

# 或使用 pip
pip install -e .
```

### 配置

```bash
# 1. 配置 LLM 参数
cp src/phd_hunter/frontend/hound_config.example.json src/phd_hunter/frontend/hound_config.json
# 编辑 hound_config.json 填入你的 API Key 和模型信息

# 2. 配置采集参数（可选）
cp src/phd_hunter/frontend/hunt_config.example.json src/phd_hunter/frontend/hunt_config.json
```

### 数据采集（CLI 模式）

```bash
# 1. 爬取教授数据
python main.py crawl --area ai --region world --max-professors 5

# 2. 获取论文
python main.py fetch-papers --max-papers 10

# 3. 抓取教授主页（需要配置 LLM）
python -m phd_hunter.crawlers.homepage_crawler

# 4. 运行匹配度打分（需要配置 LLM）
python -m phd_hunter.hound.scorer

# 5. 查看统计
python main.py stats
```

### 启动 Web 界面

```bash
# 启动 Flask Web 服务器（默认 http://localhost:8080）
PYTHONPATH=src python -m phd_hunter.frontend.app
```

然后在浏览器中打开 http://localhost:8080，即可：

- **Hunt 页面**：浏览教授卡片，筛选、排序、标记优先级
- **Chat 页面**：点击教授进入对话，AI 自动生成分析报告和套磁信草稿
- **Profile 页面**：上传 CV/PS、添加 arXiv 论文、设置研究偏好

## 📁 项目结构

```
phd_hunter/
├── main.py                       # CLI 入口
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
├── docs/                         # Sphinx 文档
├── tests/                        # 测试文件
└── src/phd_hunter/
    ├── __init__.py               # 包初始化
    ├── models.py                 # Pydantic 数据模型
    ├── database.py               # SQLite 数据库操作
    ├── api_infra/                # LLM API 基础设施
    │   ├── __init__.py
    │   └── core/
    │       └── client.py         # 统一 LLM 客户端
    ├── crawlers/
    │   ├── __init__.py           # 导出 ArxivCrawler, CSRankingsCrawler
    │   ├── base.py               # 爬虫基类 (缓存支持)
    │   ├── csrankings.py         # CSRankings 爬虫 (Selenium)
    │   ├── arxiv_crawler.py      # arXiv 爬虫
    │   └── homepage_crawler.py   # 教授主页抓取 + AI 摘要
    ├── hound/
    │   ├── __init__.py
    │   └── scorer.py             # 教授匹配度打分器
    ├── analyzer/
    │   ├── __init__.py           # 导出 analyze_professor, chat_with_professor
    │   ├── analyzer.py           # 教授分析 + 套磁信生成核心
    │   └── prompts.py            # Analyzer prompt 模板
    ├── utils/
    │   ├── logger.py             # 日志配置
    │   ├── helpers.py            # 工具函数
    │   └── pdf_extract.py        # PDF 文本提取 + Profile 构建
    └── frontend/                 # Web 前端界面
        ├── app.py                # Flask API 服务器
        ├── index.html            # 主页面
        ├── hound_config.json     # LLM 配置（需手动创建）
        ├── hunt_config.json      # 采集配置
        ├── static/
        │   ├── styles.css        # 样式表
        │   ├── app.js            # 前端逻辑
        │   └── windsurf.svg      # AI 头像图标
        └── templates/            # HTML 模板
```

## 🗄️ 数据库结构

项目使用 SQLite 存储数据，核心表：

### professors 表
- 基本信息：姓名、大学、排名、院系、邮箱、主页
- 研究方向、优先级（-1~3）
- AI 分析：homepage_summary, direction_match_score, admission_difficulty_score
- 对话历史：messages (JSON)

### papers 表
- 论文元数据（标题、作者、摘要、年份、venue）
- arXiv ID、PDF 链接、引用数
- 关联到教授记录

### applicant_profile 表
- 用户 Profile：CV 文本、PS 文本
- 研究偏好、arXiv 论文列表

## 🔧 核心模块

### Analyzer - 教授分析与套磁信

基于你的 Profile 和教授信息，自动生成：
1. 教授研究方向分析
2. 你与教授的匹配点分析
3. 套磁信撰写指南
4. 完整的套磁信草稿

支持多轮对话，可以基于初稿继续追问修改。

### Scorer - 匹配度打分

使用 LLM 对每位教授评分：
- **Direction Match** (1-5): 研究方向匹配度
- **Admission Difficulty** (1-5): 录取难度评估

### Homepage Crawler - 主页抓取

使用 Selenium 抓取教授个人主页，通过 LLM 摘要提取：
- 研究重点
- 招生状态
- 主页内容摘要

## 🌐 Web 界面使用指南

### 1. 配置 LLM

点击右上角 ⚙️ 设置图标，配置：
- API Key
- Provider / Model
- URL（自定义 API 地址）
- Temperature / Max Tokens
- Scoring Iterations

### 2. 完善 Profile

进入 Profile 页面：
- 上传 CV 和 PS（PDF 格式）
- 添加感兴趣的 arXiv 论文链接
- 设置研究偏好

### 3. 浏览教授

Hunt 页面显示所有教授卡片：
- 顶栏显示统计：大学数、教授数、论文数、平均分
- 使用筛选栏按优先级 / 领域 / 大学 / 分数筛选
- 点击教授卡片查看详细信息（论文可跳转 arXiv）

### 4. AI 对话分析

点击 Chat 进入对话：
- 首次进入自动分析教授并生成套磁信草稿
- 可以继续对话修改、追问细节
- 每条消息可单独删除

## 📊 命令行详解

### `crawl` - 爬取教授信息

```bash
python main.py crawl --area ai --region world --max-professors 5
```

**参数：**
- `--area`：研究领域（默认：`ai`）
- `--region`：地区过滤（默认：`world`）
- `--max-universities`：最大大学数量（默认：全部）
- `--max-professors`：每所大学最大教授数（默认：5）
- `--no-headless`：显示浏览器窗口
- `--timeout`：页面超时（秒，默认：30）

### `fetch-papers` - 获取论文

```bash
python main.py fetch-papers --max-papers 10 --max-professors 50
```

**参数：**
- `--max-papers`：每位教授最大论文数（默认：10）
- `--max-professors`：最大处理教授数（默认：全部）
- `--delay`：请求间隔（秒，默认：1.0）

### `stats` - 统计信息

```bash
python main.py stats
```

## ⚠️ 已知限制

1. **arXiv 覆盖度**：并非所有教授都在 arXiv 发表论文
2. **作者歧义**：arXiv 作者搜索可能包含重名结果
3. **LLM 成本**：Analyzer 和 Scorer 需要调用 LLM API，注意费用控制
4. **主页抓取**：部分教授主页有反爬机制，可能抓取失败

## 📖 文档

完整文档见 `docs/` 目录或本地浏览：
- [安装指南](docs/source/installation.rst)
- [系统架构](docs/source/architecture.rst)
- [爬虫模块](docs/source/crawlers.rst)
- [API 参考](docs/source/api.rst)
- [更新日志](docs/source/changelog.rst)

构建文档：
```bash
cd docs && make html
```

## 🧪 开发

### 运行测试

```bash
uv run pytest tests/ -v
```

### 代码检查

```bash
uv run black --check src/
uv run ruff check src/
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [CSRankings](http://csrankings.org/) - 教授数据来源
- [arXiv](https://arxiv.org/) - 论文数据来源
- [Semantic Scholar](https://www.semanticscholar.org/) - 论文补充数据

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
