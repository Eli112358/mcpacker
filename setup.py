from setuptools import setup

setup(
    name='mcpacker',
    version='0.8.0',
    description="Wrapper for vberlier's mcpack",
    author='Eli112358',
    url='https://github.com/Eli112358/mcpacker',
    packages=['mcpacker'],
    package_dir={'mcpacker': 'src'},
    requires=[
        'dill',
        'mcpack',
        'nbtlib'
    ],
    provides=['mcpacker'],
    package_data={'mcpacker': ['data/*.json']},
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ]
)
