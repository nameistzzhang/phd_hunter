# PhD Hunter 🎓

**PhD 导师套磁筛选助手** - 一个智能化的 PhD 导师匹配与分析系统

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-alpha-yellow.svg)

## ✨ 功能特色

- 📊 **智能匹配** - 基于 LLM 分析论文和研究方向，计算与你的匹配分数
- 🔍 **数据整合** - 自动爬取 CSRankings、Google Scholar、arXiv 数据
- 📝 **自动报告** - 生成详细的套磁建议、风险评估和申请策略
- 🌐 **Web 界面** - 基于 Streamlit 的友好交互界面
- ⚡ **高效可靠** - 异步处理、缓存机制、重试逻辑

## 🚀 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- Chrome/Chromium 浏览器 (用于 Selenium)

### 安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd phd-hunter

# 2. 安装依赖
uv sync

# 3. 复制配置文件
copy config\settings.example.yaml config\settings.yaml

# 4. 编辑配置文件，填入你的 API Keys
# config/settings.yaml
```

### 运行

```bash
# 启动前端界面
uv run streamlit run src/phd_hunter/frontend/app.py

# 或启动 API 服务
uv run python src/phd_hunter/api.py
```

访问 http://localhost:8501 开始使用！

## 📁 项目结构

```
phd_hunter/
├── src/phd_hunter/       # 主代码包
│   ├── crawlers/         # 爬虫模块
│   │   ├── csrankings.py # CSRankings 爬取
│   │   ├── scholar.py    # Google Scholar (待实现)
│   │   ├── professor.py  # 导师主页解析 (待实现)
│   │   └── arxiv.py      # arXiv 下载 (待实现)
│   ├── agents/           # Agent 模块 (待实现)
│   │   ├── coordinator.py
│   │   ├── researcher.py
│   │   └── reporter.py
│   ├── llm/              # LLM 接口
│   │   ├── client.py     # LLM 客户端
│   │   └── prompts.py    # Prompt 模板
│   ├── reports/          # 报告生成 (待实现)
│   ├── utils/            # 工具模块
│   │   ├── config.py     # 配置管理
│   │   ├── logger.py     # 日志
│   │   └── helpers.py    # 辅助函数
│   ├── frontend/         # Streamlit 前端
│   │   └── app.py
│   ├── api.py            # FastAPI 后端
│   ├── models.py         # 数据模型
│   └── main.py           # 主程序入口
├── config/               # 配置文件
├── docs/                 # Sphinx 文档
├── tests/                # 测试文件
├── pyproject.toml        # 项目配置
└── README.md
```

## 🔧 配置

编辑 `config/settings.yaml`:

```yaml
llm:
  provider: "openai"        # "openai" 或 "anthropic"
  api_key: "your-api-key"
  model: "gpt-4o"

crawlers:
  selenium:
    headless: true
    timeout: 30

output:
  reports_dir: "./reports"
  papers_dir: "./papers"
```

或设置环境变量：

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."

# Unix/macOS
export OPENAI_API_KEY="sk-..."
```

## 📖 文档

> 🌐 **在线文档已发布！** 访问 https://nameistzzhang.github.io/phd_hunter/ 查看最新的自动构建文档。

完整文档见 `docs/` 目录或在线浏览：

- [安装指南](docs/source/installation.rst)
- [系统架构](docs/source/architecture.rst)
- [爬虫模块](docs/source/crawlers.rst)
- [Agent 系统](docs/source/agents.rst)
- [LLM 集成](docs/source/llm.rst)
- [报告生成](docs/source/reports.rst)
- [前端界面](docs/source/frontend.rst)
- [API 参考](docs/source/api.rst)
- [贡献指南](docs/source/contributing.rst)

构建文档：

```bash
cd docs
make html
```

## 🧪 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 带覆盖率报告
uv run pytest --cov=phd_hunter --cov-report=html

# 类型检查
uv run mypy src/phd_hunter/

# 代码格式化检查
uv run black --check src/
uv run ruff check src/
```

## 🛠️ 开发

### 代码规范

- 遵循 PEP 8
- 使用类型提示
- Google 风格 docstrings
- 提交前运行 pre-commit hooks

```bash
uv run pre-commit install
```

### 添加新功能

1. Fork 并创建功能分支
2. 编写代码和测试
3. 确保测试通过
4. 提交 PR

## 📊 使用示例

```python
from phd_hunter import PhDHunter

# 初始化
hunter = PhDHunter()

# 搜索教授
results = await hunter.search(
    universities=["MIT", "Stanford"],
    research_area="machine learning",
    max_professors=30
)

# 查看结果
for prof in results.professors:
    print(f"{prof.name} - 匹配度: {prof.match_score:.1f}%")
```

## 🔮 路线图

- [x] 项目结构和文档
- [x] CSRankings 爬虫基础实现
- [ ] Google Scholar 数据获取
- [ ] 导师主页解析
- [ ] arXiv 论文下载
- [ ] LLM 分析流水线
- [ ] 报告生成器
- [ ] Streamlit 前端完善
- [ ] FastAPI 后端完善
- [ ] 数据库持久化
- [ ] Docker 部署
- [ ] 批量处理

## 🤝 贡献

欢迎贡献！请阅读 [贡献指南](docs/source/contributing.rst) 了解详情。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 问题反馈：[GitHub Issues](https://github.com/your-org/phd-hunter/issues)
- 邮箱：team@phdhunter.dev

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
