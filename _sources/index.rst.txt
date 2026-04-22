PhD Hunter - PhD 导师套磁筛选助手
====================================

PhD Hunter 是一个轻量级的 PhD 导师信息收集工具，专注于自动化获取 CS 领域教授信息及其最新论文。

当前功能
--------

* **CSRankings 数据爬取**: 自动爬取 CSRankings 网站获取院校和导师信息
* **arXiv 论文获取**: 按作者搜索并保存最新论文元数据
* **SQLite 存储**: 所有数据本地持久化
* **Web 可视化界面**: 基于 Flask 的交互式教授浏览、筛选和管理
* **优先级标记**: 为每位教授标记优先级（冲刺/匹配/稳妥/保底/不考虑）
* **多维筛选**: 按优先级、研究领域、大学筛选教授列表

项目架构
--------

.. code-block:: text

    phd_hunter/
    ├── main.py                       # CLI 入口 (根目录)
    ├── arxiv_demo.py                 # arXiv API 演示
    ├── pyproject.toml                # 项目配置
    ├── README.md                     # 项目说明
    ├── docs/                         # Sphinx 文档
    └── src/phd_hunter/
        ├── models.py                 # Pydantic 数据模型
        ├── database.py               # SQLite 数据库操作
        ├── crawlers/
        │   ├── base.py               # 爬虫基类 (缓存支持)
        │   ├── csrankings.py         # CSRankings 爬虫
        │   └── arxiv_crawler.py      # arXiv 爬虫
        ├── utils/
        │   ├── logger.py             # 日志配置
        │   └── helpers.py            # 工具函数
        └── frontend/                 # Web 前端界面
            ├── app.py                # Flask API 服务器
            ├── index.html            # 主页面
            ├── static/
            │   ├── styles.css        # 样式表
            │   ├── app.js            # 前端逻辑
            │   └── assets/           # 静态资源 (图标等)
            └── templates/            # HTML 模板

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
      cd phd-hunter

2. **安装依赖**

   使用 uv (推荐):

   .. code-block:: bash

      uv sync

   或使用 pip:

   .. code-block:: bash

      python -m venv .venv
      .venv\Scripts\activate  # Windows
      pip install -e .

3. **运行应用**

   命令行模式：

   .. code-block:: bash

      # 爬取教授数据
      python main.py crawl --area ai --region world --max-professors 5

      # 获取论文
      python main.py fetch-papers --max-papers 10

      # 查看统计
      python main.py stats

   Web 界面模式：

   .. code-block:: bash

      # 启动 Flask 服务器
      cd src/phd_hunter/frontend
      python run_server.py

      # 然后在浏览器打开 http://localhost:5000

文档
----

.. toctree::
   :maxdepth: 2
   :caption: 目录:

   installation
   architecture
   crawlers
   api
   contributing
   changelog

索引与表格
----------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
