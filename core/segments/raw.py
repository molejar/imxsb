# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from .base import DatSegBase, get_full_path


class InitErrorRAW(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegRAW(DatSegBase):
    """ Data segments class for raw binary image

        <NAME>.raw:
            DESC: srt
            ADDR: int
            FILE: path (required)
    """

    MARK = 'raw'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize RAW segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorRAW("{}: Property name must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorRAW("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorRAW("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorRAW("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            else:
                raise InitErrorRAW("{}: Not supported property name \"{}\" !".format(self.full_name, key))

        if self.path is None:
            raise InitErrorRAW("{}: FILE property must be defined !".format(self.full_name))

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        with open(get_full_path(root_path, self.path)[0], 'rb') as f:
            self.data = f.read()
