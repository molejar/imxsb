i.MX SmartBoot Tool
===================

[![Last Release](https://img.shields.io/github/release/molejar/imxsb.svg)](https://github.com/molejar/imxsb/releases)

This tool is usable for managed boot of embedded devices based on i.MX application processors. It fully replaces the
[imx_loader](https://github.com/boundarydevices/imx_usb_loader) and adds features for an easy modification of binary
sections in boot images like:

* i.MX Device Configuration Data (DCD)
* U-Boot Environment Variables
* U-Boot Executable Image
* Kernel Device Tree Data

Later will be added support for on the fly sign and encryption of loaded boot images.

* i.MX Code Signing Data (CSF)

All of this is complemented by user-friendly graphical interface.

<p align="center">
  <img src="docs/images/imxsb_gtkui_run.png" alt="i.MX SmartBoot Tool GUI: Main window"/>
</p>

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

The standalone executables for Windows OS are available in [releases](https://github.com/molejar/imxsb/releases) page. For Linux users
will exist installation packages later, at this moment use raw sources.

In case of development clone this repo into your PC and install all dependencies:

``` bash
    $ git clone https://github.com/molejar/imxsb.git
    $ cd imxsb
    $ pip install -r requirements.txt
```

For running `imxsb-wxui.py` install `wxPython` package:

``` bash
    $ pip install wxPython
```

For running `imxsb-qtui.py` install `PyQT5` package:

``` bash
    $ pip install PyQT5
```

For running `imxsb-gtkui.py` install `PyGObject` package:

``` bash
    $ pip install PyGObject
```

>The PyGObject package is available only for Linux OS yet.

Usage
-----

The i.MX SmartBoot tool is available int two variants:

* [imxsb-cli](docs/imxsb-cli.md) - with standard command line interface
* [imxsb-gui](docs/imxsb-gui.md) - with user friendly graphical interface

> Linux users can get into device permission issue if run i.MX SmartBoot tool without root privileges (sudo).
To fix this problem install udev rules distributed with [pyIMX](https://github.com/molejar/pyIMX) package.