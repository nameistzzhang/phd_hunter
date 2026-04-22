Architecture Overview
=====================

本文档描述 PhD Hunter 的系统架构。

系统设计
--------

PhD Hunter 采用简洁的模块化设计，核心包含爬虫、数据库、Web 界面和命令行接口四个部分。

.. code-block:: text

   ┌────────────────────────────────────────────────────┐
   │    Web Frontend (Flask + HTML/CSS/JS)              │
   │    • Professor cards with priority & filters       │
   │    • Real-time filtering & sorting                 │
   │    • Modal detail view with papers                 │
   └────────────────────┬───────────────────────────────┘
                        │ REST API
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌─────────┐
   │ CLI     │    │  Arxiv  │    │ SQLite  │
   │(main.py)│    │ Crawler │    │Database │
   └─────────┘    └──────────┘    └─────────┘
         │
         ▼
   ┌─────────────┐
   │ CSRankings  │
   │   Crawler   │
   └─────────────┘

核心组件
--------

1. **Web 前端界面** (frontend/)

   Flask + 原生 HTML/CSS/JavaScript 构建的可视化界面：

   - ``app.py``: Flask API 服务器，提供 JSON 数据接口
   - ``index.html``: 主页面，包含导航栏、筛选栏、教授列表和详情弹窗
   - ``styles.css``: 黑白简约风格样式表
   - ``app.js``: 前端逻辑（数据加载、筛选、优先级更新、弹窗显示）

   主要功能：
   - 教授卡片展示（分数、论文数、研究领域、优先级色条）
   - 三维筛选（Priority / Research Area / University）
   - 优先级下拉菜单修改（实时保存到数据库）
   - 教授详情弹窗（基本信息、指标、论文列表）

2. **CLI 入口** (main.py)

   命令行主程序，提供三个子命令：

   - ``crawl``: 从 CSRankings 爬取教授信息
   - ``fetch-papers``: 从 arXiv 获取教授论文
   - ``stats`` / ``list``: 查看数据库内容

2. **爬虫模块** (crawlers/)

   - ``CSRankingsCrawler``: 使用 Selenium 爬取 CSRankings.org 的大学排名和教授列表
   - ``ArxivCrawler``: 使用 arXiv API 按作者搜索论文

   所有爬虫继承自 ``BaseCrawler``，支持缓存机制。

3. **数据库** (database.py)

   SQLite 数据库，包含：

   - ``professors`` 表: 教授基本信息
   - ``papers`` 表: 论文元数据

   提供完整的 CRUD 操作和数据导出功能。

4. **数据模型** (models.py)

   Pydantic 模型定义：

   - ``Professor``: 教授信息
   - ``Paper``: 论文信息
   - ``University``: 大学信息

5. **工具模块** (utils/)

   - ``logger.py``: 结构化日志配置
   - ``helpers.py``: 通用辅助函数

数据流程
--------

1. **爬取阶段**

   .. code-block::

      User → main.py crawl
         → CSRankingsCrawler.fetch()
         → Selenium 打开浏览器
         → 解析 HTML 提取教授列表
         → Database.upsert_professor()
         → SQLite 保存

2. **论文获取阶段**

   .. code-block::

      User → main.py fetch-papers
         → Database.list_professors()
         → 对每位教授:
            ArxivCrawler.fetch(professor)
            → arxiv.Search 查询
            → 解析返回结果
            → Database.upsert_paper()
         → SQLite 保存

3. **Web 界面查询阶段**

   .. code-block::

      Browser → Flask app.py (GET /api/professors)
         → Database.list_professors()
         → JSON 返回教授列表
         → JavaScript 渲染卡片 + 筛选

      Browser → Flask app.py (POST /api/professor/<id>/priority)
         → Database.update_professor_priority()
         → 更新数据库并返回最新列表

4. **命令行查询阶段**

   .. code-block::

      User → main.py stats / list
         → Database.get_stats() / list_professors()
         → 格式化输出

配置
----

当前版本无需配置文件，所有参数通过命令行传递。

未来可能的配置项：

- 数据库路径
- 爬虫延迟时间
- 缓存设置
- 日志级别

扩展性
------

添加新爬虫：

1. 创建 ``crawlers/newsource.py``
2. 继承 ``BaseCrawler``
3. 实现 ``fetch()`` 方法
4. 在 ``crawlers/__init__.py`` 中注册
5. 在 main.py 中添加对应命令

示例：

.. code-block:: python

   from .base import BaseCrawler

   class DBLPCrawler(BaseCrawler):
       def fetch(self, query: str):
           # 实现爬取逻辑
           pass

开发流程
--------

1. 修改代码
2. 运行验证: ``python main.py ...``
3. 提交变更

参见
----

- :doc:`crawlers`
- :doc:`api`
- :doc:`contributing`
