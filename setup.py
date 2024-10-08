import os
from setuptools import setup, find_packages


version = '0.4.1'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


install_requires = [
    'mistune <= 1',
]

tests_require = [
    'pytest >= 8',
    'coverage >= 7',
    'flake8',
    'autopep8',
]

devtools_require = [
    'twine',
    'build',
]

setup(name='sdiff',
      version=version,
      description=('sdiff compares the structure of two markdown texts'),
      classifiers=[
          'License :: OSI Approved :: BSD License',
          'Intended Audience :: Developers',
          'Programming Language :: Python'],
      author='Keepsafe',
      author_email='support@getkeepsafe.com',
      url='https://github.com/KeepSafe/html-structure-diff/',
      license='Apache',
      packages=find_packages(exclude=['tests']),
      package_data={},
      namespace_packages=[],
      install_requires=install_requires,
      tests_require=tests_require,
      extras_require={
          'tests': tests_require,
          'devtools': devtools_require,
      },
      include_package_data=False)
