# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import imx
import uboot
from .base import DatSegBase, get_data_segment, get_full_path

EXPORT_UENV_FIX = True

img_types = {
    "SCD":     imx.img.EnumAppType.SCD,
    "SCFW":    imx.img.EnumAppType.SCFW,
    "CM4-0":   imx.img.EnumAppType.M4_0,
    "CM4-1":   imx.img.EnumAppType.M4_1,
    "APP-A35": imx.img.EnumAppType.A53,
    "APP-A53": imx.img.EnumAppType.A53,
    "APP-A72": imx.img.EnumAppType.A72
}


class InitErrorIMX(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegIMX2(DatSegBase):
    """ Data segments class for i.MX6 and i.MX7 boot image

        <NAME>.imx2:
            DESC: srt
            FILE: path (required)
            MODE: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            MARK: str (default: 'bootcmd=')
            EVAL: str (required if MODE is not disabled)

        <NAME>.imx2:
            DESC: srt
            DATA:
                STADDR: int (required)
                OFFSET: int (default: 0x400)
                PLUGIN: <'yes' or 'no'> (default: 'no')
                IMGVER: int (default: 0x41)
                DCDSEG: <NAME>.DCD
                APPSEG: <NAME>.UBIN (required)
    """

    MARK = 'imx2'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self.dcd = None
        self._eval = None
        self._mode = 'disabled'
        self._mark = 'bootcmd='
        self._imx_data = {}
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize FDT segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict), "ERROR -"

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorIMX("{}: Key must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            elif key == 'MODE':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/MODE: Value must be a string !".format(self.full_name))
                val = val.lower()
                if val not in ('disabled', 'merge', 'replace'):
                    raise InitErrorIMX("{}/MODE: Not supported value \"{}\"".format(self.full_name, val))
                self._mode = val
            elif key == 'MARK':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/MARK: Value must be a string !".format(self.full_name))
                self._mark = val
            elif key == 'EVAL':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/EVAL: Value must be a string !".format(self.full_name))
                self._eval = val
            elif key == 'DATA':
                if not isinstance(val, dict):
                    raise InitErrorIMX("{}/DATA: Not a dictionary !".format(self.full_name))
                for k, v in val.items():
                    if not isinstance(k, str):
                        raise InitErrorIMX("{}/DATA: Not supported key: {}".format(self.full_name, k))
                    k = k.upper()
                    if k in ('STADDR', 'OFFSET', 'IMGVER'):
                        if not isinstance(v, int):
                            try:
                                v = int(v, 0)
                            except Exception as ex:
                                raise InitErrorIMX("{}/DATA/{}: {}".format(self.full_name, k, str(ex)))
                    elif k == 'PLUGIN':
                        if not isinstance(v, str):
                            raise InitErrorIMX("{}/DATA/{}: Value must be a string !".format(self.full_name, k))
                        v = v.lower()
                        if v not in ('yes', 'no'):
                            raise InitErrorIMX("{}/DATA/{}: Not supported value \"{}\"".format(self.full_name, k, v))
                    elif k in ('DCDSEG', 'APPSEG'):
                        if not isinstance(v, str):
                            raise InitErrorIMX("{}/DATA/{}: Value must be a string !".format(self.full_name, k))
                    else:
                        raise InitErrorIMX("{}/DATA: Not supported attribute \"{}\"".format(self.full_name, k))
                    self._imx_data[k] = v

                if 'STADDR' not in self._imx_data:
                    raise InitErrorIMX()
                if 'OFFSET' not in self._imx_data:
                    self._imx_data['OFFSET'] = 0x400
                if 'PLUGIN' not in self._imx_data:
                    self._imx_data['PLUGIN'] = 'no'
                if 'IMGVER' not in self._imx_data:
                    self._imx_data['IMGVER'] = 0x41
                if 'APPSEG' not in self._imx_data:
                    raise InitErrorIMX()

        if self.path is None and not self._imx_data:
            raise InitErrorIMX()
        if self._imx_data and ('STADDR' not in self._imx_data or 'APPSEG' not in self._imx_data):
            raise InitErrorIMX()

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if self._imx_data:
            imx_obj = imx.img.BootImg2(address=self._imx_data['STADDR'],
                                       offset=self._imx_data['OFFSET'],
                                       version=self._imx_data['IMGVER'],
                                       plugin=True if self._imx_data['PLUGIN'] == 'yes' else False)

            if 'DCDSEG' in self._imx_data:
                self.dcd = get_data_segment(db, self._imx_data['DCDSEG']).data
                imx_obj.dcd = imx.img.SegDCD.parse(self.dcd)

            imx_obj.add_image(get_data_segment(db, self._imx_data['APPSEG']))
            self.address = imx_obj.address + imx_obj.offset
            self.data = imx_obj.export()

        else:
            img_path = get_full_path(root_path, self.path)[0]
            if self._mode == 'disabled':
                with open(img_path, 'rb') as f:
                    self.data = f.read()
            else:
                env_img = uboot.EnvImgOld(self._mark)
                env_img.open_img(img_path)
                if self._mode == 'replace':
                    env_img.clear()
                env_img.load(self._eval)
                self.data = env_img.export_img()

            imx_obj = imx.img.BootImg2.parse(self.data)
            self.address = imx_obj.address + imx_obj.offset
            self.dcd = imx_obj.dcd.export()


class DatSegIMX2B(DatSegBase):
    """ Data segments class for i.MX8M and i.MX8Mm boot image

        <NAME>.imx2b:
            DESC: srt
            FILE: path (required)
            MODE: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            MARK: str (default: 'bootcmd=')
            EVAL: str
    """

    MARK = 'imx2b'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize FDT segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            pass

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)


class DatSegIMX3(DatSegBase):
    """ Data segments class for i.MX8QM, i.MX8DM and i.MX8QXP boot image

        <NAME>.imx3:
            DESC: srt
            MODE: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            MARK: str (default: 'bootcmd=')
            EVAL: str (required if MODE not disabled)
            FILE: path (required)

        <NAME>.imx3:
            DESC: srt
            MODE: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            MARK: str (default: 'bootcmd=')
            EVAL: str (required if MODE is not disabled)
            DATA:
                STADDR: int (required)
                OFFSET: int (default: 0x400)
                IMGVER: int (default: 0x43)
                DCDSEG: <NAME>.DCD
                IMAGES: list
                    - TYPE: <'SCD', 'SCFW', 'CM4-0', 'CM4-1', 'APP-A35', 'APP-A53' or 'APP-A72'>
                      ADDR: int
                      FILE: path (required)
    """

    MARK = 'imx3'

    def __init__(self, name, smx_data=None):
        super().__init__(name)
        self.dcd = None
        self._eval = None
        self._mode = 'disabled'
        self._mark = 'bootcmd='
        self._imx_data = {}
        if smx_data is not None:
            self.init(smx_data)

    def init(self, smx_data):
        """ Initialize FDT segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        for key, val in smx_data.items():
            if not isinstance(key, str):
                raise InitErrorIMX("{}: Key must be a string !".format(self.full_name))
            key = key.upper()
            if key == 'DESC':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/DESC: Value must be a string !".format(self.full_name))
                self.description = val
            elif key == 'FILE':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/FILE: Value must be a string !".format(self.full_name))
                self.path = val
            elif key == 'MODE':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/MODE: Value must be a string !".format(self.full_name))
                val = val.lower()
                if val not in ('disabled', 'merge', 'replace'):
                    raise InitErrorIMX("{}/MODE: Not supported value \"{}\"".format(self.full_name, val))
                self._mode = val
            elif key == 'MARK':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/MARK: Value must be a string !".format(self.full_name))
                self._mark = val
            elif key == 'EVAL':
                if not isinstance(val, str):
                    raise InitErrorIMX("{}/EVAL: Value must be a string !".format(self.full_name))
                self._eval = val
            elif key == 'DATA':
                if not isinstance(val, dict):
                    raise InitErrorIMX("{}/DATA: Not a dictionary !".format(self.full_name))
                for k, v in val.items():
                    if not isinstance(k, str):
                        raise InitErrorIMX("{}/DATA: Not supported key: {}".format(self.full_name, k))
                    k = k.upper()
                    if k in ('STADDR', 'OFFSET', 'IMGVER'):
                        if not isinstance(v, int):
                            try:
                                v = int(v, 0)
                            except Exception as ex:
                                raise InitErrorIMX("{}/DATA/{}: {}".format(self.full_name, k, str(ex)))
                    elif k == 'DCDSEG':
                        if not isinstance(v, str):
                            raise InitErrorIMX("{}/DATA/{}: Value must be a string !".format(self.full_name, k))
                    elif k == 'IMAGES':
                        if not isinstance(v, dict):
                            raise InitErrorIMX("{}/DATA/{}: Value must be a string !".format(self.full_name, k))
                        # TODO: Add validation for images
                    else:
                        raise InitErrorIMX("{}/DATA: Not supported attribute \"{}\"".format(self.full_name, k))
                    self._imx_data[k] = v
                # ...
                if 'STADDR' not in self._imx_data:
                    raise InitErrorIMX()
                if 'OFFSET' not in self._imx_data:
                    self._imx_data['OFFSET'] = 0x400
                if 'IMGVER' not in self._imx_data:
                    self._imx_data['IMGVER'] = 0x43

        if self.path is None and not self._imx_data:
            raise InitErrorIMX()

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list), ""
        assert isinstance(root_path, str), ""

        if self._imx_data:
            imx_obj = imx.img.BootImg3b(address=self._imx_data['STADDR'],
                                        offset=self._imx_data['OFFSET'],
                                        version=self._imx_data['IMGVER'])

            if 'DCDSEG' in self._imx_data:
                self.dcd = get_data_segment(db, self._imx_data['DCDSEG']).data
                imx_obj.dcd = imx.img.SegDCD.parse(self.dcd)

            for image in self._imx_data['IMAGES']:
                if image['TYPE'] not in img_types.keys():
                    raise Exception()
                address = image['ADDR']
                if not isinstance(address, int):
                    try:
                        address = int(address, 0)
                    except Exception as ex:
                        raise InitErrorIMX('{}'.format(str(ex)))
                with open(get_full_path(root_path, image['FILE'])[0], 'rb') as f:
                    imx_obj.add_image(f.read(), img_types[image['TYPE']], address)

            self.address = imx_obj.address + imx_obj.offset
            self.data = imx_obj.export()

        else:
            img_path = get_full_path(root_path, self.path)[0]
            if self._mode == 'disabled':
                with open(img_path, 'rb') as f:
                    self.data = f.read()
            else:
                env_img = uboot.EnvImgOld(self._mark)
                env_img.open_img(img_path)
                if self._mode == 'replace':
                    env_img.clear()
                env_img.load(self._eval)
                self.data = env_img.export_img()

            imx_obj = imx.img.BootImg3b.parse(self.data)
            self.address = imx_obj.address + imx_obj.offset
            self.dcd = imx_obj.dcd.export()
