Contributing
============

感谢你考虑为 PhD Hunter 做贡献！本文档概述了开发流程。

快速开始
--------

1. **Fork 并克隆**

   .. code-block:: bash

      git clone https://github.com/your-username/phd-hunter.git
      cd phd-hunter

2. **设置开发环境**

   .. code-block:: bash

      uv sync

3. **创建分支**

   .. code-block:: bash

      git checkout -b feature/my-feature

开发流程
--------

1. **编写代码**

   遵循 PEP 8，使用类型提示。

   .. code-block:: python

      from typing import Optional

      def search_professor(
          name: str,
          university: Optional[str] = None
      ) -> Professor:
          """Search for a professor by name."""
          ...

2. **运行测试**

   .. code-block:: bash

      python -m pytest tests/ -v

3. **代码格式化**

   .. code-block:: bash

      uv run black .
      uv run ruff check .

4. **提交**

   遵循 conventional commits:

   .. code-block:: text

      feat: add arxiv batch mode
      fix: handle professor not found
      docs: update installation guide

代码规范
--------

**Python**: PEP 8, 88 字符行限制

**类型提示**: 所有公开函数必需

**Docstrings**: Google 风格

**Imports**: 标准库 → 第三方 → 本地

添加功能
--------

1. **添加新爬虫**

   - 创建 ``crawlers/newsource.py``
   - 继承 ``BaseCrawler``
   - 实现 ``fetch()`` 方法
   - 在 ``crawlers/__init__.py`` 注册
   - 在 ``main.py`` 添加命令

2. **修改 CLI**

   在 ``main.py`` 中添加新的子命令和参数。

文档
----

构建文档：

.. code-block:: bash

   cd docs
   make html

提交代码时同时更新文档。

Pull Request 检查清单
---------------------

- [ ] 代码符合规范
- [ ] 测试通过
- [ ] 类型提示完整
- [ ] Docstrings 已更新
- [ ] 文档已更新
- [ ] CHANGELOG 已更新

获取帮助
--------

- Issues: https://github.com/your-org/phd-hunter/issues
- 邮箱: team@phdhunter.dev

许可证
------

MIT License - 详见 ``LICENSE`` 文件。
