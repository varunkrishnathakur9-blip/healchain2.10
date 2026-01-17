#!/usr/bin/env python3
"""
HealChain FL Client Setup
Minimal setup configuration for the HealChain Federated Learning Client
"""

from setuptools import setup, find_packages

setup(
    name="healchain-fl-client",
    version="1.0.0",
    description="HealChain Federated Learning Client (Miner)",
    author="HealChain Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "web3>=6.15.1",
        "eth-account>=0.11.0",
        "eth-hash>=0.7.0",
        "tinyec>=0.4.0",
        "torch>=2.0.0",
        "numpy>=1.24",
        "requests>=2.31",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "healchain-client=scripts.start_client:main",
            "healchain-test=scripts.test_client:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
