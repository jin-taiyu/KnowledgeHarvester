from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="knowledge-harvester",
    version="0.1.0",
    description="A GUI tool for harvesting API documentation and converting it to AI-friendly formats",
    author="jin-taiyu",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "knowledge-harvester=src:main",
        ],
    },
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Text Processing :: Markup",
    ],
)
