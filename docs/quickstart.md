---
jupyter:
  jupytext:
    cell_metadata_filter: -all
    formats: .jupytext-sync-ipynb//ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.17.3
  kernelspec:
    display_name: DEFECT
    language: python
    name: defect
---

# Quickstart


## Create test system

Let's start by setting up a little test system: a BCC Li 2x2x2 supercell to calculate the migration barrier of Li into a vacancy we create.

First, create the BCC Li 2x2x2 supercell:

```python
from pymatgen.core import Structure, Lattice

li_bcc = Structure(
    Lattice.cubic(3.51),
    ["Li", "Li"],
    [[0, 0, 0], [0.5, 0.5, 0.5]]
)
supercell = li_bcc * [2, 2, 2]
```

We select one of the Li (with site index 9) and remove it to create a vacancy.
Then we write the structure to a CIF file:

```python
initial_structure = supercell.copy()
initial_structure.remove_sites([9,])
initial_structure.to('initial.cif');
```

After inspecting the initial structure with VESTA, we determine we want to calculate the migration of the Li with site index 10 into the freshly created vacancy.
To create the final structure, we simply create a copy of the initial structure and translate the Li site:

```python
final_structure = initial_structure.copy()
final_structure.translate_sites(10, initial_structure.sites[10].frac_coords - supercell.sites[9].frac_coords)
```

Creating the final structure by translating the migrating site make sure the indices of all atoms correspond, which is important for the NEB calculation.
To obtain a visualization of the migration path (sans geometry optimization!), we create the images and add all the migrating site positions to a single structure before writing the CIF:

```python
neb_images = initial_structure.interpolate(final_structure, nimages=6)

path_structure = neb_images[0]

for image in neb_images[0:]:
    path_structure.append('Li', image.sites[10].frac_coords)

path_structure.to('path.cif');
```

You can open this CIF file with your favorite visualizer tool (e.g. VESTA) to see the path we're going to calculate the transition barrier for!


## Calculate the energy barrier

As always, we start by loading our profile:

```python
from aiida import orm, load_profile

load_profile()
```

Next, we want to run the `NebWorkChain`.
To make it easier to specify default inputs, we have developed what we call a "protocol", i.e. a set of input parameters which can be overridden or adapted later.
These can be obtained using the `get_builder_from_protocol` method:

```python
from aiida_defects_neb.workflows.neb import NebWorkChain

builder = NebWorkChain.get_builder_from_protocol(
    initial_structure = orm.StructureData(pymatgen=initial_structure),
    final_structure = orm.StructureData(pymatgen=final_structure),
    vasp_code = orm.load_code('vasp-6.4.3-vtst@pawsey'),
    options = {
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 60,
            'num_cores_per_mpiproc': 1
        },
        'account': 'pawsey1141',
        'queue_name': 'debug',
        'max_memory_kb': int(115 * 1024 * 1024),
        'max_wallclock_seconds': 3600
    },
    number_images=5
)
```

A "process builder" is a more general concept in AiiDA.
It basically stores all the inputs for the process you want to run.
You can see its contents by simply returning it:

```python
builder
```

You can also change inputs as desired, for example, we probably don't need such a high energy cutoff for Li:

```python
builder['relax']['parameters']['incar']['encut'] = 300
builder['neb']['parameters']['incar']['encut'] = 300
```

Now we're happy with the inputs, we can _submit_ the workflow to the engine!

```python
from aiida import engine

workchain = engine.submit(builder)
```

Basically, the workflow is now stored in the AiiDA database.
To execute it, we'll have to start the daemon:

```python
!verdi daemon start
```

The daemon is a process that runs a Python instance in the background 
Once the workflow is finished, you can e.g. plot the resulting energies:

```python
if not workchain.is_finished:
    print('The workflow is still running!')
else:
    import matplotlib.pyplot as plt
    plt.plot(workchain.outputs['energies'])
```
