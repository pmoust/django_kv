"""
Setup script for django-kv package.
"""

from setuptools import setup

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-kv",
    version="0.1.0",
    author="django-kv contributors",
    description="A pluggable Django cache backend using py-key-value stores",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pmoust/django_kv",
    packages=["django_kv", "django_kv.backends"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Framework :: Django",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Django>=5.1",
        "py-key-value-sync>=0.3.0",
    ],
    extras_require={
        "redis": ["py-key-value-sync[redis]>=0.3.0"],
        "otel": [
            "opentelemetry-sdk>=1.28.0",
            "opentelemetry-exporter-otlp>=1.28.0",
            "opentelemetry-instrumentation-django>=0.49b0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-django>=4.5",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
            "opentelemetry-sdk>=1.28.0",
            "opentelemetry-exporter-otlp>=1.28.0",
            "opentelemetry-instrumentation-django>=0.49b0",
        ],
    },
)

