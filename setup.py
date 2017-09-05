#!/usr/bin/env python3

import os
from distutils.core import setup
from distutils.command.build_py import build_py
import setuptools  # so we have develop mode


class build( build_py ):
  def run( self ):
    # get all the .py files, unless they end in _test.py
    # we don't need testing files in our published product
    for package in self.packages:
      package_dir = self.get_package_dir( package )
      modules = self.find_package_modules( package, package_dir )
      for ( package2, module, module_file ) in modules:
        assert package == package2
        if os.path.basename( module_file ).endswith( '_test.py' ):
          continue
        self.build_module( module, module_file, package )


setup( name='cinp',
       version='0.9.2',
       description='CInP, Concise Interaction Protocol',
       author='Peter Howe',
       author_email='pnhowe@gmail.com',
       url='https://github.com/cinp/python',
       python='~=3.5',
       packages=[ 'cinp' ],
       cmdclass={ 'build_py': build }
     )
