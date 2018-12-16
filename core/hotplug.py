# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import os


class HotPlugBase:

    def __init__(self):
        pass

    def attach(self, callback):
        pass

    def start(self):
        pass

    def stop(self):
        pass


if os.name == 'posix':

    import pyudev
    # import syslog

    class HotPlug(HotPlugBase):

        def __init__(self, callback=None):
            super().__init__()
            context = pyudev.Context()
            # context.log_priority = syslog.LOG_DEBUG
            self.monitor = pyudev.Monitor.from_netlink(context)
            self.monitor.filter_by(subsystem='usb')
            self.callback = None
            self.observer = None
            if callback is not None:
                self.attach(callback)

        def attach(self, callback):
            self.callback = callback

        def start(self):
            assert self.callback is not None, ""
            self.callback()
            self.observer = pyudev.MonitorObserver(self.monitor, callback=self.callback, name='monitor-observer')
            self.observer.start()

        def stop(self):
            assert self.callback is not None, ""
            if self.observer is not None:
                self.observer.stop()
                self.observer = None


elif os.name == 'nt':

    class HotPlug(HotPlugBase):

        def __init__(self, callback=None):
            super().__init__()
            self.callback = None
            if callback is not None:
                self.attach(callback)

        def attach(self, callback):
            self.callback = callback

        def start(self):
            assert self.callback is not None, ""
            self.callback()


else:

    raise OSError('Not supported OS type')
