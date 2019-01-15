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

# SmartBoot Core module
import core

# qt module
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMessageBox, QFileDialog, QVBoxLayout, QHBoxLayout, \
                            QPushButton, QComboBox, QSizePolicy, QLineEdit, QSplitter, QFrame, QListWidget, \
                            QAbstractScrollArea, QTextEdit, QProgressBar, QSpacerItem

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
class Worker(QThread):

    logger = pyqtSignal(str, int)
    finish = pyqtSignal(str, bool)
    prgbar = pyqtSignal(int)

    def __init__(self, device, script):
        super().__init__()
        self._device = device
        self._script = script
        # internal variables
        self._running = False
        self._pgstp = 0
        self._pgval = 0

    def stop(self):
        self._running = False

    def progress_handler(self, level):
        self.prgbar.emit(int(self._pgval + (self._pgstp / PGRANGE) * level))
        return self._running

    def run(self):
        self._running = True
        self._script.set_pgrange(PGRANGE)
        self._device.pg_range = PGRANGE
        # start timer
        start_time = time.time()
        self.logger.emit(" START: {}".format(self._script.name), True)

        try:
            # connect target
            self._device.open(self.progress_handler)
            for cmd in self._script:

                if not self._running:
                    break

                self._pgval += self._pgstp
                self._pgstp = cmd['pg']

                # print command info
                self.logger.emit(" {} {}".format(elapsed_time(start_time), cmd['description']), False)

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

            self.prgbar.emit(PGRANGE)

        except Exception as e:
            self.finish.emit(" STOP: {}".format(str(e)), False)

        else:
            self.finish.emit(" DONE: Successfully started", True)

        finally:
            self._device.close()


# Main Window Class
class MainWindow(QFrame):

    smx_file = core.SmxFile()
    hotplug = core.HotPlug()
    devices = []
    target = None
    worker = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle('i.MX Smart-Boot Tool')
        self.setMinimumSize(600, 400)
        self.center()

        # create main box
        layout = QVBoxLayout()

        # --------------------------------------------------------------------------------------------------------------
        # Device selection drop-box with scan button
        # --------------------------------------------------------------------------------------------------------------
        box = QHBoxLayout()
        self.deviceBox = QComboBox()
        box.addWidget(self.deviceBox)

        self.scanButton = QPushButton("  Scan")
        self.scanButton.setFixedWidth(80)
        self.scanButton.setIcon(QIcon.fromTheme("view-refresh"))
        self.scanButton.clicked.connect(self.on_scan_button_clicked)
        box.addWidget(self.scanButton)
        layout.addLayout(box)

        # --------------------------------------------------------------------------------------------------------------
        # SMX File inbox with open button
        # --------------------------------------------------------------------------------------------------------------
        box = QHBoxLayout()
        self.smxEdit = QLineEdit()
        self.smxEdit.setReadOnly(True)
        box.addWidget(self.smxEdit)

        self.openButton = QPushButton(" Open")
        self.openButton.setFixedWidth(80)
        self.openButton.setIcon(QIcon.fromTheme("document-open"))
        self.openButton.clicked.connect(self.on_open_button_clicked)
        box.addWidget(self.openButton)
        layout.addLayout(box)

        # --------------------------------------------------------------------------------------------------------------
        # Body
        # --------------------------------------------------------------------------------------------------------------
        self.splitter = QSplitter()
        self.splitter.setHandleWidth(5)
        self.splitter.setMidLineWidth(0)
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.setOpaqueResize(True)
        self.splitter.setChildrenCollapsible(False)

        self.scriptsList = QListWidget(self.splitter)
        self.scriptsList.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.scriptsList.setMinimumHeight(60)

        self.textEdit = QTextEdit(self.splitter)
        self.textEdit.setReadOnly(True)
        self.textEdit.setMinimumHeight(100)
        layout.addWidget(self.splitter)

        # Progress Bar
        self.pgTask = QProgressBar()
        self.pgTask.setRange(0, PGRANGE)
        self.pgTask.setFixedHeight(16)
        self.pgTask.setTextVisible(False)
        layout.addWidget(self.pgTask)

        # --------------------------------------------------------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------------------------------------------------------
        box = QHBoxLayout()
        box.setContentsMargins(-1, 5, -1, -1)

        # About Button
        self.aboutButton = QPushButton(" About")
        self.aboutButton.setMinimumSize(100, 40)
        self.aboutButton.setIcon(QIcon.fromTheme("help-contents"))
        self.aboutButton.clicked.connect(self.on_about_button_clicked)
        box.addWidget(self.aboutButton)

        # Device Info Button
        self.devInfoButton = QPushButton(" DevInfo")
        self.devInfoButton.setEnabled(False)
        self.devInfoButton.setMinimumSize(100, 40)
        self.devInfoButton.setIcon(QIcon.fromTheme("help-about"))
        self.devInfoButton.clicked.connect(self.on_info_button_clicked)
        box.addWidget(self.devInfoButton)

        # Spacer
        box.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Start Button
        self.startButton = QPushButton(" Start")
        self.startButton.setEnabled(False)
        self.startButton.setMinimumSize(100, 40)
        self.startButton.setIcon(QIcon.fromTheme("media-playback-start"))
        self.startButton.clicked.connect(self.on_start_button_clicked)
        box.addWidget(self.startButton)

        # Start Button
        self.exitButton = QPushButton(" Exit")
        self.exitButton.setMinimumSize(100, 40)
        self.exitButton.setIcon(QIcon.fromTheme("application-exit"))
        self.exitButton.clicked.connect(self.on_exit_button_clicked)
        box.addWidget(self.exitButton)

        layout.addLayout(box)
        self.setLayout(layout)

        # USB hot-plug (Linux only)
        # self.hotplug.attach(self.scan_usb)
        # self.hotplug.start()
        # TODO: Fix USB hot-plug
        self.scan_usb()

    def center(self):
        # center point of screen
        cp = QDesktopWidget().availableGeometry().center()
        # move rectangle's center point to screen's center point
        qr = self.frameGeometry()
        qr.moveCenter(cp)
        # top left of rectangle becomes top left of window centering it
        self.move(qr.topLeft())

    ####################################################################################################################
    # Helper methods
    ####################################################################################################################
    def scan_usb(self, obj=None):
        self.devices = imx.sdp.scan_usb(self.target)
        self.deviceBox.clear()
        if self.devices:
            for dev in self.devices:
                self.deviceBox.addItem(dev.usbd.info)
            self.deviceBox.setCurrentIndex(0)
            self.deviceBox.setEnabled(True)
            self.devInfoButton.setEnabled(True)
            self.startButton.setEnabled(False if self.target is None else True)
        else:
            self.deviceBox.setEnabled(False)
            self.devInfoButton.setEnabled(False)
            self.startButton.setEnabled(False)

    def Logger(self, msg, clear):
        if clear:
            self.textEdit.clear()
        if msg:
            self.textEdit.append(msg)

    def ProgressBar(self, value):
        self.pgTask.setValue(min(value, PGRANGE))

    def ShowMesageBox(self, title, message, icon=QMessageBox.Warning):
        alert = QMessageBox()
        alert.setWindowTitle(title)
        alert.setText(message)
        alert.setIcon(icon)
        alert.exec_()

    ####################################################################################################################
    # Buttons callback methods
    ####################################################################################################################
    def on_scan_button_clicked(self):
        self.scan_usb()

    def on_open_button_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Choose a SmartBoot script file", BASEDIR,
                                                  "i.MX SmartBoot Files (*.smx)", options=options)
        if fileName:
            self.smxEdit.clear()
            self.scriptsList.clear()
            try:
                self.smx_file.open(fileName, True)
            except Exception as e:
                self.ShowMesageBox("SMX File Open Error", str(e), QMessageBox.Warning)
                self.target = None
                self.startButton.setEnabled(False)
            else:
                self.target = self.smx_file.platform
                self.smxEdit.setText(fileName)
                for i, item in enumerate(self.smx_file.scripts):
                    self.scriptsList.addItem("{}.  {}  ({})".format(i, item.name, item.description))
                self.scriptsList.setCurrentRow(0)
                self.scriptsList.adjustSize()
                # update usb device list
                self.scan_usb()

    def on_about_button_clicked(self):
        text = "<b>i.MX SmartBoot Tool</b> v {}".format(core.__version__)
        text += "<p>{}".format(core.DESCRIPTION)
        text += "<p>Copyright &copy; 2018 Martin Olejar."
        text += "<p>License: {}".format(core.__license__)
        text += "<p>Sources: <a href='https://github.com/molejar/imxsb'>https://github.com/molejar/imxsb</a>"
        QMessageBox.about(self, "About", text)

    def on_info_button_clicked(self):
        device = self.devices[self.deviceBox.currentIndex()]
        device.open()
        self.textEdit.clear()
        self.textEdit.append("Device: {} \n".format(device.device_name))
        device.close()

    def on_start_button_clicked(self):
        if self.startButton.text().endswith("Start"):
            try:
                device = self.devices[self.deviceBox.currentIndex()]
                script = self.smx_file.get_script(self.scriptsList.currentRow())
            except Exception as e:
                self.ShowMesageBox("Script Load Error", str(e), QMessageBox.Warning)
            else:
                # Start Worker
                self.worker = Worker(device, script)
                self.worker.logger.connect(self.Logger)
                self.worker.finish.connect(self.on_finish)
                self.worker.prgbar.connect(self.ProgressBar)
                self.worker.daemon = True
                self.worker.start()

                self.startButton.setText(" Stop")
                self.startButton.setIcon(QIcon.fromTheme("media-playback-stop"))
                self.scanButton.setEnabled(False)
                self.openButton.setEnabled(False)
                self.deviceBox.setEnabled(False)
                self.scriptsList.setEnabled(False)
                self.devInfoButton.setEnabled(False)
        else:
            # Stop Worker
            self.worker.stop()

    def on_finish(self, msg, done):
        self.textEdit.append(msg)
        self.startButton.setText(" Start")
        self.startButton.setIcon(QIcon.fromTheme("media-playback-start"))
        self.scanButton.setEnabled(True)
        self.scriptsList.setEnabled(True)
        self.openButton.setEnabled(True)
        if done:
            self.deviceBox.clear()
            self.startButton.setEnabled(False)
        else:
            self.scan_usb()

    def on_exit_button_clicked(self):
        self.close()


def main(argv):
    app = QApplication(argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main(sys.argv)
