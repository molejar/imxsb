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

# GTK module
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

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
        GLib.idle_add(self._prgbar, self._pgval + (self._pgstp / PGRANGE) * level)
        return self._running

    def run(self):
        self._running = True
        self._script.set_pgrange(PGRANGE)
        self._device.pg_range = PGRANGE

        start_time = time.time()
        GLib.idle_add(self._logger, " START: {}\n".format(self._script.name))

        try:
            # connect target
            self._device.open(self.progress_handler)
            for cmd in self._script:

                if not self._running:
                    break

                self._pgval += self._pgstp
                self._pgstp = cmd['pg']

                # print command info
                GLib.idle_add(self._logger, " {} {}\n".format(elapsed_time(start_time), cmd['description']), False)

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

            GLib.idle_add(self._prgbar, PGRANGE)

        except Exception as e:
            GLib.idle_add(self._finish, " STOP: {}".format(str(e)), False)

        else:
            GLib.idle_add(self._finish, " DONE: Successfully started", True)

        finally:
            self._device.close()


# Main Window Class
class MainWindow(Gtk.Window):

    smx_file = core.SmxFile()
    hotplug = core.HotPlug()
    devices = []
    target = None
    worker = None

    def __init__(self):
        Gtk.Window.__init__(self, title="i.MX Smart-Boot Tool")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_from_file(os.path.join(BASEDIR, 'icon.png'))
        self.set_default_size(600, 400)
        self.set_size_request(600, 400)
        self.set_border_width(6)

        # create main box
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # --------------------------------------------------------------------------------------------------------------
        # Device selection drop-box with scan button
        # --------------------------------------------------------------------------------------------------------------
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # device selection drop-box
        self.devices_name = Gtk.ListStore(str)
        self.devices_box = Gtk.ComboBox.new_with_model(self.devices_name)
        renderer_text = Gtk.CellRendererText()
        self.devices_box.pack_start(renderer_text, True)
        self.devices_box.add_attribute(renderer_text, "text", 0)
        self.devices_box.set_sensitive(False)
        box.pack_start(self.devices_box, True, True, 0)

        # scan button
        self.scan_button = Gtk.Button(label=" Scan", image=Gtk.Image(stock=Gtk.STOCK_UNDO))
        self.scan_button.connect("clicked", self.on_scan_button_clicked)
        self.scan_button.set_size_request(80, 20)
        box.pack_start(self.scan_button, False, True, 0)

        layout.pack_start(box, False, True, 0)

        # --------------------------------------------------------------------------------------------------------------
        # SMX File inbox with open button
        # --------------------------------------------------------------------------------------------------------------
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # smx path inbox
        self.smx_path = Gtk.Entry()
        self.smx_path.set_can_focus(False)
        self.smx_path.set_editable(False)
        box.pack_start(self.smx_path, True, True, 0)

        # open button
        self.open_button = Gtk.Button(label=" Open", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        self.open_button.connect("clicked", self.on_open_button_clicked)
        self.open_button.set_size_request(80, 20)
        box.pack_start(self.open_button, False, True, 0)

        layout.pack_start(box, False, True, 0)

        # --------------------------------------------------------------------------------------------------------------
        # Body
        # --------------------------------------------------------------------------------------------------------------
        paned_box = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned_box.set_border_width(1)
        paned_box.set_wide_handle(True)
        paned_box.set_position(50)

        # smx scripts list
        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=False)
        scrolled_window.set_size_request(-1, 100)
        self.liststore = Gtk.ListStore(str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        column = Gtk.TreeViewColumn("N", Gtk.CellRendererText(xalign=0.5), text=0)
        column.set_property('alignment', 0.5)
        self.treeview.append_column(column)
        column = Gtk.TreeViewColumn("Script Name", Gtk.CellRendererText(), text=1)
        column.set_property('alignment', 0.5)
        self.treeview.append_column(column)
        column = Gtk.TreeViewColumn("Description", Gtk.CellRendererText(), text=2)
        column.set_property('alignment', 0.5)
        self.treeview.append_column(column)
        scrolled_window.add(self.treeview)
        paned_box.pack1(scrolled_window, False, False)

        # smx debug box
        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window.set_size_request(-1, 100)
        self.textview = Gtk.TextView(editable=False, cursor_visible=False)
        scrolled_window.add(self.textview)
        paned_box.pack2(scrolled_window, False, False)

        layout.pack_start(paned_box, True, True, 0)

        # ProgressBar
        self.progressbar = Gtk.ProgressBar(show_text=False)
        self.progressbar.set_show_text(False)
        self.progressbar.set_fraction(0.0)
        layout.pack_start(self.progressbar, False, True, 3)

        # --------------------------------------------------------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------------------------------------------------------
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # About Button
        about_button = Gtk.Button(label=" About", image=Gtk.Image(stock=Gtk.STOCK_DIALOG_QUESTION))
        about_button.set_size_request(100, 40)
        about_button.connect("clicked", self.on_about_button_clicked)
        box.pack_start(about_button, False, True, 0)

        # Device Info Button
        self.info_button = Gtk.Button(label=" DevInfo", image=Gtk.Image(stock=Gtk.STOCK_DIALOG_INFO))
        self.info_button.set_size_request(100, 40)
        self.info_button.set_sensitive(False)
        self.info_button.connect("clicked", self.on_info_button_clicked)
        box.pack_start(self.info_button, False, True, 0)

        # Exit Button
        self.exit_button = Gtk.Button(label=" Exit", image=Gtk.Image(stock=Gtk.STOCK_CLOSE))
        self.exit_button.set_size_request(100, 40)
        self.exit_button.connect("clicked", self.on_exit_button_clicked)
        box.pack_end(self.exit_button, False, True, 0)

        # Start Button
        self.start_button = Gtk.Button(label=" Start", image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        self.start_button.set_size_request(100, 40)
        self.start_button.set_sensitive(False)
        self.start_button.connect("clicked", self.on_start_button_clicked)
        box.pack_end(self.start_button, False, True, 0)

        layout.pack_start(box, False, True, 2)
        self.add(layout)

        # USB hotplug (Linux only)
        # self.hotplug.attach(self.scan_usb)
        # self.hotplug.start()
        # TODO: Fix USB hot-plug
        self.scan_usb()

    ####################################################################################################################
    # Helper methods
    ####################################################################################################################
    def scan_usb(self, obj=None):
        self.devices_box.set_sensitive(False)
        self.info_button.set_sensitive(False)
        self.start_button.set_sensitive(False)
        self.devices_name.clear()

        self.devices = imx.sdp.scan_usb(self.target)
        if self.devices:
            for dev in self.devices:
                self.devices_name.append([dev.usbd.info])
            self.devices_box.set_active(0)
            self.devices_box.set_sensitive(True)
            self.info_button.set_sensitive(True)
            if self.target is not None:
                self.start_button.set_sensitive(True)

    def get_script_selection_index(self):
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter is not None:
            return int(model[treeiter][0])
        return 0

    def show_mesage_box(self, head, message, mtype=Gtk.MessageType.INFO):
        md = Gtk.MessageDialog(parent=self,
                               flags=0,
                               message_type=mtype,
                               buttons=Gtk.ButtonsType.OK,
                               text=head)
        md.format_secondary_text(message)
        md.run()
        md.destroy()
        self.set_sensitive(True)

    def logger(self, msg, clear=True):
        if clear:
            self.textview.get_buffer().set_text(msg)
        else:
            self.textview.get_buffer().insert_at_cursor(msg)

    def pgbar(self, val):
        self.progressbar.set_fraction(val / PGRANGE)

    ####################################################################################################################
    # Buttons callback methods
    ####################################################################################################################
    def on_scan_button_clicked(self, widget):
        self.scan_usb()

    def on_open_button_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Choose a SmartBoot script file", action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        smx_filter = Gtk.FileFilter()
        smx_filter.set_name("i.MX SmartBoot Files (*.smx)")
        smx_filter.add_pattern("*.smx")
        dialog.add_filter(smx_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.liststore.clear()
            self.smx_path.set_text("")
            try:
                self.smx_file.open(path, True)
            except Exception as e:
                self.show_mesage_box("SMX File Open Error", str(e), Gtk.MessageType.ERROR)
                self.target = None
                self.start_button.set_sensitive(False)
            else:
                self.smx_path.set_text(path)
                self.target = self.smx_file.platform
                for i, item in enumerate(self.smx_file.scripts):
                    self.liststore.append([str(i), item.name, item.description])
                self.treeview.set_cursor(0)
                # update usb device list
                self.scan_usb()

        dialog.destroy()

    def on_about_button_clicked(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_modal(False)
        about_dialog.set_transient_for(self)
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_default_response(Gtk.ResponseType.CLOSE)

        # fill the about dialog
        about_dialog.set_title("About")
        about_dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file(os.path.join(BASEDIR, 'icon.png')))
        about_dialog.set_program_name("i.MX SmartBoot Tool")
        about_dialog.set_version(core.__version__)
        about_dialog.set_comments(core.DESCRIPTION)
        about_dialog.set_copyright("Copyright \xa9 2018 Martin Olejar")
        about_dialog.set_website("https://github.com/molejar/imxsb")
        about_dialog.set_website_label("https://github.com/molejar/imxsb")
        about_dialog.set_authors(["Martin Olejar"])
        about_dialog.set_documenters(["Martin Olejar"])
        about_dialog.set_license(core.LICENSE)

        about_dialog.run()
        about_dialog.destroy()

    def on_info_button_clicked(self, widget):
        device = self.devices[self.devices_box.get_active()]

        device.open()
        self.logger("Device: {} \n".format(device.device_name.strip()))
        device.close()

    def on_start_button_clicked(self, widget):
        if self.start_button.get_label().endswith("Start"):
            try:
                device = self.devices[self.devices_box.get_active()]
                script = self.smx_file.get_script(self.get_script_selection_index())
            except Exception as e:
                self.show_mesage_box("Script Load Error", str(e), Gtk.MessageType.ERROR)
            else:
                # Start Worker
                self.worker = Worker(device, script, self.logger, self.on_finish, self.pgbar)
                self.worker.daemon = True
                self.worker.start()

                self.start_button.set_label(" Stop")
                self.start_button.set_image(Gtk.Image(stock=Gtk.STOCK_MEDIA_STOP))
                self.scan_button.set_sensitive(False)
                self.open_button.set_sensitive(False)
                self.info_button.set_sensitive(False)
                self.devices_box.set_sensitive(False)
                self.treeview.set_sensitive(False)
        else:
            # Stop Worker
            self.worker.stop()

    def on_finish(self, msg, done):
        self.logger(msg, False)
        self.start_button.set_label(" Start")
        self.start_button.set_image(Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        self.scan_button.set_sensitive(True)
        self.open_button.set_sensitive(True)
        self.treeview.set_sensitive(True)
        if done:
            self.devices_name.clear()
            self.start_button.set_sensitive(False)
        else:
            self.scan_usb()

    def on_exit_button_clicked(self, widget):
        sys.exit(0)


def main(argv):
    window = MainWindow()
    window.connect("delete-event", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main(sys.argv)
