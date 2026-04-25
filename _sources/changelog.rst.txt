Changelog
=========

所有 PhD Hunter 的重大更改都将记录在此。

[0.1.0] - 2026-04-25
---------------------

Added
~~~~~

* **Analyzer 模块** - 基于 LLM 的教授分析与套磁信生成
    * 首次对话自动生成教授分析报告 + cold email 草稿
    * 支持多轮对话修改套磁信
    * 基于用户 Profile（CV/PS/论文）个性化生成
* **Profile 页面** - 完整的用户资料管理
    * CV/PS PDF 上传与文本提取
    * arXiv 论文链接添加与解析
    * 研究偏好设置
* **教授匹配度打分** - LLM 驱动的评分系统
    * Direction Match Score (1-5): 研究方向匹配度
    * Admission Difficulty Score (1-5): 录取难度评估
    * 后台自动轮询打分，支持配置迭代次数
* **教授主页抓取** - Selenium + LLM 摘要
    * 自动抓取教授个人主页
    * AI 提取研究重点、招生状态、内容摘要
* **LLM 配置弹窗** - 可配置 API Key、模型、URL、温度等参数
* **Chat 页面改进**
    * 用户/AI 头像区分
    * 消息删除功能
    * "Analyzing..." 加载动画
    * 消息自动滚动
* **Web 界面改进**
    * 顶栏显示 Avg Match / Avg Diff 统计
    * 教授详情中论文标题可跳转 arXiv
    * 简化的 Basic Info / Metrics 布局

Changed
~~~~~~~

* 新增 ``api_infra`` 模块统一 LLM 客户端调用
* 新增 ``utils/pdf_extract.py`` 提取 PDF 文本，避免 scorer 与 analyzer 耦合
* 数据库表增加 ``direction_match_score``、``admission_difficulty_score``、``homepage_summary``、``messages`` 字段

[0.0.1] - 2026-04-21
---------------------

Added
~~~~~

* ArxivCrawler: 按作者搜索论文
* CLI 命令 ``fetch-papers``: 批量获取教授论文
* CLI 命令 ``stats`` / ``list``: 数据库查询
* Web 前端：教授浏览、筛选、优先级标记

Changed
~~~~~~~

* 主入口移至根目录 ``main.py``
* 简化项目结构

[0.0.0] - 2026-04-19
---------------------

Added
~~~~~

* 初始项目结构
* uv 依赖管理
* Sphinx 文档系统
* CSRankings 爬虫基础实现
* SQLite 数据库模型
