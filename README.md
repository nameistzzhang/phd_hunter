# PhD Hunter 🎓

**PhD 导师套磁筛选助手** - 自动化收集 CS 教授信息及其最新论文

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-alpha-yellow.svg)

## ✨ 当前功能

- 📊 **CSRankings 爬取** - 自动获取各大学 CS 领域教授排名和名单
- 📝 **arXiv 论文获取** - 按作者搜索并保存最新论文元数据
- 💾 **SQLite 存储** - 所有数据本地持久化
- 🌐 **Web 可视化界面** - 基于 Flask 的交互式教授浏览和筛选
- 🏷️ **优先级标记** - 为每位教授标记优先级（冲刺/匹配/稳妥/保底/不考虑）
- 🔍 **多维筛选** - 按优先级、研究领域、大学筛选教授列表

## 🚀 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- Chrome/Chromium 浏览器（用于 Selenium）

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

### 使用

**命令行模式：**

```bash
# 1. 爬取教授数据
python main.py crawl --area ai --region world --max-professors 5

# 2. 获取论文
python main.py fetch-papers --max-papers 10

# 3. 查看统计
python main.py stats

# 4. 列出教授
python main.py list --limit 20
```

**Web 界面模式：**

```bash
# 启动 Flask Web 服务器（默认 http://localhost:5000）
cd src/phd_hunter/frontend
python run_server.py
```

然后在浏览器中打开 http://localhost:5000，即可：
- 浏览所有教授卡片（显示匹配分数、论文数、研究领域）
- 使用顶部筛选栏按优先级 / 领域 / 大学筛选
- 点击教授卡片查看详细信息（包含论文列表）
- 通过下拉菜单修改教授优先级（自动保存到数据库）

## 📁 项目结构

```
phd_hunter/
├── main.py                       # CLI 入口 (根目录)
├── arxiv_demo.py                 # arXiv API 演示脚本
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
├── docs/                         # Sphinx 文档
└── src/phd_hunter/
    ├── __init__.py              # 包初始化
    ├── models.py                # Pydantic 数据模型
    ├── database.py              # SQLite 数据库操作
    ├── crawlers/
    │   ├── __init__.py          # 导出 ArxivCrawler, CSRankingsCrawler
    │   ├── base.py              # 爬虫基类 (缓存支持)
    │   ├── csrankings.py        # CSRankings 爬虫 (Selenium)
    │   └── arxiv_crawler.py     # arXiv 爬虫 (arxiv API)
    ├── utils/
    │   ├── logger.py            # 日志配置
    │   └── helpers.py           # 工具函数
    └── frontend/                # Web 前端界面
        ├── app.py               # Flask API 服务器
        ├── index.html           # 主页面
        ├── static/
        │   ├── styles.css       # 样式表
        │   ├── app.js           # 前端逻辑
        │   └── setting_icon.svg # 设置图标
        └── templates/           # HTML 模板
```

## 🗄️ 数据库结构

项目使用 SQLite 存储数据，包含两张表：

### professors 表
- 教授基本信息（姓名、大学、院系、邮箱）
- 研究方向、个人主页、优先级（-1~3）
- 论文统计、匹配分数等指标

### papers 表
- 论文元数据（标题、作者、摘要、年份）
- arXiv ID 和 PDF 链接
- 关联到教授记录

## 🔧 命令行详解

### `crawl` - 爬取教授信息

从 CSRankings 获取教授列表。

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
- `-v, --verbose`：详细日志

### `fetch-papers` - 获取论文

从 arXiv 搜索并保存教授的论文。

```bash
python main.py fetch-papers --max-papers 10 --max-professors 50
```

**参数：**
- `--max-papers`：每位教授最大论文数（默认：10）
- `--max-professors`：最大处理教授数（默认：全部）
- `--delay`：请求间隔（秒，默认：1.0）

### `stats` - 统计信息

显示数据库统计摘要。

```bash
python main.py stats
```

### `list` - 列出教授

查看数据库中的教授记录。

```bash
python main.py list --limit 20 --min-score 50
```

**参数：**
- `--limit`：显示数量限制
- `--min-score`：最低匹配分数过滤

## 🌐 Web 界面

项目包含一个基于 Flask 的 Web 可视化界面，用于浏览和管理教授数据。

### 启动 Web 服务器

```bash
# 进入 frontend 目录
cd src/phd_hunter/frontend

# 启动 Flask 服务器（默认 http://localhost:5000）
python run_server.py
```

### 使用 Web 界面

1. 在浏览器中打开 http://localhost:5000
2. 左侧面板显示所有教授卡片，包含：
   - 匹配分数、论文数、链接数
   - 研究领域标签（最多 3 个）
   - 优先级颜色条（右侧边缘）
3. 使用顶部筛选栏：
   - **Priority**：按优先级筛选
   - **Research Area**：按研究领域筛选
   - **University**：按大学筛选
4. 点击教授卡片查看详细信息（论文列表、联系方式等）
5. 使用卡片上的下拉菜单修改教授优先级（自动保存）

## ⚠️ 已知限制

1. **arXiv 覆盖度**：并非所有教授都在 arXiv 发表论文
2. **作者歧义**：arXiv 作者搜索可能包含重名结果（后续可改进消歧）
3. **速率限制**：arXiv API 限制每分钟约 30 次请求，代码已包含延时

## 📊 数据库文件

默认数据库文件：`phd_hunter.db`

```bash
# 使用 sqlite3 命令行查看
sqlite3 phd_hunter.db "SELECT name FROM sqlite_master WHERE type='table'"

# 导出为 JSON
python -c "from phd_hunter.database import Database; db=Database(); db.export_to_json('export.json')"
```

## 🔍 arXiv 演示

运行 `arxiv_demo.py` 测试作者搜索效果：

```bash
python arxiv_demo.py
```

## 📖 文档

> 🌐 **在线文档已发布！** 访问 https://nameistzzhang.github.io/phd_hunter/ 查看最新的自动构建文档。

完整文档见 `docs/` 目录或本地浏览：
- [安装指南](docs/source/installation.rst)
- [系统架构](docs/source/architecture.rst)
- [爬虫模块](docs/source/crawlers.rst)
- [API 参考](docs/source/api.rst)

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
uv run mypy src/
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 问题反馈：[GitHub Issues](https://github.com/your-org/phd-hunter/issues)
- 邮箱：team@phdhunter.dev

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
