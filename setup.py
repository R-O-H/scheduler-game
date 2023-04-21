import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="scheduler",
    version="0.1.0",
    author="Ricardo Hernandez",
    author_email=["roh12@rutgers.edu", "ricardoohernand@gmail.com"],
    description="A game about scheduling tasks to complete in the shortest time",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mygame",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["pygame"],
)
