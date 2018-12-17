# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import fdt
from .base import DatSegBase, get_full_path


class InitErrorFDT(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegFDT(DatSegBase):
    """ Data segments class for Device Configuration Data

        <NAME>.fdt:
            DESC: srt
            ADDR: int
            FILE: path (required)
            MODE: <'disabled' or 'merge'> default ('disabled')
            DATA: str
    """

    MARK = 'fdt'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self._dts_data = None
        self._mode = 'disabled'
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize FDT segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorFDT("{}: Property name must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorFDT("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorFDT("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorFDT("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            elif key == 'DATA':
                if not isinstance(val, str):
                    raise InitErrorFDT("{}/DATA: Value must be a string !".format(self.full_name))
                self._dts_data = val
            elif key == 'MODE':
                if not isinstance(val, str):
                    raise InitErrorFDT("{}/MODE: Value must be a string !".format(self.full_name))
                val = val.lower()
                if val not in ('disabled', 'merge'):
                    raise InitErrorFDT("{}/MODE: Not supported value \"{}\"".format(self.full_name, val))
                self._mode = val
            else:
                raise InitErrorFDT("{}: Not supported property name \"{}\" !".format(self.full_name, key))

        if self.path is None:
            raise InitErrorFDT("{}: FILE property must be defined !".format(self.full_name))

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        file_path = get_full_path(root_path, self.path)[0]
        if file_path.endswith(".dtb"):
            with open(file_path, 'rb') as f:
                fdt_obj = fdt.parse_dtb(f.read())
        else:
            with open(file_path, 'r') as f:
                fdt_obj = fdt.parse_dts(f.read())

        if self._mode is 'merge':
            fdt_obj.merge(fdt.parse_dts(self._dts_data))

        if fdt_obj.header.version is None:
            fdt_obj.header.version = 17

        self.data = fdt_obj.to_dtb()
