import sys

try:
    from restricted_pkg import setup
except:
    # allow falling back to setuptools only if
    # we are not trying to upload
    if 'upload' in sys.argv:
        raise ImportError('restricted_pkg is required to upload, first do pip install restricted_pkg')
    from setuptools import setup

setup(
    name='deferrable',
    version='0.0.1',
    description='Queueing framework with pluggable backends',
    url='https://github.com/gamechanger/deferrable',
    private_repository='gamechanger',
    author='GameChanger',
    author_email='travis@gamechanger.io',
    packages=['deferrable'],
    install_requires=[
        'Dockets>=0.3.4,<0.4.0'
    ],
    tests_require=[
        'nose>=1.3.0,<2.0.0',
        'mock>=1.0.0,<2.0.0',
        'redis>=2.10.0,<3.0.0'
    ],
    test_suite="nose.collector",
    zip_safe=False
)
