"""Validation reports for finite rigid-body molecular assemblies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Sequence

import numpy as np
from ase import Atoms

from frame import MolecularFrame

if TYPE_CHECKING:
    from assembly import VerticalInterface


@dataclass(frozen=True)
class ClosestContact:
    """The closest pair of atoms belonging to different components."""

    atom_i: int
    atom_j: int
    component_i: int
    component_j: int
    distance: float


@dataclass(frozen=True)
class ValidationReport:
    """Structured pass/warning/fail result for one assembled structure."""

    passed: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    atom_count: int
    expected_atom_count: int | None
    component_count: int | None
    minimum_intercomponent_distance: float | None
    closest_contact: ClosestContact | None
    maximum_rigid_body_error: float | None
    requested_geometry_errors: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Return the complete report as serialisable built-in types."""

        return asdict(self)


def _pairwise_distances(positions: np.ndarray) -> np.ndarray:
    differences = positions[:, None, :] - positions[None, :, :]
    return np.linalg.norm(differences, axis=-1)


def _closest_intercomponent_contact(
    positions: np.ndarray, component_ids: np.ndarray
) -> ClosestContact | None:
    closest: ClosestContact | None = None
    for component_i in np.unique(component_ids):
        indices_i = np.flatnonzero(component_ids == component_i)
        for component_j in np.unique(component_ids):
            if component_j <= component_i:
                continue
            indices_j = np.flatnonzero(component_ids == component_j)
            differences = positions[indices_i, None, :] - positions[indices_j, :]
            distances = np.linalg.norm(differences, axis=-1)
            flat_index = int(np.argmin(distances))
            local_i, local_j = np.unravel_index(flat_index, distances.shape)
            distance = float(distances[local_i, local_j])
            if closest is None or distance < closest.distance:
                closest = ClosestContact(
                    atom_i=int(indices_i[local_i]),
                    atom_j=int(indices_j[local_j]),
                    component_i=int(component_i),
                    component_j=int(component_j),
                    distance=distance,
                )
    return closest


def _rigid_transform(
    reference: np.ndarray, transformed: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    reference_center = reference.mean(axis=0)
    transformed_center = transformed.mean(axis=0)
    covariance = (reference - reference_center).T @ (transformed - transformed_center)
    left, _, right_transpose = np.linalg.svd(covariance)
    rotation = right_transpose.T @ left.T
    if np.linalg.det(rotation) < 0.0:
        right_transpose[-1] *= -1.0
        rotation = right_transpose.T @ left.T
    translation = transformed_center - rotation @ reference_center
    return rotation, translation


def _signed_angle_degrees(
    first: np.ndarray, second: np.ndarray, normal: np.ndarray
) -> float:
    cosine = float(np.clip(np.dot(first, second), -1.0, 1.0))
    sine = float(np.dot(normal, np.cross(first, second)))
    return float(np.rad2deg(np.arctan2(sine, cosine)))


def _wrapped_angle_error(actual: float, expected: float) -> float:
    return float((actual - expected + 180.0) % 360.0 - 180.0)


def validate_assembly(
    assembly: Atoms,
    reference_components: Sequence[Atoms] | None = None,
    *,
    clash_threshold: float = 0.8,
    contact_warning_threshold: float | None = None,
    rigid_body_tolerance: float = 1.0e-8,
    reference_frames: Sequence[MolecularFrame] | None = None,
    vertical_interfaces: Sequence["VerticalInterface"] | None = None,
    geometry_tolerance: float = 1.0e-7,
    angle_tolerance_degrees: float = 1.0e-6,
) -> ValidationReport:
    """Validate composition, rigidity, clashes, and requested stack geometry.

    Parameters
    ----------
    assembly
        Assembled finite structure containing a per-atom ``component_id``.
    reference_components
        Original monomers in component-ID order. When supplied, atom counts,
        compositions, and intra-component distance matrices are checked.
    clash_threshold
        Inter-component distances below this value in Å are failures.
    contact_warning_threshold
        Optional larger distance in Å below which a non-failing warning is
        issued. This is geometric screening, not a bonding interpretation.
    rigid_body_tolerance
        Maximum allowed pairwise-distance change in Å.
    reference_frames, vertical_interfaces
        Optional ordered inputs used together to verify relative separation,
        slip, and twist for a vertical stack.
    """

    if not isinstance(assembly, Atoms):
        raise TypeError("assembly must be an ase.Atoms object")
    for value, name in (
        (clash_threshold, "clash_threshold"),
        (rigid_body_tolerance, "rigid_body_tolerance"),
        (geometry_tolerance, "geometry_tolerance"),
        (angle_tolerance_degrees, "angle_tolerance_degrees"),
    ):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be a positive finite number")
    if contact_warning_threshold is not None:
        if (
            not np.isfinite(contact_warning_threshold)
            or contact_warning_threshold <= clash_threshold
        ):
            raise ValueError(
                "contact_warning_threshold must be finite and exceed clash_threshold"
            )

    errors: list[str] = []
    warnings: list[str] = []
    positions = np.asarray(assembly.get_positions(), dtype=float)
    coordinates_are_finite = bool(np.all(np.isfinite(positions)))
    if not coordinates_are_finite:
        errors.append("assembly contains non-finite Cartesian coordinates")

    references = (
        tuple(reference_components) if reference_components is not None else None
    )
    expected_atom_count = (
        sum(len(component) for component in references) if references else None
    )
    if expected_atom_count is not None and len(assembly) != expected_atom_count:
        errors.append(
            f"atom count mismatch: assembly has {len(assembly)}, expected {expected_atom_count}"
        )

    component_ids: np.ndarray | None = None
    component_count: int | None = None
    if "component_id" not in assembly.arrays:
        errors.append("assembly is missing the per-atom component_id array")
    else:
        raw_ids = np.asarray(assembly.arrays["component_id"])
        if raw_ids.shape != (len(assembly),):
            errors.append("component_id must contain exactly one value per atom")
        elif not np.issubdtype(raw_ids.dtype, np.integer):
            errors.append("component_id values must use an integer dtype")
        elif np.any(raw_ids < 0):
            errors.append("component_id values must be non-negative")
        else:
            component_ids = raw_ids.astype(int, copy=False)
            unique_ids = np.unique(component_ids)
            expected_ids = np.arange(len(unique_ids), dtype=int)
            if not np.array_equal(unique_ids, expected_ids):
                errors.append(
                    "component_id values must be complete and contiguous from zero"
                )
            component_count = len(unique_ids)
            if references is not None and component_count != len(references):
                errors.append(
                    f"component count mismatch: assembly has {component_count}, "
                    f"expected {len(references)}"
                )

    maximum_rigid_body_error: float | None = None
    if references is not None and component_ids is not None and coordinates_are_finite:
        maximum_rigid_body_error = 0.0
        for component_id, reference in enumerate(references):
            selected = np.flatnonzero(component_ids == component_id)
            if len(selected) != len(reference):
                errors.append(
                    f"component {component_id} atom count mismatch: "
                    f"assembly has {len(selected)}, expected {len(reference)}"
                )
                continue
            if not np.array_equal(assembly.numbers[selected], reference.numbers):
                errors.append(
                    f"component {component_id} composition or atom order changed"
                )
                continue
            reference_positions = np.asarray(reference.get_positions(), dtype=float)
            if not np.all(np.isfinite(reference_positions)):
                errors.append(
                    f"reference component {component_id} has non-finite coordinates"
                )
                continue
            distance_error = float(
                np.max(
                    np.abs(
                        _pairwise_distances(positions[selected])
                        - _pairwise_distances(reference_positions)
                    )
                )
            )
            maximum_rigid_body_error = max(maximum_rigid_body_error, distance_error)
            if distance_error > rigid_body_tolerance:
                errors.append(
                    f"component {component_id} is not rigid: maximum pairwise-distance "
                    f"change is {distance_error:.6g} Å"
                )

    closest_contact = None
    if (
        component_ids is not None
        and coordinates_are_finite
        and component_count
        and component_count > 1
    ):
        closest_contact = _closest_intercomponent_contact(positions, component_ids)
        if closest_contact is not None and closest_contact.distance < clash_threshold:
            errors.append(
                "severe inter-component clash: atoms "
                f"{closest_contact.atom_i} (component {closest_contact.component_i}) and "
                f"{closest_contact.atom_j} (component {closest_contact.component_j}) are "
                f"{closest_contact.distance:.6g} Å apart"
            )
        elif (
            closest_contact is not None
            and contact_warning_threshold is not None
            and closest_contact.distance < contact_warning_threshold
        ):
            warnings.append(
                f"short inter-component contact of {closest_contact.distance:.6g} Å"
            )

    geometry_errors: dict[str, float] = {}
    if vertical_interfaces is not None or reference_frames is not None:
        if references is None or component_ids is None:
            errors.append(
                "requested-geometry validation requires reference_components and component_id"
            )
        elif vertical_interfaces is None or reference_frames is None:
            errors.append(
                "reference_frames and vertical_interfaces must be supplied together"
            )
        elif len(reference_frames) != len(references):
            errors.append(
                "reference_frames must have one frame per reference component"
            )
        elif len(vertical_interfaces) != len(references) - 1:
            errors.append(
                "vertical_interfaces must have one entry per adjacent component pair"
            )
        elif coordinates_are_finite and all(
            np.count_nonzero(component_ids == index) == len(reference)
            for index, reference in enumerate(references)
        ):
            transformed_frames: list[MolecularFrame] = []
            for component_id, (reference, frame) in enumerate(
                zip(references, reference_frames)
            ):
                if not isinstance(frame, MolecularFrame):
                    errors.append(
                        "reference_frames must contain MolecularFrame objects"
                    )
                    transformed_frames = []
                    break
                selected = np.flatnonzero(component_ids == component_id)
                rotation, translation = _rigid_transform(
                    np.asarray(reference.get_positions()), positions[selected]
                )
                transformed_frames.append(
                    MolecularFrame(
                        rotation @ frame.origin + translation,
                        rotation @ frame.x_axis,
                        rotation @ frame.y_axis,
                        rotation @ frame.normal,
                    )
                )

            if transformed_frames:
                stack_frame = transformed_frames[0]
                for index, interface in enumerate(vertical_interfaces):
                    previous = transformed_frames[index]
                    current = transformed_frames[index + 1]
                    origin_delta = current.origin - previous.origin
                    actual_values = {
                        "normal_separation": float(
                            np.dot(origin_delta, stack_frame.normal)
                        ),
                        "slip_x": float(np.dot(origin_delta, stack_frame.x_axis)),
                        "slip_y": float(np.dot(origin_delta, stack_frame.y_axis)),
                        "twist_degrees": _signed_angle_degrees(
                            previous.x_axis, current.x_axis, stack_frame.normal
                        ),
                    }
                    expected_values = {
                        "normal_separation": float(interface.normal_separation),
                        "slip_x": float(interface.slip_x),
                        "slip_y": float(interface.slip_y),
                        "twist_degrees": float(interface.twist_degrees),
                    }
                    for quantity, actual in actual_values.items():
                        if quantity == "twist_degrees":
                            difference = _wrapped_angle_error(
                                actual, expected_values[quantity]
                            )
                            tolerance = angle_tolerance_degrees
                        else:
                            difference = actual - expected_values[quantity]
                            tolerance = geometry_tolerance
                        geometry_errors[f"interface_{index}.{quantity}"] = difference
                        if abs(difference) > tolerance:
                            errors.append(
                                f"interface {index} {quantity} differs from the request by "
                                f"{difference:.6g}"
                            )

    if errors:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"
    return ValidationReport(
        passed=not errors,
        status=status,
        errors=tuple(errors),
        warnings=tuple(warnings),
        atom_count=len(assembly),
        expected_atom_count=expected_atom_count,
        component_count=component_count,
        minimum_intercomponent_distance=(
            closest_contact.distance if closest_contact is not None else None
        ),
        closest_contact=closest_contact,
        maximum_rigid_body_error=maximum_rigid_body_error,
        requested_geometry_errors=geometry_errors,
    )


__all__ = ["ClosestContact", "ValidationReport", "validate_assembly"]
