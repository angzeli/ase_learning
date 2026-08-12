from __future__ import annotations

import numpy as np

from assembly import (
    Component,
    LateralPlacement,
    VerticalInterface,
    add_lateral_components,
    build_horizontal_assembly,
    build_vertical_stack,
)
from frame import define_frame
from transforms import rotate_about_axis, rotation_matrix
from validation import validate_assembly


def test_vertical_dimer_geometry_and_identity(component: Component) -> None:
    interface = VerticalInterface(3.4, slip_x=1.1, slip_y=-0.4, twist_degrees=27.0)
    dimer = build_vertical_stack([component, component], [interface])
    metadata = dimer.info["assembly"]

    assert len(dimer) == 2 * len(component.atoms)
    assert np.array_equal(
        dimer.arrays["component_id"],
        np.repeat([0, 1], len(component.atoms)),
    )
    assert np.allclose(
        metadata["components"][1]["transform"]["translation_local"], [1.1, -0.4, 3.4]
    )
    assert metadata["components"][1]["transform"]["twist_degrees"] == 27.0

    report = validate_assembly(
        dimer,
        [component.atoms, component.atoms],
        reference_frames=[component.frame, component.frame],
        vertical_interfaces=[interface],
    )
    assert report.passed, report.errors
    assert (
        max(abs(value) for value in report.requested_geometry_errors.values()) < 1.0e-10
    )


def test_vertical_trimer_uses_relative_interfaces(component: Component) -> None:
    interfaces = [
        VerticalInterface(3.2, slip_x=0.5, twist_degrees=10.0),
        VerticalInterface(3.6, slip_x=-0.2, slip_y=0.4, twist_degrees=-25.0),
    ]
    trimer = build_vertical_stack([component, component, component], interfaces)
    transforms = [entry["transform"] for entry in trimer.info["assembly"]["components"]]

    assert len(trimer) == 3 * len(component.atoms)
    assert np.allclose(transforms[2]["translation_local"], [0.3, 0.4, 6.8])
    assert transforms[2]["twist_degrees"] == -15.0

    report = validate_assembly(
        trimer,
        [component.atoms] * 3,
        reference_frames=[component.frame] * 3,
        vertical_interfaces=interfaces,
    )
    assert report.passed, report.errors


def test_heterogeneous_stack_aligns_non_axis_oriented_frame(
    component: Component,
) -> None:
    matrix = rotation_matrix([1.0, 1.0, 0.5], 43.0)
    rotated_atoms = rotate_about_axis(
        component.atoms, [1.0, 1.0, 0.5], 43.0, center=[0.0, 0.0, 0.0]
    )
    guest_frame = define_frame(
        rotated_atoms,
        [0, 1, 2, 3],
        [0, 1],
        normal_reference=matrix @ component.frame.normal,
    )
    guest = Component(rotated_atoms, guest_frame, label="B")
    interface = VerticalInterface(3.5, slip_y=0.7, twist_degrees=13.0)
    stack = build_vertical_stack([component, guest, component], [interface, interface])

    report = validate_assembly(
        stack,
        [component.atoms, guest.atoms, component.atoms],
        reference_frames=[component.frame, guest.frame, component.frame],
        vertical_interfaces=[interface, interface],
    )
    assert report.passed, report.errors
    assert [entry["label"] for entry in stack.info["assembly"]["components"]] == [
        "A",
        "B",
        "A",
    ]


def test_horizontal_dimer_and_multiple_partners(component: Component) -> None:
    placements = [
        LateralPlacement(component, (8.0, 0.0, 0.0), 30.0),
        LateralPlacement(component, (-8.0, 2.0, 0.0), -45.0),
    ]
    assembly = build_horizontal_assembly(component, placements)

    assert len(assembly) == 3 * len(component.atoms)
    assert np.array_equal(
        assembly.arrays["component_id"],
        np.repeat([0, 1, 2], len(component.atoms)),
    )
    frames = assembly.info["assembly"]["components"]
    assert np.allclose(
        frames[1]["frame"]["origin"], component.frame.point_to_cartesian([8, 0, 0])
    )
    expected_x = rotation_matrix(component.frame.normal, 30.0) @ component.frame.x_axis
    assert np.allclose(frames[1]["frame"]["x_axis"], expected_x)


def test_mixed_vertical_and_lateral_composition(component: Component) -> None:
    stack = build_vertical_stack(
        [component, component], [VerticalInterface(3.5, slip_x=0.5)]
    )
    mixed = add_lateral_components(
        stack,
        component.frame,
        [LateralPlacement(component, (8.0, 0.0, 0.0), 90.0)],
    )

    assert mixed.info["assembly"]["assembly_type"] == "mixed"
    assert np.array_equal(
        mixed.arrays["component_id"],
        np.repeat([0, 1, 2], len(component.atoms)),
    )
    report = validate_assembly(mixed, [component.atoms] * 3)
    assert report.passed, report.errors


def test_builders_are_deterministic_and_do_not_mutate_inputs(
    component: Component,
) -> None:
    original_positions = component.atoms.get_positions().copy()
    interface = VerticalInterface(3.3, slip_x=0.2, twist_degrees=11.0)
    first = build_vertical_stack([component, component], [interface])
    second = build_vertical_stack([component, component], [interface])

    assert np.array_equal(first.positions, second.positions)
    assert np.array_equal(component.atoms.positions, original_positions)
