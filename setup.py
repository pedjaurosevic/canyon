from setuptools import setup, find_packages

setup(
    name="canyon-bench",
    version="0.1.0",
    author="Canyon Team",
    description="A framework for mechanistic and behavioural evaluation of semantic grounding in LLMs",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pedjaurosevic/canyon",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.0.0",
        "rich>=13.0.0",
        "click>=8.0.0",
        "pyyaml>=6.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "accelerate>=0.20.0",
        "textual>=0.40.0",
    ],
    entry_points={
        "console_scripts": [
            "canyon=canyon.cli:cli",
            "canon=canyon.cli:cli",
        ],
    },
    python_requires=">=3.10",
)
