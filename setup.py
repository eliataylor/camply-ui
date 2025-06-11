from setuptools import setup, find_packages

setup(
    name="camply-favorites",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "jinja2>=3.0.0",
        "pandas>=2.0.0",
        "beautifulsoup4>=4.9.0",
        "pyyaml>=6.0.0",
        "requests>=2.25.0",
        "google-api-python-client>=2.0.0",
    ],
    python_requires=">=3.7",
) 