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
import queue
import threading
import collections

# SmartBoot Core module
import core

# TK module
from tkinter import ttk, filedialog, messagebox, PanedWindow
try:
    from ttkthemes import ThemedTk as Tk
except:
    from tkinter import Tk


# Application base directory
BASEDIR = os.path.dirname(os.path.realpath(__file__))

# The range of progressbar
PGRANGE = 1000

# Queue Message Format
Message = collections.namedtuple('Message', ['status', 'msg', 'value', 'done'])


# ...
def elapsed_time(start_time):
    elapsed = time.time() - start_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return "[{:02d}:{:06.3f}]".format(int(minutes), seconds)


# Worker class
class Worker(threading.Thread):

    def __init__(self, device, script, queue):
        super().__init__()
        self._device = device
        self._script = script
        self._queue = queue
        # internal variables
        self._running = False
        self._pgstp = 0
        self._pgval = 0

    def stop(self):
        self._running = False

    def progress_handler(self, level):
        self._queue.put(Message("progress", "", self._pgval + (self._pgstp / PGRANGE) * level, False))
        return self._running

    def run(self):
        self._running = True
        self._script.set_pgrange(PGRANGE)
        self._device.pg_range = PGRANGE
        self._device.pg_resolution = 150

        start_time = time.time()

        self._queue.put(Message("logger", " START: {}\n".format(self._script.name), 1, False))
        try:
            # connect target
            self._device.open(self.progress_handler)
            for cmd in self._script:

                if not self._running:
                    break

                self._pgval += self._pgstp
                self._pgstp = cmd['pg']

                # print command info
                self._queue.put(
                    Message("logger", " {} {}\n".format(elapsed_time(start_time), cmd['description']), 0, False)
                )

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

            self._queue.put(Message("progress", "", PGRANGE, False))

        except Exception as e:
            self._queue.put(Message("finish", " STOP: {}".format(str(e)), 0, False))
            pass

        else:
            self._queue.put(Message("finish", " DONE: Successfully started", 0, True))
            pass

        finally:
            self._device.close()


# Main Window Class
class MainWindow(Tk):

    smx_file = core.SmxFile()
    hotplug = core.HotPlug()
    devices = []
    running = False
    target = None
    worker = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("i.MX Smart-Boot Tool")
        self.wm_minsize(600, 450)

        # Top separator
        ttk.Frame(self).pack(fill='x', pady=4)

        # --------------------------------------------------------------------------------------------------------------
        # Device selection drop-box with scan button
        # --------------------------------------------------------------------------------------------------------------
        frame = ttk.Frame(self)
        frame.pack(fill='x', padx=5)

        self.devices_box = ttk.Combobox(frame, state='readonly')
        self.devices_box.pack(side='left', fill='x', expand=True, padx=2, pady=3)

        self.scan_button = ttk.Button(frame, text="Scan", command=self.on_scan_button_clicked)
        self.scan_button.pack(side='right', padx=2, pady=2)

        # --------------------------------------------------------------------------------------------------------------
        # SMX File inbox with open button
        # --------------------------------------------------------------------------------------------------------------
        frame = ttk.Frame(self)
        frame.pack(fill='x', padx=5)

        self.smx_path = ttk.Entry(frame)
        self.smx_path.pack(side='left', fill='x', expand=True, padx=2, pady=0)

        self.open_button = ttk.Button(frame, text="Open", command=self.on_open_button_clicked)
        self.open_button.pack(side='right', padx=2, pady=2)

        # --------------------------------------------------------------------------------------------------------------
        # Body
        # --------------------------------------------------------------------------------------------------------------
        pw = PanedWindow(self, orient='vertical')
        pw.pack(fill='both', expand=True, padx=6, pady=2)

        frame = ttk.Frame()
        frame.pack(fill='x', padx=4)

        self.script_view = ttk.Treeview(frame, height=5, columns=('num', 'name', 'desc'), show="headings")
        self.script_view.heading('num', text='-')
        self.script_view.heading('name', text='Name')
        self.script_view.heading('desc', text='Description')
        self.script_view.column('num', minwidth=25, width=25, anchor='center', stretch='no')
        self.script_view.column('name', minwidth=160, width=160, anchor='center', stretch='no')
        self.script_view.column('desc', width=100, anchor='w')
        self.script_view.pack(side='left', fill='both', expand=True)

        vsb1 = ttk.Scrollbar(frame, orient="vertical", command=self.script_view.yview)
        vsb1.pack(side='right', fill='y')
        self.script_view.configure(yscrollcommand=vsb1.set)

        pw.add(frame)
        pw.paneconfig(frame, minsize=95, height=95)

        frame = ttk.Frame()
        frame.pack(fill='both', padx=4)

        self.log_view = ttk.Treeview(frame, height=5, columns=('desc',), show='', selectmode='none')
        self.log_view.column('desc', anchor='w')
        self.log_view.pack(side='left', fill='both', expand=True)

        vsb2 = ttk.Scrollbar(frame, orient="vertical", command=self.log_view.yview)
        vsb2.pack(side='right', fill='y')
        self.log_view.configure(yscrollcommand=vsb2.set)

        pw.add(frame)
        pw.paneconfig(frame, minsize=85)

        self.progressbar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progressbar["maximum"] = PGRANGE
        self.progressbar.pack(fill='x', padx=6, pady=2)

        # --------------------------------------------------------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------------------------------------------------------
        frame = ttk.Frame(self)
        frame.pack(fill='x', side='bottom', padx=4, pady=5)

        self.about_button = ttk.Button(frame, text="About", command=self.on_about_button_clicked)
        self.about_button.pack(side='left', padx=2, pady=2)
        self.info_button = ttk.Button(frame, text="DevInfo", command=self.on_info_button_clicked, state='disabled')
        self.info_button.pack(side='left', padx=2, pady=2)
        self.exit_button = ttk.Button(frame, text="Exit", command=self.on_exit_button_clicked)
        self.exit_button.pack(side='right', padx=2, pady=2)
        self.start_button = ttk.Button(frame, text="Start", command=self.on_start_button_clicked, state='disabled')
        self.start_button.pack(side='right', padx=2, pady=2)

        self.queue = queue.Queue()

        # USB hotplug (Linux only)
        # self.hotplug.attach(self.scan_usb)
        # self.hotplug.start()
        # TODO: Fix USB hot-plug
        self.scan_usb()

    ####################################################################################################################
    # Helper methods
    ####################################################################################################################
    def scan_usb(self):
        self.devices = imx.sdp.scan_usb(self.target)
        if self.devices:
            self.devices_box.state(['!disabled'])
            self.devices_box['values'] = [dev.usbd.info for dev in self.devices]
            self.devices_box.current(0)
            self.info_button.state(['!disabled'])
            if self.target is not None:
                self.start_button.state(['!disabled'])
        else:
            self.devices_box.set('')
            self.devices_box.state(['disabled'])
            self.info_button.state(['disabled'])
            self.start_button.state(['disabled'])

    def get_script_selection_index(self):
        return self.script_view.index(self.script_view.selection())

    def show_mesage_box(self, title, message, mtype='info'):
        if mtype == 'info':
            messagebox.showinfo(title, message)
        elif mtype == 'warning':
            messagebox.showwarning(title, message)
        else:
            messagebox.showerror(title, message)

    def logger(self, msg, clear=True):
        if clear:
            self.log_view.delete(*self.log_view.get_children())
        self.log_view.insert('', 'end', text='', value=(msg,))

    def check_queue(self):
        if not self.queue.empty():
            item = self.queue.get()

            if item.status == 'progress':
                self.progressbar["value"] = int(item.value)
                self.after(100, self.check_queue)
            elif item.status == 'logger':
                self.logger(item.msg, True if item.value else False)
                self.after(100, self.check_queue)
            else:
                self.logger(item.msg, False)
                self.start_button.configure(text="Start")
                self.scan_button.state(['!disabled'])
                self.open_button.state(['!disabled'])
                self.script_view.state(['!disabled'])
                if item.done:
                    self.devices_box.set('')
                    self.start_button.state(['disabled'])
                else:
                    self.scan_usb()
        else:
            if self.running:
                self.after(100, self.check_queue)

    ####################################################################################################################
    # Buttons callback methods
    ####################################################################################################################
    def on_scan_button_clicked(self):
        self.scan_usb()

    def on_open_button_clicked(self):
        path = filedialog.askopenfilename(parent=self,
                                          initialdir=os.getcwd(),
                                          title="Select a SmartBoot script file",
                                          filetypes=(("i.MX SmartBoot Files", "*.smx"),))
        if path:
            self.smx_path.state(['!readonly'])
            self.smx_path.delete(0, 'end')
            self.smx_path.state(['readonly'])
            self.script_view.delete(*self.script_view.get_children())

            try:
                self.smx_file.open(path, True)
            except Exception as e:
                self.show_mesage_box("SMX File Open Error", str(e), 'error')
                self.target = None
                self.start_button.state(['disabled'])
            else:
                self.smx_path.state(['!readonly'])
                self.smx_path.insert('', path)
                self.smx_path.state(['readonly'])
                self.target = self.smx_file.platform
                for i, item in enumerate(self.smx_file.scripts):
                    self.script_view.insert('', 'end', text=str(i), value=(str(i), item.name, item.description))
                self.script_view.selection_set(self.script_view.get_children()[0])
                # update usb device list
                self.scan_usb()

    def on_about_button_clicked(self):
        text = "i.MX SmartBoot Tool v {}\n".format(core.__version__)
        text += "{}\n".format(core.DESCRIPTION)
        text += "License: {}\n".format(core.__license__)
        text += "Sources: https://github.com/molejar\n"
        text += "Copyright 2018 Martin Olejar."
        messagebox.showinfo("About", text)

    def on_info_button_clicked(self):
        device = self.devices[self.devices_box.current()]
        device.open()
        device_info = " Device: {}".format(device.device_name.strip())
        device.close()
        self.logger(device_info)

    def on_start_button_clicked(self):
        if not self.running:
            try:
                device = self.devices[self.devices_box.current()]
                script = self.smx_file.get_script(self.get_script_selection_index())
            except Exception as e:
                self.show_mesage_box("Script Load Error", str(e), 'error')
            else:
                # Start Worker
                self.worker = Worker(device, script, self.queue)
                self.worker.daemon = True
                self.worker.start()

                self.start_button.configure(text="Stop")
                self.scan_button.state(['disabled'])
                self.open_button.state(['disabled'])
                self.info_button.state(['disabled'])
                self.devices_box.state(['disabled'])
                self.script_view.state(['disabled'])
                self.running = True
                self.check_queue()
        else:
            # Stop Worker
            self.worker.stop()
            self.worker.join()
            self.running = False

    @staticmethod
    def on_exit_button_clicked():
        sys.exit(0)


def main(argv):
    app = MainWindow()
    try:
        app.set_theme('arc')
    except:
        pass
    app.mainloop()


if __name__ == "__main__":
    main(sys.argv)
