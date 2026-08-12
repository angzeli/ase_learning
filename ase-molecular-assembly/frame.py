"""Explicit local coordinate frames for finite molecular structures."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Sequence

import numpy as np
from ase import Atoms


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


@dataclass(frozen=True)
class MolecularFrame:
    """A right-handed orthonormal molecular coordinate frame.

    ``origin`` is a Cartesian point in Å. The remaining fields are unit
    vectors expressed in the global Cartesian coordinate system.
    """

    origin: np.ndarray
    x_axis: np.ndarray
    y_axis: np.ndarray
    normal: np.ndarray

    def __post_init__(self) -> None:
        origin = _as_vector(self.origin, "origin")
        x_axis = _unit_vector(self.x_axis, "x_axis")
        y_axis = _unit_vector(self.y_axis, "y_axis")
        normal = _unit_vector(self.normal, "normal")

        basis = np.column_stack((x_axis, y_axis, normal))
        if not np.allclose(basis.T @ basis, np.eye(3), atol=1.0e-10):
            raise ValueError("frame axes must be mutually orthogonal")
        if not np.allclose(np.cross(x_axis, y_axis), normal, atol=1.0e-10):
            raise ValueError("frame axes must satisfy cross(x_axis, y_axis) = normal")

        for name, value in (
            ("origin", origin),
            ("x_axis", x_axis),
            ("y_axis", y_axis),
            ("normal", normal),
        ):
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    @property
    def basis(self) -> np.ndarray:
        """Return the 3 x 3 basis matrix with local axes as columns."""

        return np.column_stack((self.x_axis, self.y_axis, self.normal))

    def vector_to_cartesian(self, local_vector: Sequence[float]) -> np.ndarray:
        """Convert a vector from local-frame components to Cartesian form."""

        return self.basis @ _as_vector(local_vector, "local_vector")

    def vector_to_local(self, cartesian_vector: Sequence[float]) -> np.ndarray:
        """Resolve a Cartesian vector into local-frame components."""

        return self.basis.T @ _as_vector(cartesian_vector, "cartesian_vector")

    def point_to_cartesian(self, local_point: Sequence[float]) -> np.ndarray:
        """Convert local coordinates to a Cartesian point in Å."""

        return self.origin + self.vector_to_cartesian(local_point)

    def point_to_local(self, cartesian_point: Sequence[float]) -> np.ndarray:
        """Convert a Cartesian point in Å to local coordinates."""

        return self.vector_to_local(
            _as_vector(cartesian_point, "cartesian_point") - self.origin
        )

    def to_dict(self) -> dict[str, list[float]]:
        """Return a simple serialisable representation of the frame."""

        return {
            "origin": self.origin.tolist(),
            "x_axis": self.x_axis.tolist(),
            "y_axis": self.y_axis.tolist(),
            "normal": self.normal.tolist(),
        }


def _validated_indices(
    indices: Sequence[int], atom_count: int, name: str, minimum: int
) -> tuple[int, ...]:
    values = tuple(indices)
    if len(values) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} atom indices")
    if any(not isinstance(index, Integral) for index in values):
        raise TypeError(f"{name} must contain only integer atom indices")
    integer_values = tuple(int(index) for index in values)
    if len(set(integer_values)) != len(integer_values):
        raise ValueError(f"{name} must not contain duplicate atom indices")
    invalid = [index for index in integer_values if index < 0 or index >= atom_count]
    if invalid:
        raise IndexError(f"{name} contains out-of-range atom indices: {invalid}")
    return integer_values


def define_frame(
    atoms: Atoms,
    plane_indices: Sequence[int],
    x_axis_indices: Sequence[int],
    *,
    origin: str | Sequence[float] = "center_of_mass",
    normal_reference: Sequence[float] | None = None,
    degeneracy_tolerance: float = 1.0e-10,
) -> MolecularFrame:
    """Define a molecular local frame from explicit atom selections.

    Parameters
    ----------
    atoms
        Input structure. It is never modified.
    plane_indices
        At least three unique atoms defining the best-fit molecular plane.
    x_axis_indices
        Exactly two ordered atoms. Their connecting vector is projected into
        the fitted plane, and its order fixes the positive local x direction.
    origin
        ``"center_of_mass"`` (default), ``"centroid"``,
        ``"plane_centroid"``, or an explicit Cartesian point in Å.
    normal_reference
        Optional Cartesian vector used to choose the plane-normal sign. The
        fitted normal is oriented to have a positive dot product with it. If
        omitted, the normal's largest-magnitude Cartesian component is made
        positive, giving a deterministic coordinate-based convention.
    degeneracy_tolerance
        Relative singular-value tolerance used to reject collinear planes.

    Returns
    -------
    MolecularFrame
        A deterministic right-handed orthonormal coordinate frame.
    """

    if not isinstance(atoms, Atoms):
        raise TypeError("atoms must be an ase.Atoms object")
    if not np.isfinite(degeneracy_tolerance) or degeneracy_tolerance <= 0.0:
        raise ValueError("degeneracy_tolerance must be a positive finite number")

    positions = np.asarray(atoms.get_positions(), dtype=float)
    if positions.shape != (len(atoms), 3) or not np.all(np.isfinite(positions)):
        raise ValueError("atoms must contain only finite Cartesian coordinates")

    plane = _validated_indices(plane_indices, len(atoms), "plane_indices", 3)
    axis_pair = _validated_indices(x_axis_indices, len(atoms), "x_axis_indices", 2)
    if len(axis_pair) != 2:
        raise ValueError("x_axis_indices must contain exactly two atom indices")

    plane_coordinates = positions[list(plane)]
    plane_centroid = plane_coordinates.mean(axis=0)
    centered = plane_coordinates - plane_centroid
    _, singular_values, right_vectors = np.linalg.svd(centered, full_matrices=False)
    if singular_values[0] <= _TOLERANCE:
        raise ValueError("plane atom selection is degenerate")
    if singular_values[1] <= degeneracy_tolerance * singular_values[0]:
        raise ValueError("plane atom selection is collinear or nearly collinear")

    normal = right_vectors[-1].copy()
    if normal_reference is not None:
        reference = _unit_vector(normal_reference, "normal_reference")
        projection = float(np.dot(normal, reference))
        if abs(projection) <= degeneracy_tolerance:
            raise ValueError(
                "normal_reference is orthogonal to the fitted plane normal"
            )
        if projection < 0.0:
            normal *= -1.0
    else:
        dominant_component = int(np.argmax(np.abs(normal)))
        if normal[dominant_component] < 0.0:
            normal *= -1.0

    raw_x_axis = positions[axis_pair[1]] - positions[axis_pair[0]]
    raw_x_norm = float(np.linalg.norm(raw_x_axis))
    if raw_x_norm <= _TOLERANCE:
        raise ValueError("x-axis atom pair defines a zero-length vector")
    x_axis = raw_x_axis - np.dot(raw_x_axis, normal) * normal
    projected_norm = float(np.linalg.norm(x_axis))
    if projected_norm <= degeneracy_tolerance * raw_x_norm:
        raise ValueError("x-axis atom pair has no stable in-plane projection")
    x_axis /= projected_norm
    y_axis = np.cross(normal, x_axis)
    y_axis /= np.linalg.norm(y_axis)

    if isinstance(origin, str):
        if origin == "center_of_mass":
            frame_origin = np.asarray(atoms.get_center_of_mass(), dtype=float)
        elif origin == "centroid":
            frame_origin = positions.mean(axis=0)
        elif origin == "plane_centroid":
            frame_origin = plane_centroid
        else:
            raise ValueError(
                "origin must be 'center_of_mass', 'centroid', 'plane_centroid', "
                "or an explicit Cartesian point"
            )
    else:
        frame_origin = _as_vector(origin, "origin")
    if not np.all(np.isfinite(frame_origin)):
        raise ValueError("frame origin must contain only finite values")

    return MolecularFrame(frame_origin, x_axis, y_axis, normal)


__all__ = ["MolecularFrame", "define_frame"]
