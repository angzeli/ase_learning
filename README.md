# ASE Learning

A personal learning repository for exploring the [Atomic Simulation
Environment (ASE)](https://ase-lib.org/). It collects worked versions of
official tutorials and leaves room for small, experimental projects built
while learning ASE.

## Repository structure

- `official_tutorials_introductory/` and `official_tutorials_advanced/` — notebooks and notes based on official ASE tutorials.
- `files/` — structures and other supporting data used by the exercises.
- `toy_projects/` — planned home for future experiments and small projects.

## Getting started

Create and activate a virtual environment, then install ASE and JupyterLab:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install ase jupyterlab
jupyter lab
```

Individual tutorials may require additional packages. Their notebooks should
document any extra setup they need.

## License

This repository is available under the [MIT License](LICENSE).

## Author

Angze Li
