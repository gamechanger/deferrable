import os
import sys
import imp

try:
    from restricted_pkg import setup
except:
    # allow falling back to setuptools only if
    # we are not trying to upload
    if 'upload' in sys.argv:
        raise ImportError('restricted_pkg is required to upload, first do pip install restricted_pkg')
    from setuptools import setup

try:
    requirements = imp.load_source('requirements', os.path.realpath('static_requirements.py'))
    print 'Using static requirements'
except (IOError, ImportError):
    requirements = imp.load_source('requirements', os.path.realpath('dynamic_requirements.py'))
    print 'Using dynamic requirements'

setup(
    name='deferrable',
    version='0.0.1',
    description='Queueing framework with pluggable backends',
    url='https://github.com/gamechanger/deferrable',
    private_repository='gamechanger',
    author='GameChanger',
    author_email='travis@gamechanger.io',
    packages=['deferrable'],
    install_requires=requirements.install_requires,
    tests_require=requirements.test_requires,
    test_suite="nose.collector",
    zip_safe=False
)
