#!/usr/bin/env python

# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import sys
import imx
import time
import argparse
# SmartBoot Core module
import core


########################################################################################################################
# Helper class
########################################################################################################################
class ProgressBar(object):

    def __init__(self, range=100, nbars=30, prefix='', file=sys.stderr):
        self.file = file
        self.total = range
        self.nbars = nbars
        self.prefix = prefix
        self.disabled = False
        # private
        self._last_printed_len = 0
        self._start_time = 0
        self._started = False

    def _print_status(self, s):
        self.file.write('\r' + s + ' ' * max(self._last_printed_len - len(s), 0))
        self.file.flush()
        self._last_printed_len = len(s)

    def _format_interval(self, t):
        mins, s = divmod(t, 60)
        _, m = divmod(mins, 60)
        return '%02d:%06.3f' % (int(m), s)

    def _format_meter(self, value, elapsed_time):
        frac = float(value) / self.total
        bar_length = int(frac * self.nbars)
        bar = '#' * bar_length + '-' * (self.nbars - bar_length)
        return '[%s] %3d%% (%s) ' % (bar, frac * 100, self._format_interval(elapsed_time))

    def start(self):
        if not self.disabled:
            self._print_status(self.prefix + self._format_meter(0, 0))
            self._start_time = time.time()
            self._started = True

    def update(self, value):
        if not self.disabled and self._started:
            self._print_status(self.prefix + self._format_meter(value, time.time() - self._start_time))

    def finish(self, leave=False):
        if not self.disabled:
            if not leave:
                self._print_status('')
                sys.stdout.write('\r')
            else:
                self.update(self.total)
                self.file.write('\n')

            self._started = False


########################################################################################################################
# main function
########################################################################################################################
def main():

    # application error code
    error_code = 1

    # cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('smx_file', help='path to *.smx file')
    parser.add_argument('-i', '--info', dest='print_info', action='store_true',
                        help='print SMX file info and exit')
    parser.add_argument('-s', '--script', dest='index', type=int, default=100,
                        help='select script by its index')
    parser.add_argument('-p', '--progress', dest='show_progress', action='store_true',
                        help='show progressbar')
    parser.add_argument('-v', '--version', action='version', version=core.__version__)

    results = parser.parse_args()

    try:
        # open and load smx file
        smx = core.SmxFile(results.smx_file, True)
    except Exception as e:
        print("\n ERROR: %s" % str(e))
        sys.exit(error_code)

    if results.print_info:
        print("\n Name: %s\n Desc: %s\n Chip: %s\n" % (smx.name, smx.description, smx.platform))
        print(' ' + '-' * 50)
        num = 0
        for script in smx.scripts:
            print(" %d) %s (%s)" % (num, script.name, script.description))
            num += 1
        print(' ' + '-' * 50)
    else:
        error_flg = False
        error_msg = ""
        script_index = results.index
        device_index = 0

        # scan for USB target
        devices = imx.sdp.scan_usb(smx.platform)
        if not devices:
            print("\n No {} board connected !".format(smx.platform))
            sys.exit(error_code)

        if len(devices) > 1:
            i = 0
            print('')
            for dev in devices:
                print(" %d) %s" % (i, dev.usbd.info))
                i += 1
            print("\n Select target device: ", end='', flush=True)
            c = input()
            print()
            device_index = int(c, 10)

        print("\n DEVICE: %s\n" % devices[device_index].usbd.info)
        flasher = devices[device_index]

        if len(smx.scripts) == 1:
            script_index = 0

        # select boot script
        if script_index > len(smx.scripts):
            num = 0
            for script in smx.scripts:
                print(" %d) %s (%s)" % (num, script.name, script.description))
                num += 1
            print("\n Select boot script: ", end='', flush=True)
            c = input()
            script_index = int(c, 10)
            print()

        bar = ProgressBar(nbars=40, prefix=' ', file=sys.stdout)

        def progress_handler(value):
            bar.update(value)
            return True

        try:
            # connect target
            if results.show_progress:
                flasher.open(progress_handler)
                flasher.pg_resolution = 20
            else:
                flasher.open()
                bar.disabled = True

            # load script
            script = smx.get_script(script_index)
            print(' ' + '-' * 50)
            print(" START: %s (%s)" % (script.name, script.description))
            print(' ' + '-' * 50)

            # execute script
            num = 1
            for cmd in script:

                # print command info
                print(" %d/%d) %s" % (num, len(script), cmd['description']))

                if cmd['name'] == 'wreg':
                    flasher.write(cmd['address'], cmd['value'], cmd['bytes'])

                elif cmd['name'] == 'wdcd':
                    bar.start()
                    flasher.write_dcd(cmd['address'], cmd['data'])
                    bar.finish()

                elif cmd['name'] == 'wimg':
                    bar.start()
                    flasher.write_file(cmd['address'], cmd['data'])
                    bar.finish()

                elif cmd['name'] == 'sdcd':
                    flasher.skip_dcd()

                elif cmd['name'] == 'jrun':
                    flasher.jump_and_run(cmd['address'])

                else:
                    raise Exception("Command: {} not supported".format(cmd['name']))

                num += 1

        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown Error !"
            error_flg = True

        finally:
            flasher.close()
            if error_flg:
                print()
            else:
                print(' ' + '-' * 50)

        if error_flg:
            print(" ERROR: %s" % error_msg)
            sys.exit(error_code)


if __name__ == '__main__':
    main()
