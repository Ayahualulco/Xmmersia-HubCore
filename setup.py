from setuptools import setup, find_packages

setup(
    name="xmmersia-hubcore",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.22.0",
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ]
    },
    python_requires=">=3.10",
    author="Marc Santugini",
    author_email="marc@xmmersia.com",
    description="Foundation for all Xmmersia Hubs - unified interfaces for agent collaboration",
    long_description=open("README.md", encoding="utf-8").read(),
    url="https://github.com/Ayahualulco/Xmmersia-HubCore",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
