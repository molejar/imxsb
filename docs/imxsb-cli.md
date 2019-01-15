i.MX SmartBoot Tool - CLI
=========================

Following description of i.MX SmartBoot Tool is focusing to its implementation with standard Command Line Interface (CLI).
For printing a general info of it usage just execute `imxsb-cli.py` with argument `-h` or `--help` inside shell terminal.

```sh
$ imxsb-cli.py -h

usage: imxsb-cli.py [-h] [-i] [-s INDEX] [-q] [-v] smx_file

positional arguments:
  smx_file              path to *.smx file

optional arguments:
  -h, --help            show this help message and exit
  -i, --info            print SMX file info and exit
  -s INDEX, --script INDEX
                        select script by its index
  -q, --quiet           no progressbar
  -v, --version         show program's version number and exit
```

The user guide how to create input file for i.MX SmartBoot tool is here: [SMX file](smx_file.md)

#### Print SMX file info and exit

```sh
 $ imxsb-cli.py -i example.smx

 0) InitRAMFS Boot (Boot from RAMDisk image)
 1) Network Boot 0 (Mount RootFS via NFS)
 2) Network Boot 1 (Load kernel and DTB over TFTP and mount RootFS via NFS)
```

#### Start boot

```sh
 $ imxsb-cli.py example.smx

 DEVICE: SE Blank ULT1 (0x15A2, 0x0076)

 0) InitRAMFS Boot (Boot from RAMDisk image)
 1) Network Boot 0 (Mount RootFS via NFS)
 2) Network Boot 1 (Load kernel and DTB over TFTP and mount RootFS via NFS)

 Select boot script: 1

 --------------------------------------------------
 START: Network Boot 0 (Mount RootFS via NFS)
 --------------------------------------------------
 1/7) Write DCD from: ddr3 (436.0 B)
 2/7) Write image: imx7d_sdb/u-boot.imx (467.0 kiB)
 3/7) Skip DCD segments inside u-boot image
 4/7) Write image: uboot_script0 (500.0 B)
 5/7) Write image: imx7d_sdb/zImage (6.4 MiB)
 6/7) Write image: imx7d_sdb/imx7d-sdb.dtb (46.0 kiB)
 7/7) Boot from address: 0x877FF400
 --------------------------------------------------
```