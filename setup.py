import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='knossos_aam',
    version='0.1',
    packages=find_packages(),
    scripts=["knossos-aam"],
    include_package_data=True,
    license='GPL2',  # example license
    description='The server-side administration program for KNOSSOS Task Management.',
    long_description=read("README.md"),
    url="https://github.com/knossos-project/knossos_aam",
    author='Fabian Svara',
    author_email='knossos-team@mpimf-heidelberg.mpg.de',
    install_requires =[
        "django",
        "django_extensions",
        "GDAL",
        "psycopg2"
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',  # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
