.. PhD Hunter documentation master file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PhD Hunter - PhD 导师套磁筛选助手
====================================

PhD Hunter 是一个智能化的 PhD 导师套磁筛选系统，通过自动化爬取和分析学术信息，帮助你找到最适合的博士导师。

核心功能
--------

* **CSRankings 数据爬取**: 自动爬取 CSRankings 网站获取院校和导师信息
* **Google Scholar 追踪**: 获取导师近年发表论文及引用情况
* **导师主页解析**: 提取导师基本信息、研究方向、招生情况等
* **arXiv 论文下载**: 自动下载相关论文全文
* **LLM 智能分析**: 使用大语言模型分析导师研究方向、招生偏好、学生背景匹配度
* **报告生成**: 生成结构化的套磁建议和评估报告
* **前端界面**: 提供友好的 Web 界面进行交互

项目架构
--------

.. code-block:: text

    phd_hunter/
    ├── crawlers/          # 爬虫模块
    │   ├── csrankings.py  # CSRankings 爬取
    │   ├── scholar.py     # Google Scholar 爬取
    │   ├── professor.py   # 导师主页解析
    │   └── arxiv.py       # arXiv 论文下载
    ├── agents/            # Agent 模块
    │   ├── coordinator.py # 协调 Agent
    │   ├── researcher.py  # 研究分析 Agent
    │   └── reporter.py    # 报告生成 Agent
    ├── llm/               # LLM 接口
    │   ├── client.py      # LLM API 客户端
    │   └── prompts.py     # Prompt 模板
    ├── reports/           # 报告模块
    │   ├── templates/     # 报告模板
    │   └── generator.py   # 报告生成器
    ├── utils/             # 工具模块
    │   ├── config.py      # 配置管理
    │   ├── logger.py      # 日志工具
    │   └── helpers.py     # 辅助函数
    ├── config/            # 配置文件
    │   └── settings.yaml  # 应用配置
    ├── frontend/          # 前端界面
    │   ├── app.py         # Streamlit 主程序
    │   └── pages/         # 页面模块
    ├── tests/             # 测试文件
    ├── pyproject.toml     # 项目配置
    └── README.md          # 项目说明

快速开始
--------

环境要求
~~~~~~~~

* Python 3.10+
* uv (推荐) 或 pip
* Chrome/Chromium 浏览器 (用于 Selenium)

安装步骤
~~~~~~~~

1. **克隆项目**

   .. code-block:: bash

      git clone <repository-url>
      cd phd_hunter

2. **创建虚拟环境**

   使用 uv (推荐):

   .. code-block:: bash

      uv sync

   或使用 pip:

   .. code-block:: bash

      python -m venv .venv
      .venv\\Scripts\\activate  # Windows
      pip install -e .

3. **配置环境变量**

   复制配置文件模板:

   .. code-block:: bash

      copy config\\settings.example.yaml config\\settings.yaml

   编辑 ``config/settings.yaml`` 填入你的 API Keys:

   .. code-block:: yaml

      llm:
        provider: "openai"  # 或 "anthropic"
        api_key: "your-api-key"
        model: "gpt-4o"    # 或 "claude-3-opus"

      crawlers:
        selenium:
          headless: true
          timeout: 30

      output:
        reports_dir: "./reports"
        papers_dir: "./papers"

4. **运行应用**

   .. code-block:: bash

      # 启动前端界面
      uv run streamlit run frontend/app.py

      # 或使用 API 服务
      uv run uvicorn main:app --reload

文档
----

.. toctree::
   :maxdepth: 2
   :caption: 目录:

   installation
   architecture
   crawlers
   agents
   llm
   reports
   frontend
   api
   contributing
   changelog

索引与表格
----------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
