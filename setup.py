from setuptools import setup

setup(
    name='mcpacker',
    version='0.11.0',
    description="Wrapper for vberlier's mcpack",
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author='Eli112358',
    url='https://github.com/Eli112358/mcpacker',
    packages=['mcpacker'],
    package_dir={'mcpacker': 'src'},
    requires=[
        'deprecated',
        'dill',
        'mcpack',
        'nbtlib',
    ],
    provides=['mcpacker'],
    package_data={'mcpacker': ['data/*.json']},
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ]
)
