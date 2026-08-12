from __future__ import annotations

import numpy as np
import pytest
from ase import Atoms

from frame import define_frame


def test_frame_is_orthonormal_and_right_handed(planar_atoms: Atoms) -> None:
    frame = define_frame(planar_atoms, [0, 1, 2, 3], [0, 1])

    assert np.allclose(frame.basis.T @ frame.basis, np.eye(3), atol=1.0e-12)
    assert np.allclose(np.cross(frame.x_axis, frame.y_axis), frame.normal)


def test_default_normal_orientation_is_deterministic(planar_atoms: Atoms) -> None:
    first = define_frame(planar_atoms, [0, 1, 2, 3], [0, 1])
    reordered = define_frame(planar_atoms, [3, 1, 0, 2], [0, 1])

    assert np.allclose(first.normal, reordered.normal)
    dominant = np.argmax(np.abs(first.normal))
    assert first.normal[dominant] > 0.0


def test_reference_vector_controls_normal_sign(planar_atoms: Atoms) -> None:
    frame = define_frame(
        planar_atoms,
        [0, 1, 2, 3],
        [0, 1],
        normal_reference=[0.0, 0.0, -1.0],
    )

    assert np.dot(frame.normal, [0.0, 0.0, -1.0]) > 0.999999


def test_frame_does_not_mutate_input(planar_atoms: Atoms) -> None:
    original = planar_atoms.get_positions().copy()
    define_frame(planar_atoms, [0, 1, 2, 3], [0, 1])
    assert np.array_equal(planar_atoms.get_positions(), original)


@pytest.mark.parametrize(
    "plane_indices,x_axis_indices,error",
    [
        ([0, 1], [0, 1], ValueError),
        ([0, 1, 99], [0, 1], IndexError),
        ([0, 0, 1], [0, 1], ValueError),
        ([0, 1, 2], [0, 0], ValueError),
    ],
)
def test_invalid_selections_fail_clearly(
    planar_atoms: Atoms,
    plane_indices: list[int],
    x_axis_indices: list[int],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        define_frame(planar_atoms, plane_indices, x_axis_indices)


def test_collinear_plane_definition_fails() -> None:
    atoms = Atoms("C3", positions=[[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    with pytest.raises(ValueError, match="collinear"):
        define_frame(atoms, [0, 1, 2], [0, 1])


def test_nonfinite_coordinates_fail(planar_atoms: Atoms) -> None:
    planar_atoms.positions[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        define_frame(planar_atoms, [0, 1, 2, 3], [0, 1])
