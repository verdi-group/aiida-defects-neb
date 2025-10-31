# Introduction

The `aiida-defects-neb` package is currently mainly a testing ground for developing workflows to run NEB calculations for calculating the migration barrier of defects.

## Installation

First, clone the repository:

```
git clone https://github.com/verdi-group/aiida-defects-neb.git

```

Create a Python environment with the tool of your choice and install the package from the source code in _editable_ mode (`-e`):

```
pip install -e aiida-defects-neb
```

This will also install AiiDA (via the `aiida-core` package).
All you need now is to set up a profile, let's call it `neb`:

```
verdi presto -p neb
```

## First steps

<div class="grid cards" markdown>

-   ⚙️ **Set up**

    ---

    First steps: start by setting up AiiDA and the necessary computer and VASP code.

    [→ Go to the setup page](setup.md)

-   🚀 **Quickstart**

    ---

    After performing the required setup, try running your first NEB workflow with the quick start tutorial!

    [→ Go to the tutorial](quickstart.md)

</div>

!!! warning

    If you found your way to this repository and are interested in running the workflows, feel free!
    However, be aware that the API of the workflows can still change drastically until we get to a first stable release (v1.0.0), which may still take quite some time.
    Here be dragons! 🐉
