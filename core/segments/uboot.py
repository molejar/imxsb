# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import uboot
from .base import DatSegBase, get_full_path


class InitErrorUBI(Exception):
    """Thrown when parsing a file fails"""
    pass


class InitErrorUBX(Exception):
    """Thrown when parsing a file fails"""
    pass


class InitErrorUBT(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegUBI(DatSegBase):
    """ Data segments class for old U-Boot main image

        <NAME>.ubi:
            DESC: srt
            ADDR: int
            FILE: path (required)
            MODE: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            MARK: str (default: 'bootcmd=')
            EVAL: str (required if MODE is not disabled)
    """

    MARK = 'ubi'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self.address = None
        self._eval = None
        self._mode = 'disabled'
        self._mark = 'bootcmd='
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize UBI segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorUBI("{}: Key must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorUBI("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorUBI("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorUBI("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            elif key == 'MODE':
                if not isinstance(val, str):
                    raise InitErrorUBI("{}/MODE: Value must be a string !".format(self.full_name))
                val = val.lower()
                if val not in ('disabled', 'merge', 'replace'):
                    raise InitErrorUBI("{}/MODE: Not supported value \"{}\"".format(self.full_name, val))
                self._mode = val
            elif key == 'MARK':
                if not isinstance(val, str):
                    raise InitErrorUBI("{}/MARK: Value must be a string !".format(self.full_name))
                self._mark = val
            elif key == 'EVAL':
                if not isinstance(val, str):
                    raise InitErrorUBI("{}/EVAL: Value must be a string !".format(self.full_name))
                self._eval = val
            else:
                raise InitErrorUBI("{}: Not supported attribute \"{}\"".format(self.full_name, key))

        if self.path is None:
            raise InitErrorUBI("{}/FILE: Value must be defined !".format(self.full_name))
        if self._mode != 'disabled' and self._eval is None:
            raise InitErrorUBI("{}/EVAL: Value must be defined !".format(self.full_name))

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if self._mode == 'disabled':
            with open(get_full_path(root_path, self.path)[0], 'rb') as f:
                self.data = f.read()
        else:
            img_obj = uboot.EnvImgOld(self._mark)
            img_obj.open_img(get_full_path(root_path, self.path)[0])
            if self._mode == 'replace':
                img_obj.clear()
            img_obj.load(self._eval)

            self.data = img_obj.export_img()


class DatSegUBX(DatSegBase):
    """ Data segments class for old U-Boot executable image

        <NAME>.uexe:
            DESC: srt
            ADDR: int
            HEAD:
                nane: str(32)
                eaddr: int (default: 0)
                laddr: int (default: 0)
                type:  "standalone", "firmware", "script", "multi" (default: "firmware")
                arch: "alpha", "arm", "x86", ... (default: "arm")
                os: "openbsd", "netbsd", "freebsd", "bsd4", "linux", ... (default: "linux")
                compress: "none", "gzip", "bzip2", "lzma", "lzo", "lz4" (default: "none")
            <DATA or PATH>: str (required)
    """

    MARK = 'ubx'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self._txt_data = None
        self._header = {}
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize UBX segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorUBX("{}: Key must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorUBX("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorUBX("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'FILE':
                if not isinstance(val, (str, list)):
                    raise InitErrorUBX("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            elif key == 'DATA':
                if not isinstance(val, str):
                    raise InitErrorUBX("{}/DATA: Value must be a string !".format(self.full_name))
                self._txt_data = val
            elif key == 'HEAD':
                if not isinstance(val, dict):
                    raise InitErrorUBX("{}/HEAD: Not a dictionary !".format(self.full_name))
                for k, v in val.items():
                    if not isinstance(k, str):
                        raise InitErrorUBX("{}/HEAD: Not supported key: {}".format(self.full_name, k))
                    self._header[k.lower()] = v
            else:
                raise InitErrorUBX("{}: Not supported attribute \"{}\"".format(self.full_name, key))

        if self.path is None and self._txt_data is None:
            raise InitErrorUBX("{} FILE or DATA attribute must be defined !".format(self.full_name))

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        img_obj = uboot.new_img(**self._header)
        if img_obj.header.image_type == uboot.EnumImageType.FIRMWARE:
            with open(get_full_path(root_path, self.path)[0], 'rb') as f:
                img_obj.data = f.read()
        elif img_obj.header.image_type == uboot.EnumImageType.SCRIPT:
            if self.path is None:
                img_obj.load(self._txt_data)
            else:
                with open(get_full_path(root_path, self.path)[0], 'r') as f:
                    img_obj.load(f.read())
        elif img_obj.header.image_type == uboot.EnumImageType.MULTI:
            for img_path in get_full_path(root_path, self.path):
                with open(img_path, 'rb') as f:
                    img_obj.append(uboot.parse_img(f.read()))
        else:
            with open(get_full_path(root_path, self.path)[0], 'rb') as f:
                img_obj.data = f.read()

        self.data = img_obj.export()


class DatSegUBT(DatSegBase):
    """ Data segments class for new FDT U-Boot image

        <NAME>.ubt:
            DESC: srt
            ADDR: int
            FILE: path (required)

        <NAME>.ubt:
            DESC: srt
            ADDR: int
            DATA: str (required)
    """

    MARK = 'ubt'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self._its_data = None
        if smx_data is not None:
            self.init(smx_data)

    def init(self, data):
        """ Initialize UBT segments
        :param data: ...
        """
        assert isinstance(data, dict)

        for key, val in data.items():
            if not isinstance(key, str):
                raise InitErrorUBT()
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorUBT()
                self.description = val
            elif key == 'ADDR':
                if not isinstance(val, int):
                    try:
                        self.address = int(val, 0)
                    except Exception as ex:
                        raise InitErrorUBT("{}/ADDR: {}".format(self.full_name, str(ex)))
                else:
                    self.address = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorUBT()
                self.path = val
            elif key == 'DATA':
                if not isinstance(val, str):
                    raise InitErrorUBT()
                self._its_data = val
            else:
                raise InitErrorUBT()

        if self.path is None and self._its_data is None:
            raise InitErrorUBT()

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

