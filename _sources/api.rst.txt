API Reference
=============

当前版本使用命令行接口 (CLI) 作为主要 API。

命令行参考
----------

主程序入口: ``python main.py``

命令
~~~~

.. code-block:: text

   phd-hunter crawl [OPTIONS]
   phd-hunter fetch-papers [OPTIONS]
   phd-hunter stats
   phd-hunter list [OPTIONS]

详细信息请参考 :doc:`architecture`。

数据库 API
----------

直接使用 ``phd_hunter.database.Database`` 类进行编程访问。

快速示例：

.. code-block:: python

   from phd_hunter.database import Database
   from phd_hunter.models import Professor, University

   db = Database(db_path="phd_hunter.db")

   # 列出教授
   professors = db.list_professors(limit=10)

   # 获取单个教授
   prof = db.get_professor(prof_id=1)

   # 获取教授的论文
   papers = db.get_papers_by_professor(professor_id=1)

   # 导出为 JSON
   db.export_to_json("output.json")

Database 类
~~~~~~~~~~~

.. autoclass:: phd_hunter.database.Database
   :members:
   :undoc-members:
   :show-inheritance:

主要方法
^^^^^^^^

**连接与初始化**

- ``__init__(db_path: str = "phd_hunter.db")``
  初始化数据库连接并创建表。

**教授操作**

- ``list_professors(status, min_match_score, limit) -> List[Dict]``
  列出教授，支持过滤。

- ``get_professor(prof_id) -> Optional[Dict]``
  根据 ID 获取教授。

- ``get_professor_by_name(name, university_name) -> Optional[Dict]``
  根据姓名（可选的大学）获取教授。

- ``upsert_professor(prof: Professor, university: University) -> int``
  插入或更新教授记录，返回数据库 ID。

**论文操作**

- ``get_papers_by_professor(professor_id, limit) -> List[Dict]``
  获取某教授的所有论文。

- ``upsert_paper(professor_id, paper_data) -> int``
  插入或更新论文记录。

- ``get_professor_with_papers(professor_id) -> Optional[Dict]``
  获取教授及其所有论文（关联查询）。

**统计与导出**

- ``get_stats() -> Dict``
  获取数据库统计信息。

- ``export_to_json(output_path)``
  导出所有数据为 JSON 文件。

模型参考
--------

Professor
~~~~~~~~~

.. autoclass:: phd_hunter.models.Professor
   :members:
   :undoc-members:
   :show-inheritance:

Paper
~~~~~

.. autoclass:: phd_hunter.models.Paper
   :members:
   :undoc-members:
   :show-inheritance:

University
~~~~~~~~~~

.. autoclass:: phd_hunter.models.University
   :members:
   :undoc-members:
   :show-inheritance:

爬虫基类
--------

.. autoclass:: phd_hunter.crawlers.base.BaseCrawler
   :members:
   :undoc-members:
   :show-inheritance:

CSRankingsCrawler
~~~~~~~~~~~~~~~~~

.. autoclass:: phd_hunter.crawlers.csrankings.CSRankingsCrawler
   :members:
   :undoc-members:
   :show-inheritance:

ArxivCrawler
~~~~~~~~~~~~

.. autoclass:: phd_hunter.crawlers.arxiv_crawler.ArxivCrawler
   :members:
   :undoc-members:
   :show-inheritance:

参见
----

- :doc:`architecture`
- :doc:`crawlers`
- :doc:`contributing`
