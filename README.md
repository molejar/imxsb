i.MX SmartBoot Tool
===================

This tool is usable for managed boot of embedded devices based on i.MX application processors. It fully replaces the
[imx_loader](https://github.com/boundarydevices/imx_usb_loader) and adds features for an easy modification of binary
sections in boot images like:

* i.MX Device Configuration Data (DCD)
* U-Boot Environment Variables
* U-Boot Executable Image
* Kernel Device Tree Data

Later will be added support for on the fly sign and encryption of loaded boot images.

* i.MX Code Signing Data (CSF)

> This project is still in developing phase. Please, test it and report founded issues.

Dependencies
------------

- [Python](https://www.python.org) - Python 3.x interpreter
- [pyYAML](http://pyyaml.org/wiki/PyYAML) - YAML parser and emitter for the Python programming language.
- [Jinja2](https://pypi.python.org/pypi/Jinja2) - A small but fast and easy to use stand-alone template engine.
- [pyIMX](https://github.com/molejar/pyIMX) - Python module targeted for i.MX Applications Processors.
- [pyFDT](https://github.com/molejar/pyFDT) - Python package for manipulation with Device Tree images.
- [pyUBoot](https://github.com/molejar/pyUBoot) - Python package for manipulation with U-Boot images and environment variables.

for GUI only:

- [PyGObject](https://pygobject.readthedocs.io/en/latest/) - Python wrapper for the GTK+ graphical user interface library.
- [PyQT5](https://www.riverbankcomputing.com/software/pyqt/intro) - PyQt5 is a comprehensive set of Python bindings for Qt v5.
- [wxPython](https://wxpython.org/) - Cross-platform GUI toolkit for the Python language.

Installation
------------

The standalone executable for Linux and Windows OS are available in [releases](https://github.com/molejar/imxsb/releases) page.

In case of development clone this repo into your PC and install all dependencies:

``` bash
    $ git clone https://github.com/molejar/imxsb.git
    $ cd imxsb
    $ pip install -r requirements.txt
    $ pip install PyQT5 wxPython
```

>The PyGObject package is not available for Windows OS yet.

Usage
-----

The i.MX SmartBoot tool has standard command line interface and also user friendly GUI.

* [imxsb_cli](docs/imxsb_cli.md)
* [imxsb_gui](docs/imxsb_gui.md)
