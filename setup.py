"""
Build for membank
"""
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

    setuptools.setup(
        name="membank",
        version="0.3.1",
        author="Juris Kaminskis",
        author_email="juris.kaminskis@gmail.com",
        description="A library to handle persistent memory",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/Kolumbs/membank",
        project_urls={
            "Bug Tracker": "https://github.com/Kolumbs/membank/issues",
        },
        classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Database",
        ],
        packages=["membank"],
        install_requires=["alembic", "sqlalchemy"],
        python_requires=">=3.10",
)
