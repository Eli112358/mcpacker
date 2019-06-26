from distutils.core import setup

setup(
    name='mcpacker',
    version='0.1',
    description="Wrapper for vberlier's mcpack",
    author='Eli112358',
    packages=['mcpacker'],
    package_dir={'mcpacker': 'src'},
    requires=[
        'mcpack',
        'nbtlib'
    ],
    provides=['mcpacker'],
    package_data={'mcpacker': ['data/*.json']}
)
