# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from imx.img import SegDCD
from .base import DatSegBase, get_full_path


class InitErrorDCD(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegDCD(DatSegBase):
    """ Data segments class for Device Configuration Data

        <NAME>.dcd:
            DESC: srt
            ADDR: int
            DATA: str or bytes (required)

        <NAME>.dcd:
            DESC: srt
            ADDR: int
            FILE: path (required)
    """

    MARK = 'dcd'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self._txt_data = None
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize DCD segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorDCD("{}: Property name must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorDCD("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorDCD("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'DATA':
                if not isinstance(val, str):
                    raise InitErrorDCD("{}/DATA: Not supported value type !".format(self.full_name))
                self._txt_data = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorDCD("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            else:
                raise InitErrorDCD("{}: Not supported property name \"{}\" !".format(self.full_name, key))

        if self.path is None and self._txt_data is None:
            raise InitErrorDCD("{}: FILE or DATA property must be defined !".format(self.full_name))

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if self.path is None:
            dcd_obj = SegDCD.parse_txt(self._txt_data)
        else:
            file_path = get_full_path(root_path, self.path)[0]
            if file_path.endswith(".txt"):
                with open(file_path, 'r') as f:
                    dcd_obj = SegDCD.parse_txt(f.read())
            else:
                with open(file_path, 'rb') as f:
                    dcd_obj = SegDCD.parse(f.read())

        self.data = dcd_obj.export()
