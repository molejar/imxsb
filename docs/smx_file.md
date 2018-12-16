i.MX SmartBoot Tool
===================

## SMX File

The SMX file is a standard text file which collect all information's about i.MX boot process: paths to images, DCD data, 
global variables, boot scripts and etc. Thanks to YAML syntax is human-readable and easy modifiable. Comments in SMX file 
start with the hash character `#` and extend to the end of the physical line. A comment may appear at the start of a line 
or following whitespace characters. The content of SMX file is split into four sections: `HEAD`, `VARS`, `DATA` and `BODY`.

#### HEAD Section:

This section contains the base information's about target device.

* **NAME** - The name of target device or evaluation board (optional)
* **DESC** - The description of target device or evaluation board (optional)
* **CHIP** - Embedded IMX processor mark: VYBRID, MX6DQP, MX6SDL, MX6SL, MX6SX, MX6UL, MX6ULL, MX6SLL, MX7SD, MX7ULP (required)

>Instead of processor mark can be used USB VID:PID of the device in string format: "0x15A2:0x0054". Useful for a new 
device which is not in list of supported devices.

Example of head section:

```
HEAD:
    NAME: MCIMX7SABRE
    DESC: Development Board Sabre SD for IMX7D
    CHIP: MX7SD
```


#### VARS Section:

Collects all variables used in `DATA` and `BODY` section. 

The syntax for defining a variable is following:

```
VARS:
    #   <name>: <value>
    OCRAM_ADDR: '0x00910000'
```

The syntax for using a variable in `DATA` or `BODY` section is following:

```
DATA:
    ddr_init.dcd:
        DESC: Device Configuration Data
        ADDR: "{{ OCRAM_ADDR }}"
        TYPE: DCD
        FILE: imx7d_sbd/dcd_micron_1gb.txt
```

#### DATA Section:

Collects all data segments which can be loaded into the target via scripts in `BODY` section. Individual data segments 
can contain a different type of data what is specified by extension in its name `<segment_name>.<data_type>`. Supported are following data types:

* **DCD** - Device configuration data
* **FDT** - Flattened device tree data (*.dtb, *.dts)
* **IMX2** - Vybrid, i.MX6 and i.MX7 boot image (*.imx)
* **IMX2B** - i.MX8M boot image (*.imx)
* **IMX3** - i.MX8DM, i.MX8QM and i.MX8QXP boot image (*.imx)
* **UBI** - U-Boot main image (*.img, *.bin)
* **UBX** - Old format of U-Boot executable image (script, firmware, ...)
* **UBT** - New format of U-Boot executable image based on FDT (script, firmware, ...)
* **RAW** - Binary raw image (*.*)

If attribute `TYPE` is not defined the data segments will be processing as binary data (`TYPE: BIN`). Other attributes 
common for all data segments are:

* **DESC** - The description of data segments (optional)
* **ADDR** - The absolute address inside SoC OCT or DDR memory (optional)
* **DATA or FILE** - The data itself or path to image (required)

>Attribute `ADDR` is optional because can be specified as second argument in the command from `BODY` section. The address
value must be defined in some of this two places. If is defined on both then the value from the command will be taken. 


##### Device configuration data segment (DCD)

This data segments contains a data which generally initialize the SoC periphery for DDR memory. More details about DCD 
are in reference manual of selected IMX device. The data itself can be specified as binary file or text string/file. The 
text format of DCD data is described here: [imxim](imxim.md)

Example of *DCD* data segments in binary and text format:

```
DATA:
    ddr_init_bin.dcd:
        DESC: Device Configuration Data
        ADDR: 0x00910000
        FILE: imx7d/dcd.bin
            
    ddr_init_txt.dcd:
        DESC: Device Configuration Data
        ADDR: 0x00910000
        DATA: |
            # DDR init
            WriteValue    4 0x30340004 0x4F400005
            WriteValue    4 0x30391000 0x00000002
            WriteValue    4 0x307A0000 0x01040001
            ...
```

##### Flattened device tree data segment (FDT)

This data segments cover device tree data in readable text format or binary blob format.   

Optional attributes:

* **MODE** - Data insert mode: disabled or merge (optional)
* **DATA** - This attribute can be used for customizing loaded *.dtb or *.dts via `FILE` attribute. Its content will be
merged with loaded data if `MODE: merge`

Example of *FDT* data segments:

```
    kernel_dtb.fdt:
        DESC: Device Tree Blob
        ADDR: 0x83000000
        FILE: imx7d/imx7d-sdb.dtb
        # insert mode (disabled or merge)
        MODE: merge
        # modifications in loaded file
        DATA: |
            // Add support for M4 core
            / {
                memory {
                    linux,usable-memory = <0x80000000 0x1FF00000 0xA0000000 0x1FF00000>;
                };
```

##### Vybrid, i.MX6 and i.MX7 boot image data segment (IMX2)

This data segments represent a complete boot image for Vybrid, i.MX6 and i.MX7 device which at least consist of DCD
and UBI images. The data for it can be specified as path to a standalone file or can be created from others segments.

Optional attributes for IMX2 data segments based on standalone file (U-Boot IMX image):

* **MODE** - Environment variables insert mode: disabled, merge or replace (optional)
* **MARK** - Environment variables start mark in u-boot image (default: 'bootdelay=')
* **EVAL** - Environment variables itself

Example of *IMX2* data segments:

```
DATA:
    uboot_file.imx2:
        DESC: U-Boot Image
        FILE: imx7d/u-boot.imx
        # Environment variables insert mode (disabled, merge or replace)
        MODE: merge
        # Environment variables start mark in u-boot image
        MARK: bootcmd=
        # Environment variables
        EVAL: |
            bootdelay = 0
            bootcmd = echo Running bootscript ...; source 0x83100000
            
    uboot_image.imx2:
        NAME: U-Boot Image
        DATA:
            STADDR: 0x877FF000
            OFFSET: 0x400
            DCDSEG: ddr_init_txt.dcd
            APPSEG: uboot_main_image.ubi
```

##### U-Boot main image data segment (UBI)

This data segments cover a raw U-Boot image without IVT, DCD and other parts which are included in i.MX image. Therefore
it can not be loaded into target directly but can be used for creation of IMX2, IMX2B and IMX3 data segments.

Optional attributes:

* **MODE** - Environment variables insert mode: disabled, merge or replace (optional)
* **MARK** - Environment variables start mark in u-boot image (default: 'bootdelay=')
* **EVAL** - Environment variables itself

Example of *UBI* data segments:

```
DATA:
    uboot_main_image.ubi:
        DESC: U-Boot Raw Image
        FILE: imx7d/u-boot.img
        # Environment variables insert mode (disabled, merge or replace)
        MODE: merge
        # Environment variables start mark in u-boot image
        MARK: bootcmd=
        # Environment variables
        EVAL: |
            bootdelay = 0
            bootcmd = echo Running bootscript ...; source 0x83100000
```

##### U-Boot executable image data segment (UBX)

This data segments cover a data which can be executed from U-Boot environment. Format of input data depends on image type
which is defined by `HEAD` attribute.

All HEAD attributes:

* **nane**     - Image name in 32 chars (default: "-")
* **eaddr**    - Entry address value (default: 0x00000000)
* **laddr**    - Load address value (default: 0x00000000)
* **image**    - Image type: "standalone", "firmware", "script", "multi" (default: "firmware")
* **arch**     - Architecture type: "alpha", "arm", "x86", ... (default: "arm")
* **os**       - OS type: "openbsd", "netbsd", "freebsd", "bsd4", "linux", ... (default: "linux")
* **compress** - Compression type: "none", "gzip", "bzip2", "lzma", "lzo", "lz4" (default: "none")



Example of *UBX* data segments:

```
DATA:      
    uboot_firmware.ubx:
        DESC: U-Boot FW
        ADDR: 0x83100000
        FILE: imx7d/u-boot.bin
                 
    uboot_script.ubx:
        DESC: NetBoot Script
        ADDR: 0x83100000
        HEAD:
            image: script
        DATA: |
            echo '>> Network Boot ...'
            setenv autoload 'no'
            dhcp
            ...
```

##### Binary raw image data segment (RAW)

This data segments is covering all images which are loaded into target as binary blob, like: kernel, initramfs, ...

Example of *RAW* data segments:

```
DATA:
    kernel_image.raw:
        DESC: Kernel Image
        ADDR: 0x80800000
        FILE: imx7d/zImage
```

#### BODY Section:

Collects all boot options as small scripts based on following commands:

* **wreg** *BYTES ADDRESS VALUE* - Write specified value into register at specified address.
* **wdcd** *DCD_DATA [ADDRESS]* - Write device configuration data into target device OC memory.
* **wimg** *IMG_DATA [ADDRESS]* - Write image into target device OC or DDR memory
* **sdcd** - Skip DCD content from loaded U-Boot image.
* **jrun** *ADDRESS or IMX_IMAGE* - Jump to specified address and run.

Description of arguments

* *BYTES* - The size of access into memory cell or register. Supported are three options: 1, 2 and 4 bytes.
* *ADDRESS* - The absolute address off memory cell or register inside SoC linear address space.
* *VALUE* - The value number in supported format (HEX, BIN, DEC or OCTA).
* *DCD_DATA* - The name of DCD segments from DATA section.
* *IMG_DATA* - The name of IMAGE segments from DATA section.

Example of boot script:

```
BODY:
    - NAME: InitRAMFS Boot
      DESC: Boot into MFG RAMDisk
      CMDS: |
        # Init DDR
        wdcd ddr_init_txt.dcd
        # Load U-Boot image
        wimg uboot_file.imx2
        # Skip DCD segment from loaded U-Boot image
        sdcd
        # Load kernel image
        wimg kernel_image.raw
        # Load device tree blob
        wimg kernel_dtb.fdt
        # Load RAMDisk image
        wimg initramfs_image.raw
        # Start boot process
        jrun uboot_file.imx2
```

Here is an example of complete i.MX SmartBoot description file: [example.smx](example.smx)
