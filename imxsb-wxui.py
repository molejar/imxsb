#!/usr/bin/env python

# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import sys
import imx
import time
import signal
import threading

# SmartBoot Core module
import core

# wxPython module
import wx
import wx.adv
import wx.dataview

# Application base directory
BASEDIR = os.path.dirname(os.path.realpath(__file__))

# The range of progressbar
PGRANGE = 1000


# ...
def elapsed_time(start_time):
    elapsed = time.time() - start_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return "[{:02d}:{:06.3f}]".format(int(minutes), seconds)


# Worker class
class Worker(threading.Thread):

    def __init__(self, device, script, logger, finish, prgbar):
        super().__init__()
        self._device = device
        self._script = script
        self._logger = logger
        self._finish = finish
        self._prgbar = prgbar
        # internal variables
        self._running = False
        self._pgstp = 0
        self._pgval = 0

    def stop(self):
        self._running = False

    def progress_handler(self, level):
        wx.CallAfter(self._prgbar, self._pgval + (self._pgstp / PGRANGE) * level)
        return self._running

    def run(self):
        self._running = True
        self._script.set_pgrange(PGRANGE)
        self._device.pg_range = PGRANGE

        start_time = time.time()

        wx.CallAfter(self._logger, " START: {}\n".format(self._script.name))
        try:
            # connect target
            self._device.open(self.progress_handler)
            for cmd in self._script:

                if not self._running:
                    break

                self._pgval += self._pgstp
                self._pgstp = cmd['pg']

                # print command info
                wx.CallAfter(self._logger, " {} {}\n".format(elapsed_time(start_time), cmd['description']), False)

                if cmd['name'] == 'wreg':
                    self._device.write(cmd['address'], cmd['value'], cmd['bytes'])

                elif cmd['name'] == 'wdcd':
                    self._device.write_dcd(cmd['address'], cmd['data'])

                elif cmd['name'] == 'wimg':
                    self._device.write_file(cmd['address'], cmd['data'])

                elif cmd['name'] == 'sdcd':
                    self._device.skip_dcd()

                elif cmd['name'] == 'jrun':
                    self._device.jump_and_run(cmd['address'])

                else:
                    raise Exception("Command: {} not supported".format(cmd['name']))

            wx.CallAfter(self._prgbar, PGRANGE)

        except Exception as e:
            wx.CallAfter(self._finish, " STOP: {}".format(str(e)), False)

        else:
            wx.CallAfter(self._finish, " DONE: Successfully started", True)

        finally:
            self._device.close()


# Main Window Class
class MainWindow(wx.Frame):

    smx_file = core.SmxFile()
    hotplug = core.HotPlug()
    devices = []
    target = None
    worker = None

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="i.MX Smart-Boot Tool", size=wx.Size(600, 400))
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.SetIcon(wx.Icon(os.path.join(BASEDIR, 'icon.png')))
        self.SetMinSize(self.GetSize())
        self.Centre()

        # create main box
        layout = wx.BoxSizer(wx.VERTICAL)

        # --------------------------------------------------------------------------------------------------------------
        # Device selection drop-box with scan button
        # --------------------------------------------------------------------------------------------------------------
        box = wx.BoxSizer(wx.HORIZONTAL)

        # device selection drop-box
        self.devices_box = wx.Choice(parent=self)
        box.Add(self.devices_box, 1, wx.TOP | wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        # scan button
        self.scan_button = wx.Button(parent=self, label=u"Scan", size=wx.Size(80, -1))
        self.scan_button.Bind(wx.EVT_BUTTON, self.OnScanButtonClicked)
        box.Add(self.scan_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        layout.Add(box, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)

        # --------------------------------------------------------------------------------------------------------------
        # SMX File inbox with open button
        # --------------------------------------------------------------------------------------------------------------
        box = wx.BoxSizer(wx.HORIZONTAL)

        # smx path inbox
        self.smxPath = wx.TextCtrl(parent=self, value=wx.EmptyString, style=wx.TE_READONLY)
        box.Add(self.smxPath, 1, wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        # open button
        self.open_button = wx.Button(parent=self, label=u"Open", size=wx.Size(80, -1))
        self.open_button.Bind(wx.EVT_BUTTON, self.OnOpenButtonClicked)
        box.Add(self.open_button, 0, wx.BOTTOM | wx.RIGHT | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        layout.Add(box, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # --------------------------------------------------------------------------------------------------------------
        # Body
        # --------------------------------------------------------------------------------------------------------------
        mbox = wx.BoxSizer(wx.VERTICAL)
        splitter = wx.SplitterWindow(parent=self, style=(wx.SP_LIVE_UPDATE | wx.SP_BORDER | wx.SP_THIN_SASH))
        splitter.SetSashGravity(0)
        splitter.SetSashSize(20)
        splitter.Bind(wx.EVT_IDLE, self.SplitterOnIdle)
        splitter.SetMinimumPaneSize(58)

        # ...
        panel1 = wx.Panel(parent=splitter, style=wx.TAB_TRAVERSAL)
        box = wx.BoxSizer(wx.VERTICAL)
        self.scriptList = wx.ListBox(parent=panel1, style=wx.LB_SINGLE)
        box.Add(self.scriptList, 1, wx.EXPAND | wx.BOTTOM | wx.TOP, 1)
        panel1.SetSizer(box)
        panel1.Layout()
        box.Fit(panel1)

        # ...
        panel2 = wx.Panel(parent=splitter, style=wx.TAB_TRAVERSAL)
        box = wx.BoxSizer(wx.VERTICAL)
        self.textCtrl = wx.TextCtrl(parent=panel2, style=(wx.TE_MULTILINE | wx.TE_READONLY))
        box.Add(self.textCtrl, 1, wx.EXPAND | wx.BOTTOM | wx.TOP, 1)
        panel2.SetSizer(box)
        panel2.Layout()
        box.Fit(panel2)

        splitter.SplitHorizontally(window1=panel1, window2=panel2, sashPosition=85)
        mbox.Add(splitter, 1, wx.EXPAND | wx.BOTTOM, 5)

        layout.Add(mbox, 1, wx.EXPAND | wx.RIGHT | wx.LEFT, 10)

        # --------------------------------------------------------------------------------------------------------------
        # Progress Bar
        # --------------------------------------------------------------------------------------------------------------
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.pg_mtask = wx.Gauge(parent=self, range=PGRANGE, size=wx.Size(-1, 10), style=wx.GA_HORIZONTAL)
        self.pg_mtask.SetValue(0)
        box.Add(self.pg_mtask, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 2)

        layout.Add(box, 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 10)

        # --------------------------------------------------------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------------------------------------------------------
        # separator
        #main_box.Add(wx.StaticLine(parent=self, style=wx.LI_HORIZONTAL), 0, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)

        # About Button
        self.about_button = wx.Button(parent=self, label=u"About", size=wx.Size(100, 40), style=0)
        self.about_button.Bind(wx.EVT_BUTTON, self.OnAboutButtonClicked)
        box.Add(self.about_button, 0, wx.ALL, 5)

        # Device Info Button
        self.info_button = wx.Button(parent=self, label=u"DevInfo", size=wx.Size(100, 40), style=0)
        self.info_button.Bind(wx.EVT_BUTTON, self.OnInfoButtonClicked)
        self.info_button.Enable(False)
        box.Add(self.info_button, 0, wx.ALL, 5)

        # Spacer
        box.Add((0, 0), 1, wx.EXPAND, 5)

        # Start Button
        self.start_button = wx.Button(parent=self, label=u"Start", size=wx.Size(100, 40), style=0)
        self.start_button.Bind(wx.EVT_BUTTON, self.OnStartButtonClicked)
        self.start_button.Enable(False)
        box.Add(self.start_button, 0, wx.ALL, 5)

        # Exit Button
        self.exit_button = wx.Button(parent=self, label=u"Exit", size=wx.Size(100, 40), style=0)
        self.exit_button.Bind(wx.EVT_BUTTON, self.OnExitButtonClicked)
        box.Add(self.exit_button, 0, wx.ALL, 5)

        layout.Add(box, 0, wx.EXPAND | wx.BOTTOM | wx.RIGHT | wx.LEFT | wx.TOP, 5)

        self.SetSizer(layout)
        self.Layout()

        # USB hotplug (Linux only)
        # self.hotplug.attach(self.scan_usb)
        # self.hotplug.start()
        # TODO: Fix USB hot-plug
        self.ScanUSB()

    ####################################################################################################################
    # Helper methods
    ####################################################################################################################
    def ScanUSB(self, obj=None):
        self.start_button.Enable(False)
        self.info_button.Enable(False)
        self.devices_box.Enable(False)
        self.devices_box.Clear()

        self.devices = imx.sdp.scan_usb(self.target)
        if self.devices:
            for dev in self.devices:
                self.devices_box.Append([dev.usbd.info()])
            self.devices_box.SetSelection(0)
            self.devices_box.Enable(True)
            self.info_button.Enable(True)
            if self.target is not None:
                self.start_button.Enable(True)

    def ShowMesageBox(self, caption, message, mtype=wx.ICON_INFORMATION):
        wx.MessageBox(parent=self,
                      caption=caption,
                      message=message,
                      style=(wx.OK | mtype))

    def Logger(self, msg, clear=True):
        if clear:
            self.textCtrl.Clear()
        if msg:
            self.textCtrl.AppendText(msg)

    def ProgressBar(self, value):
        self.pg_mtask.SetValue(min(int(value), PGRANGE))

    def SplitterOnIdle(self, event):
        splitter = event.GetEventObject()
        splitter.SetSashPosition(58)
        splitter.Unbind(wx.EVT_IDLE)
        event.Skip()

    def OnWorkerFinish(self, msg, done):
        self.Logger(msg, False)
        self.start_button.SetLabel("Start")
        self.scan_button.Enable(True)
        self.open_button.Enable(True)
        self.scriptList.Enable(True)
        if done:
            self.devices_box.Clear()
            self.start_button.Enable(False)
        else:
            self.ScanUSB()

    ####################################################################################################################
    # Buttons callback methods
    ####################################################################################################################
    def OnScanButtonClicked(self, event):
        self.ScanUSB()
        event.Skip()

    def OnOpenButtonClicked(self, event):
        with wx.FileDialog(parent=self,
                           message="Choose a SmartBoot script file",
                           wildcard="i.MX SmartBoot Files (*.smx)|*.smx",
                           defaultDir=BASEDIR,
                           style=(wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_OK:
                path = fileDialog.GetPaths()[0]
                self.smxPath.Clear()
                self.scriptList.Clear()
                try:
                    self.smx_file.open(path, True)
                except Exception as e:
                    self.ShowMesageBox("SMX File Open Error", str(e), wx.ICON_ERROR)
                    self.target = None
                    self.start_button.Enable(False)
                else:
                    self.smxPath.SetValue(path)
                    self.target = self.smx_file.platform
                    for i, item in enumerate(self.smx_file.scripts):
                        self.scriptList.Append(["{}.  {}  ({})".format(i, item.name, item.description)])
                    self.scriptList.SetSelection(0)
                    # update usb device list
                    self.ScanUSB()
        event.Skip()

    def OnAboutButtonClicked(self, event):
        if os.name == 'posix':
            info = wx.adv.AboutDialogInfo()
            #info.SetIcon(wx.Icon('hunter.png', wx.BITMAP_TYPE_PNG))
            info.SetName('i.MX SmartBoot Tool')
            info.SetVersion(core.__version__)
            info.SetDescription(core.DESCRIPTION)
            info.SetCopyright('Copyright \xa9 2018 Martin Olejar')
            info.SetWebSite('https://github.com/molejar/imxsb')
            info.SetLicence(core.LICENSE)
            info.AddDeveloper('Martin Olejar')
            info.AddDocWriter('Martin Olejar')
            wx.adv.AboutBox(info, self)
        else:
            text = "i.MX SmartBoot Tool v {}\n".format(core.__version__)
            text += "{}\n".format(core.DESCRIPTION)
            text += "License: {}\n".format(core.__license__)
            text += "Sources: https://github.com/molejar\n"
            text += "Copyright 2018 Martin Olejar."
            wx.MessageBox(parent=self, message=text, caption="About", style=(wx.OK | wx.ICON_INFORMATION))

    def OnInfoButtonClicked(self, event):
        device = self.devices[self.devices_box.GetSelection()]
        device.open()
        self.Logger("Device: {} \n".format(device.device_name))
        device.close()
        event.Skip()

    def OnStartButtonClicked(self, event):
        if self.start_button.GetLabel() == "Start":
            try:
                device = self.devices[self.devices_box.GetSelection()]
                script = self.smx_file.get_script(self.scriptList.GetSelection())
            except Exception as e:
                self.ShowMesageBox("Script Load Error", str(e), wx.ICON_ERROR)
            else:
                # Start Worker
                self.worker = Worker(device, script, self.Logger, self.OnWorkerFinish, self.ProgressBar)
                self.worker.daemon = True
                self.worker.start()

                self.start_button.SetLabel("Stop")
                self.scan_button.Enable(False)
                self.open_button.Enable(False)
                self.info_button.Enable(False)
                self.devices_box.Enable(False)
                self.scriptList.Enable(False)
        else:
            # Stop Worker
            self.worker.stop()
            self.worker.join()

        event.Skip()

    def OnExitButtonClicked(self, event):
        sys.exit(0)


def main(argv):
    app = wx.App()
    window = MainWindow(None)
    window.Show()
    app.MainLoop()


if __name__ == "__main__":
    main(sys.argv)
