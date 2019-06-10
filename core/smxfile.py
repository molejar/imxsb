# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import os
import imx
import yaml
import jinja2

# internals
from .segments import DatSegFDT, DatSegDCD, DatSegIMX2, DatSegIMX2B, DatSegIMX3, DatSegRAW, DatSegUBI, \
                      DatSegUBX, DatSegUBT


def fmt_size(num, kibibyte=True):
    base, suffix = [(1000., 'B'), (1024., 'iB')][kibibyte]
    for x in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < num < base:
            break
        num /= base
    return "{0:3.1f} {1:s}".format(num, x)


class ParseError(Exception):
    """Thrown when parsing a file fails"""
    pass


class SmxScript(object):

    def __init__(self, name, description, smx_data=None):
        """ Init SmxScript
        :param name: Data segments name
        :param description:
        :param smx_data:
        :return object
        """
        assert isinstance(name, str)
        assert isinstance(description, str)

        self.name = name
        self.description = description
        self._cmds = []
        self._loaded = False
        if smx_data is not None:
            self.init(smx_data)

    def __str__(self):
        """ String representation """
        return "{} ({})".format(self.name, self.description)

    def __len__(self):
        """ Count of commands """
        return len(self._cmds)

    def __getitem__(self, key):
        """ Get command by index """
        return self._cmds[key]

    def __iter__(self):
        return self._cmds.__iter__()

    def info(self):
        pass

    def set_pgrange(self, value):
        if not self._loaded:
            raise Exception()
        data_cnt = 0
        data_size = 0
        for cmd in self._cmds:
            if 'data' in cmd.keys():
                data_cnt += 1
                data_size += len(cmd['data'])

        steps = int(value / 100)
        point = (value - (len(self._cmds) - data_cnt) * steps) / data_size

        for cmd in self._cmds:
            if 'data' in cmd.keys():
                cmd['pg'] = int(len(cmd['data']) * point)
            else:
                cmd['pg'] = steps

    def init(self, smx_data):
        """
        :param smx_data:
        :return:
        """
        line_counter = 0

        for line in smx_data.split('\n'):
            line = line.rstrip('\0')
            line = line.lstrip(' ')
            # increment line counter
            line_counter += 1
            # ignore comments
            if not line or line.startswith('#'):
                continue
            # ...
            line = line.split()
            cmd = {'name': line[0].lower()}
            # ...
            if cmd['name'] == 'sdcd':
                cmd['description'] = 'Skip DCD segments inside u-boot image'

            elif cmd['name'] == 'jrun':
                if len(line) < 2:
                    raise Exception("Command JRUN require one argument")
                try:
                    cmd['address'] = int(line[1], 0)
                    cmd['description'] = "Start from address: 0x{:08X}".format(cmd['address'])
                except ValueError:
                    cmd['data_segment'] = line[1]

            elif cmd['name'] == 'wreg':
                if len(line) < 4:
                    raise Exception("Command WREG require three arguments")
                try:
                    cmd['bytes'] = int(line[1], 10)
                except ValueError:
                    raise Exception("bytes")
                try:
                    cmd['address'] = int(line[2], 0)
                except ValueError:
                    raise Exception("address")
                try:
                    cmd['value'] = int(line[3], 0)
                except ValueError:
                    raise Exception("value")

                cmd['description'] = "Write {}bit value: 0x{:X} at address: 0x{:08X}".format(cmd['bytes'],
                                                                                             cmd['value'],
                                                                                             cmd['address'])
            elif cmd['name'] in ('wdcd', 'wimg'):
                if len(line) < 2:
                    raise Exception("Command {} require at least one argument".format(line[0]))

                cmd['data_segment'] = line[1]

                name, ext = cmd['data_segment'].split('.')
                if '/' in ext:
                    ext = ext.split('/')
                else:
                    ext = [ext]

                if cmd['name'] == 'wdcd' and ext[0].lower() != DatSegDCD.MARK:
                    if len(line) < 3:
                        raise Exception("Command {} must have specified address value ".format(line[0]))

                if len(line) > 2:
                    try:
                        cmd['address'] = int(line[2], 0)
                    except ValueError:
                        raise Exception("address")
            else:
                raise Exception("Not a valid command: {}".format(cmd['name']))

            self._cmds.append(cmd)

    def load(self, db):
        """
        :param db:
        :return:
        """
        for cmd in self._cmds:

            if cmd['name'] in ('sdcd', 'wreg'):
                continue

            if cmd['name'] == 'jrun' and 'address' in cmd:
                continue

            name, ext = cmd['data_segment'].split('.')
            if '/' in ext:
                ext = ext.split('/')
            else:
                ext = [ext]

            image = None
            for item in db:
                if name == item.name and ext[0].lower() == item.MARK:
                    image = item
                    break

            if image is None:
                raise Exception("...")

            if 'address' not in cmd:
                cmd['address'] = image.address

            if cmd['name'] == 'jrun':
                cmd['description'] = "Boot from address: 0x{:08X}".format(cmd['address'])

            if cmd['name'] == 'wdcd':
                if ext[0].lower() in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                    cmd['data'] = image.dcd
                else:
                    cmd['data'] = image.data
                cmd['description'] = 'Write DCD from: {} ({})'.format(image.name if image.path is None else image.path,
                                                                      fmt_size(len(cmd['data'])))
            if cmd['name'] == 'wimg':
                cmd['data'] = image.data
                cmd['description'] = 'Write image: {} ({})'.format(image.name if image.path is None else image.path,
                                                                   fmt_size(len(cmd['data'])))
        self._loaded = True


class SmxFile(object):

    data_segments = {
        DatSegDCD.MARK: DatSegDCD,
        DatSegFDT.MARK: DatSegFDT,
        DatSegIMX2.MARK: DatSegIMX2,
        DatSegIMX2B.MARK: DatSegIMX2B,
        DatSegIMX3.MARK: DatSegIMX3,
        DatSegUBI.MARK: DatSegUBI,
        DatSegUBX.MARK: DatSegUBX,
        DatSegUBT.MARK: DatSegUBT,
        DatSegRAW.MARK: DatSegRAW
    }

    @property
    def name(self):
        return self._name

    @property
    def platform(self):
        return self._platform

    @property
    def description(self):
        return self._description

    @property
    def scripts(self):
        return self._body

    @property
    def path(self):
        return self._path

    def __init__(self, file=None, auto_load=False):
        # private
        self._name = ""
        self._description = ""
        self._platform = None
        self._path = None
        self._data = []
        self._body = []
        # init
        if file is not None:
            self.open(file, auto_load)

    def info(self):
        pass

    def open(self, file, auto_load=False):
        """ Open core file
        :param file:
        :param auto_load:
        :return
        """
        assert isinstance(file, str)

        # open core file
        with open(file, 'r') as f:
            txt_data = f.read()

        # load core file
        smx_data = yaml.load(txt_data)
        if 'VARS' in smx_data:
            var_data = smx_data['VARS']
            txt_data = jinja2.Template(txt_data).render(var_data)
            smx_data = yaml.load(txt_data)

        # check if all variables have been defined
        # if re.search("\{\{.*x.*\}\}", text_data) is not None:
        #   raise Exception("Some variables are not defined !")

        # set absolute path to core file
        self._path = os.path.abspath(os.path.dirname(file))

        # validate segments in core file
        if 'HEAD' not in smx_data:
            raise Exception("HEAD segments doesn't exist inside file: %s" % file)
        if 'DATA' not in smx_data:
            raise Exception("DATA segments doesn't exist inside file: %s" % file)
        if 'BODY' not in smx_data:
            raise Exception("BODY segments doesn't exist inside file: %s" % file)

        # parse header segments
        if "CHIP" not in smx_data['HEAD']:
            raise Exception("CHIP not defined in HEAD segments")
        if smx_data['HEAD']['CHIP'] not in imx.sdp.supported_devices():
            raise Exception("Device type not supported !")
        self._name = smx_data['HEAD']['NAME'] if 'NAME' in smx_data['HEAD'] else ""
        self._description = smx_data['HEAD']['DESC'] if 'DESC' in smx_data['HEAD'] else ""
        self._platform = smx_data['HEAD']['CHIP']

        # clear all data
        self._data = []
        self._body = []

        # parse data segments
        for full_name, data in smx_data['DATA'].items():
            try:
                item_name, item_type = full_name.split('.')
            except ValueError:
                raise Exception("Not supported data segments format: {}".format(full_name))
            # case tolerant type
            item_type = item_type.lower()
            if item_type not in self.data_segments.keys():
                raise Exception("Not supported data segments type: {}".format(item_type))

            self._data.append(self.data_segments[item_type](item_name, data))

        # parse scripts
        for item in smx_data['BODY']:
            if 'NAME' not in item.keys():
                raise Exception()
            if 'DESC' not in item.keys():
                item['DESC'] = ""

            self._body.append(SmxScript(item['NAME'], item['DESC'], item['CMDS']))

        if auto_load:
            self.load()

    def load(self):
        # load simple data segments
        for item in self._data:
            if item.MARK not in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self._data, self._path)

        # load complex data segments which can include simple data segments
        for item in self._data:
            if item.MARK in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self._data, self._path)

    def get_script(self, index):
        script = self._body[index]
        script.load(self._data)
        return script
