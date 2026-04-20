Crawlers
========

本模块负责从学术来源获取数据。

概述
----

爬虫负责从不同来源获取数据：

* 从 CSRankings 获取教授列表
* 从 arXiv 搜索教授发表的论文

所有爬虫遵循速率限制并包含重试逻辑。

CSRankings Crawler
------------------

**文件**: ``crawlers/csrankings.py``

从 https://csrankings.org 提取教授数据。

功能：

- 选择特定机构和 CS 子领域
- 提取教授姓名、主页和 affiliations
- 使用 Selenium 处理动态页面内容

使用：

.. code-block:: python

   from phd_hunter.crawlers.csrankings import CSRankingsCrawler

   crawler = CSRankingsCrawler(headless=True)
   universities, professors = crawler.fetch(
       areas=["ai"],
       region="world",
       max_professors=5
   )
   # 返回 University 和 Professor 对象列表

提取的数据：

- 大学名称、排名、分数
- 教授姓名
- 大学 URL
- 教授主页（从排名页面提取）

arXiv Crawler
-------------

**文件**: ``crawlers/arxiv_crawler.py``

按作者从 arXiv 搜索论文。

功能：

- 按作者姓名搜索论文
- 按提交日期排序（最新的优先）
- 返回论文元数据（标题、作者、摘要、年份、PDF 链接）

使用：

.. code-block:: python

   from phd_hunter.crawlers.arxiv_crawler import ArxivCrawler
   from phd_hunter.models import Professor

   crawler = ArxivCrawler()
   prof = Professor(name="Yangqiu Song")
   papers = crawler.fetch(prof, max_papers=10)
   # 返回 Paper 对象列表

提取的数据：

- 论文标题
- 作者列表
- 摘要
- 发表年份
- arXiv ID
- PDF URL

配置
----

当前配置通过命令行参数传递。关键参数：

.. code-block:: text

   CSRankingsCrawler:
     --headless / --no-headless   # 无头模式
     --timeout 30                 # 超时（秒）
     --max-professors 5          # 每校最大教授数

   ArxivCrawler:
     --delay 1.0                 # 请求间隔（秒）
     --max-papers 10             # 每位教授最大论文数

缓存
----

所有爬虫结果被缓存以避免冗余请求：

- **缓存位置**: 内存缓存（进程内）
- **缓存键**: 参数 hash
- **有效期**: 默认 1 天

速率限制
--------

为尊重数据源：

- 请求之间自动延时
- arXiv: 默认 1 秒间隔（可配置）

错误处理
--------

爬虫处理：

- 网络超时（重试）
- 页面布局变化（容错处理）
- 数据缺失（返回部分结果）

添加新爬虫
----------

添加新数据源：

1. 创建 ``crawlers/newsource.py``
2. 继承 ``BaseCrawler``
3. 实现 ``fetch()`` 方法
4. 在 ``crawlers/__init__.py`` 中注册
5. 在 ``main.py`` 中添加命令

示例：

.. code-block:: python

   from phd_hunter.crawlers.base import BaseCrawler

   class DBLPCrawler(BaseCrawler):
       def fetch(self, query: str):
           # 实现爬取逻辑
           pass

参见
----

- :doc:`architecture`
- :doc:`api`
