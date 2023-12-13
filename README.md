# Script for trimming UPF potentials


This repository contains the script used for trimming UPF files, used in [Bosoni, E., Beal, L., Bercx, M. et al. How to verify the precision of density-functional-theory implementations via reproducible and universal workflows. Nat Rev Phys (2023)](https://www.nature.com/articles/s42254-023-00655-3) paper. The original UPF files and trimmmed UPF files are also included for reference.
Trimming is need as Abinit discards data beyond a certain radius which is harded-coded into the code. This is because long-range data are not relavent and may contain errors.  Other code may handle this differently when reading the same pseudopotential, e.g. using a different radius (QE) or use the data as provided (CASTEP). 
Hence, to make all codes ending up with the same set of pseudopotential data without any code modification, we choose to trim the data in the the UPF files instead.

## Usage

A commandline interface is provided for timming ALL UFP pseudopotentials from a folder:


```
$ python upftrim.py --help
usage: upftrim [-h] [--mesh MESH] [--verbose] indir outdir

Tool for trimming UPF files down to a certain mesh size

positional arguments:
  indir
  outdir

optional arguments:
  -h, --help   show this help message and exit
  --mesh MESH
  --verbose
```

The only parameter needed is `--mesh` which defines the upper limit of the mesh size. Data beyond this limit are be discarded.
The value of `600` is used for the work mentioned above which corresponds to 6 bhor.
