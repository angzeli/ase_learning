from __future__ import annotations

import numpy as np

from assembly import (
    Component,
    LateralPlacement,
    VerticalInterface,
    build_horizontal_assembly,
    build_vertical_stack,
)
from validation import validate_assembly


def test_valid_structure_passes(component: Component) -> None:
    dimer = build_vertical_stack([component, component], [VerticalInterface(3.4)])
    report = validate_assembly(dimer, [component.atoms, component.atoms])

    assert report.status == "pass"
    assert report.passed
    assert report.minimum_intercomponent_distance is not None
    assert report.maximum_rigid_body_error is not None
    assert report.maximum_rigid_body_error < 1.0e-12


def test_severe_intercomponent_clash_fails(component: Component) -> None:
    clashing = build_horizontal_assembly(
        component, [LateralPlacement(component, (0.05, 0.0, 0.0))]
    )
    report = validate_assembly(clashing, [component.atoms, component.atoms])

    assert report.status == "fail"
    assert not report.passed
    assert report.closest_contact is not None
    assert report.closest_contact.distance < 0.8
    assert any("clash" in error for error in report.errors)


def test_rigid_body_distortion_is_detected(component: Component) -> None:
    dimer = build_vertical_stack([component, component], [VerticalInterface(3.4)])
    distorted = dimer.copy()
    first_guest_atom = len(component.atoms)
    distorted.positions[first_guest_atom, 0] += 0.25
    report = validate_assembly(distorted, [component.atoms, component.atoms])

    assert not report.passed
    assert report.maximum_rigid_body_error is not None
    assert report.maximum_rigid_body_error > 0.1
    assert any("not rigid" in error for error in report.errors)


def test_nonfinite_coordinate_is_rejected(component: Component) -> None:
    dimer = build_vertical_stack([component, component], [VerticalInterface(3.4)])
    invalid = dimer.copy()
    invalid.positions[0, 2] = np.nan
    report = validate_assembly(invalid, [component.atoms, component.atoms])

    assert not report.passed
    assert any("non-finite" in error for error in report.errors)


def test_missing_or_invalid_component_ids_fail(component: Component) -> None:
    dimer = build_vertical_stack([component, component], [VerticalInterface(3.4)])
    missing = dimer.copy()
    del missing.arrays["component_id"]
    report = validate_assembly(missing, [component.atoms, component.atoms])
    assert not report.passed

    noncontiguous = dimer.copy()
    noncontiguous.set_array(
        "component_id", np.repeat([0, 2], len(component.atoms)).astype(int)
    )
    report = validate_assembly(noncontiguous, [component.atoms, component.atoms])
    assert not report.passed
    assert any("contiguous" in error for error in report.errors)
