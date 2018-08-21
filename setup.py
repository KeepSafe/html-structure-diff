import os
from setuptools import setup, find_packages


version = '0.3.0'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


install_requires = [
    'mistune <= 1',
]

setup(name='sdiff',
      version=version,
      description=('sdiff compares the structure of two markdown texts'),
      long_description='\n\n'.join((read('README.md'), read('CHANGELOG'))),
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
      include_package_data=False)
