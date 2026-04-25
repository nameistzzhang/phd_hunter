"""Setup configuration for api_infra package."""

from setuptools import setup, find_packages
import os

# Read README
def read_readme():
    """Read README file."""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Read requirements from requirements.txt if it exists
def read_requirements():
    """Read requirements from requirements.txt."""
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

# Package metadata
setup(
    name="api_infra",
    version="0.1.0",
    author="Your Name",
    description="A robust infrastructure for calling closed-source AI APIs with context management and tool use",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/api_infra",
    packages=["api_infra", "api_infra.core", "api_infra.context", "api_infra.tools"],
    package_dir={
        "api_infra": ".",
        "api_infra.core": "core",
        "api_infra.context": "context",
        "api_infra.tools": "tools",
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai api llm openai yunwu model client",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=1.10.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "ruff>=0.0.260",
        ],
    },
    entry_points={
        "console_scripts": [
            # Optional command-line interface scripts
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/api_infra/issues",
        "Source": "https://github.com/yourusername/api_infra",
    },
)
