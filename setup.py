from setuptools import find_namespace_packages, setup

setup(
    name="cli-anything-pennylane",
    version="0.1.0",
    description="Agent-friendly CLI harness for the Pennylane Company API v2",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={"cli_anything.pennylane": ["skills/*.md"]},
    install_requires=["click>=8.0.0", "prompt-toolkit>=3.0.0"],
    entry_points={
        "console_scripts": [
            "cli-anything-pennylane=cli_anything.pennylane.pennylane_cli:main",
        ],
    },
    python_requires=">=3.10",
)
