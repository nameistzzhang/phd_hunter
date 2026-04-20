Changelog
=========

所有 PhD Hunter 的重大更改都将记录在此。

[0.2.0] - 2026-04-21 (进行中)
-----------------------------

Added
~~~~~

* ArxivCrawler: 按作者搜索论文
* CLI 命令 ``fetch-papers``: 批量获取教授论文
* CLI 命令 ``stats`` / ``list``: 数据库查询
* 简化项目结构，移除 LLM/Agent/Frontend 模块

Changed
~~~~~~~

* 主入口移至根目录 ``main.py``
* 依赖项精简，移除 LLM 相关依赖
* 文档更新以反映简化架构

[0.1.0] - 2026-04-19
---------------------

Added
~~~~~

* 初始项目结构
* uv 依赖管理
* Sphinx 文档系统
* CSRankings 爬虫基础实现
* SQLite 数据库模型
