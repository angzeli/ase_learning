from __future__ import annotations

import numpy as np
from ase import Atoms

from frame import MolecularFrame
from transforms import (
    align_frames,
    align_vector,
    alignment_rotation,
    rotate_about_axis,
    translate,
    translate_along,
)


def _pairwise_distances(atoms: Atoms) -> np.ndarray:
    positions = atoms.get_positions()
    return np.linalg.norm(positions[:, None] - positions[None, :], axis=-1)


def test_cartesian_and_directional_translation(planar_atoms: Atoms) -> None:
    original = planar_atoms.get_positions().copy()
    cartesian = translate(planar_atoms, [1.0, -2.0, 0.5])
    directional = translate_along(planar_atoms, [0.0, 2.0, 0.0], 3.0)

    assert np.allclose(cartesian.positions, original + [1.0, -2.0, 0.5])
    assert np.allclose(directional.positions, original + [0.0, 3.0, 0.0])
    assert np.array_equal(planar_atoms.positions, original)


def test_rotation_about_explicit_center() -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [1, 0, 0]])
    rotated = rotate_about_axis(atoms, [0, 0, 1], 90.0, center=[0, 0, 0])

    assert np.allclose(rotated.positions[1], [0.0, 1.0, 0.0], atol=1.0e-12)
    assert np.array_equal(atoms.positions, [[0, 0, 0], [1, 0, 0]])


def test_vector_alignment_handles_general_direction() -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [1, 0, 0]])
    aligned = align_vector(atoms, [1, 0, 0], [1, 1, 1], center=[0, 0, 0])
    resulting_direction = aligned.positions[1] / np.linalg.norm(aligned.positions[1])

    assert np.allclose(resulting_direction, np.ones(3) / np.sqrt(3), atol=1.0e-12)


def test_vector_alignment_handles_antiparallel_vectors() -> None:
    matrix = alignment_rotation([1, 0, 0], [-1, 0, 0])

    assert np.all(np.isfinite(matrix))
    assert np.allclose(matrix @ [1, 0, 0], [-1, 0, 0], atol=1.0e-12)
    assert np.allclose(matrix.T @ matrix, np.eye(3), atol=1.0e-12)


def test_frame_alignment_maps_axes_and_origins(planar_atoms: Atoms) -> None:
    source = MolecularFrame(
        origin=np.zeros(3),
        x_axis=np.array([1.0, 0.0, 0.0]),
        y_axis=np.array([0.0, 1.0, 0.0]),
        normal=np.array([0.0, 0.0, 1.0]),
    )
    target = MolecularFrame(
        origin=np.array([4.0, 5.0, 6.0]),
        x_axis=np.array([0.0, 1.0, 0.0]),
        y_axis=np.array([-1.0, 0.0, 0.0]),
        normal=np.array([0.0, 0.0, 1.0]),
    )
    aligned = align_frames(planar_atoms, source, target)
    expected = planar_atoms.positions @ target.basis.T + target.origin

    assert np.allclose(aligned.positions, expected)


def test_all_rigid_transforms_preserve_pairwise_distances(planar_atoms: Atoms) -> None:
    baseline = _pairwise_distances(planar_atoms)
    transformed = translate(planar_atoms, [2.0, 1.0, -4.0])
    transformed = rotate_about_axis(
        transformed, [1.0, 2.0, 3.0], 137.0, center=[0.2, -0.3, 0.7]
    )
    transformed = align_vector(
        transformed, [1.0, -1.0, 2.0], [-2.0, 3.0, 0.5], center="com"
    )

    assert np.allclose(_pairwise_distances(transformed), baseline, atol=1.0e-12)
