import os
import subprocess
from setuptools import find_packages, setup


def read(fname):
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), fname), "rb"
    ) as fid:
        return fid.read().decode("utf-8")


def output(cmd):
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()


try:
    version = read("version").strip()
except IOError:
    try:
        version = (
            output("git describe --tags --exact-match")
            .replace(".tag", "")
            .replace("pypi.", "")
        )
    except subprocess.CalledProcessError:
        # git_version will be 1.0.10-<n>-g<sha>
        # where n is number of commits after last tag
        # and <sha> is the commit sha
        # if the current commit is not the last tag
        # otherwise it will simply be the last tag version
        tag_version, n_commits, commit_sha = output("git describe --tags").split("-")
        tag_version = tag_version.replace("pypi.", "")
        version = "{tag_version}.post{n_commits}".format(**locals())


setup(
    name="deferrable",
    version=version,
    description="Queueing framework with pluggable backends",
    url="https://github.com/gamechanger/deferrable",
    author="GameChanger",
    author_email="travis@gamechanger.io",
    packages=find_packages(),
    package_data={"deferrable": ["lua/*.lua"]},
    install_requires=read("requirements.txt").splitlines(),
    tests_require=read("requirements-tests.txt").splitlines()[1:],
    test_suite="nose.collector",
    zip_safe=False,
)
