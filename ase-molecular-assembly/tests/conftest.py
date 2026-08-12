"""Shared deterministic molecular fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from assembly import Component  # noqa: E402
from frame import define_frame  # noqa: E402


@pytest.fixture
def planar_atoms() -> Atoms:
    """Return a small, non-symmetric planar demo monomer."""

    return Atoms(
        "C4H2",
        positions=np.array(
            [
                [-1.0, -0.6, 0.0],
                [1.0, -0.6, 0.0],
                [0.8, 0.7, 0.0],
                [-0.9, 0.9, 0.0],
                [-1.8, -1.0, 0.0],
                [1.8, -1.0, 0.0],
            ]
        ),
    )


@pytest.fixture
def component(planar_atoms: Atoms) -> Component:
    frame = define_frame(
        planar_atoms,
        plane_indices=[0, 1, 2, 3],
        x_axis_indices=[0, 1],
        normal_reference=[0.0, 0.0, 1.0],
    )
    return Component(planar_atoms, frame, label="A", source="deterministic fixture")
