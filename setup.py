from setuptools import setup, find_packages
import os

# Membaca requirements.txt jika ada
install_requires = []
if os.path.exists('requirements.txt'):
    with open('requirements.txt', 'r') as f:
        install_requires = f.read().splitlines()
else:
    install_requires = [
        "click",
        "httpx",
        "browser-cookie3",
        "beautifulsoup4"
    ]

setup(
    name='keyreach',
    version='0.1.0',
    description='KeyReach - Zero-Trust Capability Layer for AI Agents',
    author='KeyReach Team',
    packages=find_packages(include=['channels*', 'core*']),
    py_modules=["main", "router"],
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'keyreach=main:cli',
        ],
    },
)
