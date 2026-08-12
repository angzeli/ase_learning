"""High-level rigid-body construction of finite molecular assemblies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from ase import Atoms

from frame import MolecularFrame
from transforms import align_frames, rotate_about_axis, rotation_matrix, translate


def _finite_scalar(value: float, name: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _local_translation(value: Sequence[float]) -> tuple[float, float, float]:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("translation_local must contain three finite distances in Å")
    return tuple(float(component) for component in vector)


@dataclass(frozen=True)
class Component:
    """One rigid monomer and its explicitly defined local molecular frame."""

    atoms: Atoms
    frame: MolecularFrame
    label: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.atoms, Atoms):
            raise TypeError("atoms must be an ase.Atoms object")
        if not isinstance(self.frame, MolecularFrame):
            raise TypeError("frame must be a MolecularFrame object")
        if len(self.atoms) == 0:
            raise ValueError("a component must contain at least one atom")
        if not np.all(np.isfinite(self.atoms.get_positions())):
            raise ValueError("component coordinates must be finite")
        if self.label is not None and not isinstance(self.label, str):
            raise TypeError("label must be a string or None")
        if self.source is not None and not isinstance(self.source, str):
            raise TypeError("source must be a string or None")


@dataclass(frozen=True)
class VerticalInterface:
    """Placement of the next stack component relative to the previous one.

    Distances are in Å and ``twist_degrees`` is a right-handed rotation about
    the common positive plane normal. Slip is resolved along the first
    component's local in-plane axes. Interface values are relative; builders
    accumulate them through an ordered sequence.
    """

    normal_separation: float
    slip_x: float = 0.0
    slip_y: float = 0.0
    twist_degrees: float = 0.0

    def __post_init__(self) -> None:
        separation = _finite_scalar(self.normal_separation, "normal_separation")
        if separation <= 0.0:
            raise ValueError("normal_separation must be greater than zero")
        object.__setattr__(self, "normal_separation", separation)
        object.__setattr__(self, "slip_x", _finite_scalar(self.slip_x, "slip_x"))
        object.__setattr__(self, "slip_y", _finite_scalar(self.slip_y, "slip_y"))
        object.__setattr__(
            self, "twist_degrees", _finite_scalar(self.twist_degrees, "twist_degrees")
        )

    def to_dict(self) -> dict[str, float]:
        """Return serialisable interface parameters."""

        return {
            "normal_separation": self.normal_separation,
            "slip_x": self.slip_x,
            "slip_y": self.slip_y,
            "twist_degrees": self.twist_degrees,
        }


@dataclass(frozen=True)
class LateralPlacement:
    """Explicit placement of one guest in a host molecular frame.

    The guest frame is first aligned to the host frame. Its origin is then
    translated by ``translation_local=(x, y, normal)`` in Å, and it is rotated
    by ``rotation_degrees`` around its origin and the host plane normal.
    """

    component: Component
    translation_local: tuple[float, float, float] = field(
        default_factory=lambda: (0.0, 0.0, 0.0)
    )
    rotation_degrees: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.component, Component):
            raise TypeError("component must be a Component object")
        object.__setattr__(
            self, "translation_local", _local_translation(self.translation_local)
        )
        object.__setattr__(
            self,
            "rotation_degrees",
            _finite_scalar(self.rotation_degrees, "rotation_degrees"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return serialisable placement parameters."""

        return {
            "translation_local": list(self.translation_local),
            "rotation_degrees": self.rotation_degrees,
        }


def _component_metadata(
    component: Component,
    component_id: int,
    transform: dict[str, object],
    transformed_frame: MolecularFrame,
) -> dict[str, object]:
    return {
        "component_id": component_id,
        "label": component.label or f"component_{component_id}",
        "source": component.source,
        "atom_count": len(component.atoms),
        "formula": component.atoms.get_chemical_formula(),
        "transform": transform,
        "frame": transformed_frame.to_dict(),
    }


def _combine(parts: Sequence[Atoms], component_ids: Sequence[int]) -> Atoms:
    if len(parts) != len(component_ids) or not parts:
        raise ValueError(
            "parts and component_ids must be non-empty and have equal length"
        )
    combined = parts[0].copy()
    for part in parts[1:]:
        combined.extend(part)
    ids = np.concatenate(
        [
            np.full(len(part), component_id, dtype=int)
            for part, component_id in zip(parts, component_ids)
        ]
    )
    combined.set_array("component_id", ids)
    return combined


def _rotated_frame(
    frame: MolecularFrame,
    reference_frame: MolecularFrame,
    angle_degrees: float,
    displacement: np.ndarray,
) -> MolecularFrame:
    matrix = rotation_matrix(reference_frame.normal, angle_degrees)
    return MolecularFrame(
        reference_frame.origin + displacement,
        matrix @ reference_frame.x_axis,
        matrix @ reference_frame.y_axis,
        reference_frame.normal,
    )


def build_vertical_stack(
    components: Sequence[Component], interfaces: Sequence[VerticalInterface]
) -> Atoms:
    """Build an ordered homogeneous or heterogeneous finite vertical stack.

    For ``N`` components, exactly ``N - 1`` interfaces are required. Interface
    ``i`` places component ``i + 1`` relative to component ``i``. Separations,
    slips, and twists are cumulative in the first component's molecular frame.
    Input components are never mutated.
    """

    ordered_components = tuple(components)
    ordered_interfaces = tuple(interfaces)
    if not ordered_components:
        raise ValueError("components must contain at least one Component")
    if any(not isinstance(component, Component) for component in ordered_components):
        raise TypeError("components must contain only Component objects")
    if len(ordered_interfaces) != len(ordered_components) - 1:
        raise ValueError("an N-component stack requires exactly N - 1 interfaces")
    if any(
        not isinstance(interface, VerticalInterface) for interface in ordered_interfaces
    ):
        raise TypeError("interfaces must contain only VerticalInterface objects")

    reference_frame = ordered_components[0].frame
    placed_parts = [ordered_components[0].atoms.copy()]
    metadata = [
        _component_metadata(
            ordered_components[0],
            0,
            {
                "translation_local": [0.0, 0.0, 0.0],
                "twist_degrees": 0.0,
            },
            reference_frame,
        )
    ]
    cumulative_local = np.zeros(3, dtype=float)
    cumulative_twist = 0.0

    for component_id, (component, interface) in enumerate(
        zip(ordered_components[1:], ordered_interfaces), start=1
    ):
        cumulative_local += np.array(
            [interface.slip_x, interface.slip_y, interface.normal_separation]
        )
        cumulative_twist += interface.twist_degrees
        displacement = reference_frame.vector_to_cartesian(cumulative_local)

        placed = align_frames(component.atoms, component.frame, reference_frame)
        placed = rotate_about_axis(
            placed,
            reference_frame.normal,
            cumulative_twist,
            center=reference_frame.origin,
        )
        placed = translate(placed, displacement)
        placed_parts.append(placed)
        transformed_frame = _rotated_frame(
            component.frame,
            reference_frame,
            cumulative_twist,
            displacement,
        )
        metadata.append(
            _component_metadata(
                component,
                component_id,
                {
                    "translation_local": cumulative_local.tolist(),
                    "twist_degrees": cumulative_twist,
                },
                transformed_frame,
            )
        )

    assembly = _combine(placed_parts, list(range(len(placed_parts))))
    assembly.info["assembly"] = {
        "schema_version": 1,
        "assembly_type": "vertical",
        "component_count": len(placed_parts),
        "reference_frame": reference_frame.to_dict(),
        "components": metadata,
        "interfaces": [interface.to_dict() for interface in ordered_interfaces],
    }
    return assembly


def add_lateral_components(
    host: Atoms,
    host_frame: MolecularFrame,
    placements: Sequence[LateralPlacement],
) -> Atoms:
    """Add explicitly placed lateral components to an existing finite host.

    Existing ``component_id`` values are preserved. If the host has no such
    array, it is treated as component 0. This helper is the intended route for
    composing mixed vertical and horizontal motifs.
    """

    if not isinstance(host, Atoms) or len(host) == 0:
        raise TypeError("host must be a non-empty ase.Atoms object")
    if not isinstance(host_frame, MolecularFrame):
        raise TypeError("host_frame must be a MolecularFrame object")
    ordered_placements = tuple(placements)
    if any(
        not isinstance(placement, LateralPlacement) for placement in ordered_placements
    ):
        raise TypeError("placements must contain only LateralPlacement objects")
    if not np.all(np.isfinite(host.get_positions())):
        raise ValueError("host coordinates must be finite")

    host_part = host.copy()
    if "component_id" in host_part.arrays:
        host_ids = np.asarray(host_part.arrays["component_id"])
        if host_ids.shape != (len(host_part),) or not np.issubdtype(
            host_ids.dtype, np.integer
        ):
            raise ValueError(
                "host component_id must be a one-dimensional integer array"
            )
        if np.any(host_ids < 0):
            raise ValueError("host component_id values must be non-negative")
        next_component_id = int(host_ids.max()) + 1
    else:
        host_ids = np.zeros(len(host_part), dtype=int)
        host_part.set_array("component_id", host_ids)
        next_component_id = 1

    placed_parts: list[Atoms] = [host_part]
    part_ids: list[int] = [0]
    new_metadata: list[dict[str, object]] = []
    for offset, placement in enumerate(ordered_placements):
        component_id = next_component_id + offset
        cartesian_translation = host_frame.vector_to_cartesian(
            placement.translation_local
        )
        placed = align_frames(
            placement.component.atoms, placement.component.frame, host_frame
        )
        placed = rotate_about_axis(
            placed,
            host_frame.normal,
            placement.rotation_degrees,
            center=host_frame.origin,
        )
        placed = translate(placed, cartesian_translation)
        placed_parts.append(placed)
        part_ids.append(component_id)

        matrix = rotation_matrix(host_frame.normal, placement.rotation_degrees)
        transformed_frame = MolecularFrame(
            host_frame.origin + cartesian_translation,
            matrix @ host_frame.x_axis,
            matrix @ host_frame.y_axis,
            host_frame.normal,
        )
        new_metadata.append(
            _component_metadata(
                placement.component,
                component_id,
                placement.to_dict(),
                transformed_frame,
            )
        )

    combined = placed_parts[0].copy()
    all_ids = [host_ids.astype(int, copy=True)]
    for part, component_id in zip(placed_parts[1:], part_ids[1:]):
        combined.extend(part)
        all_ids.append(np.full(len(part), component_id, dtype=int))
    combined.set_array("component_id", np.concatenate(all_ids))

    existing_metadata = host.info.get("assembly")
    if isinstance(existing_metadata, dict):
        old_components = list(existing_metadata.get("components", []))
        history = list(existing_metadata.get("history", []))
        history.append(existing_metadata.get("assembly_type", "unknown"))
        assembly_type = "mixed"
    else:
        unique_host_ids = sorted(int(value) for value in np.unique(host_ids))
        old_components = [
            {
                "component_id": component_id,
                "label": f"component_{component_id}",
                "source": None,
                "atom_count": int(np.count_nonzero(host_ids == component_id)),
                "formula": None,
                "transform": None,
                "frame": host_frame.to_dict() if component_id == 0 else None,
            }
            for component_id in unique_host_ids
        ]
        history = []
        assembly_type = "horizontal"
    combined.info["assembly"] = {
        "schema_version": 1,
        "assembly_type": assembly_type,
        "component_count": len(np.unique(combined.arrays["component_id"])),
        "reference_frame": host_frame.to_dict(),
        "components": old_components + new_metadata,
        "placements": [placement.to_dict() for placement in ordered_placements],
        "history": history,
    }
    return combined


def build_horizontal_assembly(
    host: Component, placements: Sequence[LateralPlacement]
) -> Atoms:
    """Build one host plus any number of explicit local-frame placements."""

    if not isinstance(host, Component):
        raise TypeError("host must be a Component object")
    host_atoms = host.atoms.copy()
    host_atoms.set_array("component_id", np.zeros(len(host_atoms), dtype=int))
    host_atoms.info["assembly"] = {
        "schema_version": 1,
        "assembly_type": "horizontal_host",
        "component_count": 1,
        "reference_frame": host.frame.to_dict(),
        "components": [
            _component_metadata(
                host,
                0,
                {"translation_local": [0.0, 0.0, 0.0], "rotation_degrees": 0.0},
                host.frame,
            )
        ],
    }
    result = add_lateral_components(host_atoms, host.frame, placements)
    result.info["assembly"]["assembly_type"] = "horizontal"
    result.info["assembly"]["history"] = []
    return result


__all__ = [
    "Component",
    "LateralPlacement",
    "VerticalInterface",
    "add_lateral_components",
    "build_horizontal_assembly",
    "build_vertical_stack",
]
