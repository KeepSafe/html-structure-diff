import os
from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession

version = '0.2.2'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()

install_reqs = parse_requirements('requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]


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
      install_requires = reqs,
      include_package_data = False)
