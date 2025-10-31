---
jupyter:
  jupytext:
    cell_metadata_filter: -all
    formats: .jupytext-sync-ipynb//ipynb,md
    main_language: python
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.17.3
---

# Setup

Once you have [installed the package and set up your profile](index.md#installation), you still need to tell AiiDA:

1. Which computer to run on.
2. What VASP code you want to run.
3. Where to find the VASP pseudopotentials.

These instructions show you exactly how to do that.
First we'll import some tools and load your AiiDA profile:

```python
from aiida import orm, load_profile
from aiida.common.exceptions import NotExistent

load_profile()
```

!!! important

    You need to load your AiiDA profile to be able to interact with the database, where your computer/code/calculations are stored.
    Hence, you have to execute the code above before running any of the cells below.


## Computers

First we'll set up a computers for AiiDA to run on.
The "transport" that we'll use (identified via `core.ssh_async`) will automatically use the configuration from your `~/.ssh/config`.
Hence the instructions below assume that you've already set up you connection with the computer.

!!! warning

    Most of the setup and configuration is specific and correct for the Pawsey supercomputer.
    **But you need to update the `working_directory` in the cell below to the root directory on `/scratch` where you want to run your AiiDA calculations.**


```python
working_directory = '/scratch/pawsey1141/mbercx/aiida-defect-neb/aiida'
```

```python
try:
    pawsey = orm.load_computer('pawsey')
except NotExistent:
    pawsey = orm.Computer(
        label='pawsey',
        hostname='setonix.pawsey.org.au',
        transport_type='core.ssh_async',
        scheduler_type='core.slurm',
    )
    pawsey.set_workdir(working_directory)
    pawsey.set_mpirun_command('srun -N {num_machines} -n {tot_num_mpiprocs} -c 1 -m block:block:block'.split())
    pawsey.set_default_mpiprocs_per_machine(64)
    pawsey.set_use_double_quotes(True)
    pawsey.configure()
    pawsey.store()
```

!!! note
    The code snippets for setting up the computer is wrapped in `try-except` blocks to avoid trying to set up the same computer multiple times.
    This would fail, since two computers can't have the same label.


We can see if the computers have been set up properly using the CLI command:

```python
!verdi computer list
```

As well as test them:

```python
!verdi computer test pawsey
```

## Codes

Next, we'll set up the VASP code we need to run on `pawsey`:

```python
code_label = 'vasp-6.4.3-vtst'

try:
    orm.load_code(f'{code_label}@pawsey')
except NotExistent:
    code = orm.InstalledCode(
        label=code_label,
        computer=pawsey,
        default_calc_job_plugin='vasp.vasp',
        filepath_executable='/software/projects/pawsey1141/cverdi/vasp.6.4.3-vtst/bin/vasp_std'
    )
    code.description = 'VASP 6.4.3 std version with VTST'
    code.use_double_quotes = True
    code.prepend_text = """
module load hdf5/1.14.3-api-v112 netlib-scalapack/2.2.0 fftw/3.3.10
export OMP_NUM_THREADS=1
export MPICH_OFI_STARTUP_CONNECT=1
export MPICH_OFI_VERBOSE=1
export FI_CXI_DEFAULT_VNI=$(od -vAn -N4 -tu < /dev/urandom)
ulimit -s unlimited
"""
    code.store()
```

```python
!verdi code list
```

## Pseudo potentials


In order to set up the input `POTCAR` files, the `aiida-vasp` plugin needs access to the VASP pseudo potentials.

!!! warning "Important"
    Again, change the path below to the one where you have the VASP POTCAR files stored!
    If you run `ls` in this directory you should see all the element/POTCAR directories.

```python
path_to_potcar_files = '/Users/mbercx/tmp/potpaw'
```

The cell below loads the pseudo potentials from the path specified above.
Since you can only upload them once, we once again wrap the cell in a `try`-`except` block.

```python
from aiida_vasp.data.potcar import PotcarData

try:
    orm.load_group('PBE.64')
except NotExistent:
    PotcarData.upload_potcar_family(
        source=path_to_potcar_files,
        group_name='PBE.64',
        group_description='Family of the v64 pseudo potentials for VASP.'
    );
```

<div class="grid cards" markdown>

-   ✅ **All done!**

    ---

    You should now be ready to run your first workflow!
    Proceed to the quickstart tutorial.

    [→ Go to the tutorial](quickstart.md)

</div>
