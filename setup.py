from setuptools import find_packages, setup

setup(
    name="Covid19AnalysisProjectLib",
    packages=find_packages(include=["Covid19AnalysisProjectLib", "Covid19AnalysisProjectLib.*"]),
    version="0.1.0",
    description="A pipeline to run the Covid19 Analysis Project",
    author="Alexis BALAYRE",
    license="MIT",
)
