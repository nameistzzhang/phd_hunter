Installation Guide
==================

本指南帮助你在本地设置 PhD Hunter。

前提条件
--------

* **Python**: 3.10 或更高
* **uv**: 推荐的包管理器（或 pip）
* **浏览器**: Chrome 或 Chromium（用于 Selenium）

分步安装
--------

1. **克隆仓库**

   .. code-block:: bash

      git clone https://github.com/your-org/phd-hunter.git
      cd phd-hunter

2. **创建虚拟环境**

   使用 **uv** (推荐):

   .. code-block:: bash

      uv sync

      # 激活虚拟环境 (Windows PowerShell)
      .venv\Scripts\Activate.ps1

   使用 **pip**:

   .. code-block:: bash

      python -m venv .venv
      .venv\Scripts\activate  # Windows
      pip install -e .

3. **安装浏览器驱动**

   PhD Hunter 使用 Selenium 进行网页爬取。需要 Chrome/Chromium 和 ChromeDriver：

   - **方式 A: 自动安装** (推荐)

     .. code-block:: bash

        uv run pip install webdriver-manager

   - **方式 B: 手动安装**

     1. 从 https://chromedriver.chromium.org/ 下载 ChromeDriver
     2. 将 ChromeDriver 添加到 PATH

4. **验证安装**

   运行快速检查：

   .. code-block:: bash

      python main.py --help

   应该看到可用的命令列表。

故障排除
--------

**问题**: ``ModuleNotFoundError: No module named 'phd_hunter'``

**解决**: 确认已安装包：

.. code-block:: bash

   pip install -e .

**问题**: Selenium WebDriver 错误

**解决**: 确保 Chrome/Chromium 已安装且 ChromeDriver 版本匹配。

**问题**: 在 Windows 上权限错误

**解决**: 以管理员身份运行 PowerShell 或修改执行策略：

.. code-block:: bash

   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

下一步
------

- 阅读 :doc:`architecture` 了解架构
- 学习 :doc:`crawlers` 了解爬虫
- 查看 :doc:`api` 了解 API 参考
