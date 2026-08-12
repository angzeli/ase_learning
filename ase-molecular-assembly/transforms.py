"""Generic rigid-body transformations for ASE structures."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from ase import Atoms

from frame import MolecularFrame


_TOLERANCE = 1.0e-12


def _as_vector(value: Sequence[float], name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,):
        raise ValueError(f"{name} must be a Cartesian vector with shape (3,)")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must contain only finite values")
    return vector.copy()


def _unit_vector(value: Sequence[float], name: str) -> np.ndarray:
    vector = _as_vector(value, name)
    norm = float(np.linalg.norm(vector))
    if norm <= _TOLERANCE:
        raise ValueError(f"{name} must have non-zero length")
    return vector / norm


def _copy_or_original(atoms: Atoms, inplace: bool) -> Atoms:
    if not isinstance(atoms, Atoms):
        raise TypeError("atoms must be an ase.Atoms object")
    positions = np.asarray(atoms.get_positions(), dtype=float)
    if not np.all(np.isfinite(positions)):
        raise ValueError("atoms must contain only finite Cartesian coordinates")
    return atoms if inplace else atoms.copy()


def _resolve_center(atoms: Atoms, center: str | Sequence[float]) -> np.ndarray:
    if isinstance(center, str):
        if center not in {"center_of_mass", "com"}:
            raise ValueError(
                "center must be 'center_of_mass'/'com' or a Cartesian point"
            )
        value = np.asarray(atoms.get_center_of_mass(), dtype=float)
    else:
        value = _as_vector(center, "center")
    if not np.all(np.isfinite(value)):
        raise ValueError("rotation center must contain only finite values")
    return value


def rotation_matrix(axis: Sequence[float], angle_degrees: float) -> np.ndarray:
    """Return a right-handed 3D rotation matrix for an angle in degrees."""

    unit_axis = _unit_vector(axis, "axis")
    if not np.isfinite(angle_degrees):
        raise ValueError("angle_degrees must be finite")
    angle = np.deg2rad(float(angle_degrees))
    x, y, z = unit_axis
    cross_matrix = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    identity = np.eye(3)
    return (
        identity
        + np.sin(angle) * cross_matrix
        + (1.0 - np.cos(angle)) * (cross_matrix @ cross_matrix)
    )


def alignment_rotation(
    source_vector: Sequence[float], target_vector: Sequence[float]
) -> np.ndarray:
    """Return a stable rotation that aligns one vector with another.

    Parallel vectors return the identity. For anti-parallel vectors, the
    rotation axis is chosen deterministically from the least-aligned Cartesian
    basis vector.
    """

    source = _unit_vector(source_vector, "source_vector")
    target = _unit_vector(target_vector, "target_vector")
    cosine = float(np.clip(np.dot(source, target), -1.0, 1.0))
    cross = np.cross(source, target)
    sine = float(np.linalg.norm(cross))

    if sine <= _TOLERANCE:
        if cosine > 0.0:
            return np.eye(3)
        basis = np.eye(3)[int(np.argmin(np.abs(source)))]
        perpendicular_axis = np.cross(source, basis)
        return rotation_matrix(perpendicular_axis, 180.0)

    unit_axis = cross / sine
    angle_degrees = float(np.rad2deg(np.arctan2(sine, cosine)))
    return rotation_matrix(unit_axis, angle_degrees)


def translate(
    atoms: Atoms, displacement: Sequence[float], *, inplace: bool = False
) -> Atoms:
    """Translate by a Cartesian displacement in Å, returning a copy by default."""

    result = _copy_or_original(atoms, inplace)
    vector = _as_vector(displacement, "displacement")
    result.set_positions(result.get_positions() + vector)
    return result


def translate_along(
    atoms: Atoms,
    direction: Sequence[float],
    distance: float,
    *,
    inplace: bool = False,
) -> Atoms:
    """Translate along an arbitrary direction by ``distance`` in Å."""

    if not np.isfinite(distance):
        raise ValueError("distance must be finite")
    return translate(
        atoms, _unit_vector(direction, "direction") * float(distance), inplace=inplace
    )


def rotate_about_axis(
    atoms: Atoms,
    axis: Sequence[float],
    angle_degrees: float,
    *,
    center: str | Sequence[float] = "center_of_mass",
    inplace: bool = False,
) -> Atoms:
    """Rotate rigidly around an axis through a stated centre.

    The angle is in degrees. ``center`` may be ``"center_of_mass"`` or an
    explicit Cartesian point in Å.
    """

    result = _copy_or_original(atoms, inplace)
    rotation_center = _resolve_center(result, center)
    matrix = rotation_matrix(axis, angle_degrees)
    shifted = result.get_positions() - rotation_center
    result.set_positions(shifted @ matrix.T + rotation_center)
    return result


def align_vector(
    atoms: Atoms,
    source_vector: Sequence[float],
    target_vector: Sequence[float],
    *,
    center: str | Sequence[float] = "center_of_mass",
    inplace: bool = False,
) -> Atoms:
    """Rigidly rotate ``source_vector`` onto ``target_vector``."""

    result = _copy_or_original(atoms, inplace)
    rotation_center = _resolve_center(result, center)
    matrix = alignment_rotation(source_vector, target_vector)
    shifted = result.get_positions() - rotation_center
    result.set_positions(shifted @ matrix.T + rotation_center)
    return result


def align_frames(
    atoms: Atoms,
    source_frame: MolecularFrame,
    target_frame: MolecularFrame,
    *,
    map_origins: bool = True,
    inplace: bool = False,
) -> Atoms:
    """Align a molecular frame with a target frame using one rigid transform.

    By default, the source origin is mapped onto the target origin as the axes
    are aligned. With ``map_origins=False``, the axes rotate about the source
    origin while that origin remains fixed.
    """

    result = _copy_or_original(atoms, inplace)
    if not isinstance(source_frame, MolecularFrame) or not isinstance(
        target_frame, MolecularFrame
    ):
        raise TypeError("source_frame and target_frame must be MolecularFrame objects")
    matrix = target_frame.basis @ source_frame.basis.T
    shifted = result.get_positions() - source_frame.origin
    destination_origin = target_frame.origin if map_origins else source_frame.origin
    result.set_positions(shifted @ matrix.T + destination_origin)
    return result


__all__ = [
    "align_frames",
    "align_vector",
    "alignment_rotation",
    "rotate_about_axis",
    "rotation_matrix",
    "translate",
    "translate_along",
]
