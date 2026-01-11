#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Steel Roof Truss Generator for FreeCAD

Creates a 3D structural model of a symmetrical steel roof truss using
point-to-point coordinates and member assignments.

Specifications:
- Total Span: 18300mm (18.3m)
- Apex Height: 1700mm at center
- Symmetry Axis: X = 9150mm
- Chord Profile: SHS 100x100x8
- Web Profile: SHS 90x90x8

Usage:
    Run this script in FreeCAD's Python console or as a macro.
"""

import Part
import FreeCAD

def create_steel_roof_truss():
    """Create a symmetrical steel roof truss model."""

    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("RoofTruss")

    # Define all nodes (converting mm to mm, Z=0 for 2D truss in XZ plane)
    # Bottom Chord Nodes (Left Half)
    N1 = FreeCAD.Vector(0, 0, 0)
    N2 = FreeCAD.Vector(3050, 0, 0)
    N3 = FreeCAD.Vector(6100, 0, 0)
    N4 = FreeCAD.Vector(9150, 0, 0)  # Center

    # Top Chord Nodes (Left Half)
    T1 = FreeCAD.Vector(0, 0, 1000)
    T2 = FreeCAD.Vector(1525, 0, 1116)
    T3 = FreeCAD.Vector(3050, 0, 1233)
    T4 = FreeCAD.Vector(4575, 0, 1350)
    T5 = FreeCAD.Vector(6100, 0, 1467)
    T6 = FreeCAD.Vector(7625, 0, 1583)
    T7 = FreeCAD.Vector(9150, 0, 1700)  # Apex

    # Mirror nodes for right half (across X = 9150)
    # Bottom Chord (Right Half)
    N5 = FreeCAD.Vector(12200, 0, 0)  # Mirror of N3
    N6 = FreeCAD.Vector(15250, 0, 0)  # Mirror of N2
    N7 = FreeCAD.Vector(18300, 0, 0)  # Mirror of N1

    # Top Chord (Right Half)
    T8 = FreeCAD.Vector(10725, 0, 1583)   # Mirror of T6
    T9 = FreeCAD.Vector(12200, 0, 1467)   # Mirror of T5
    T10 = FreeCAD.Vector(13775, 0, 1350)  # Mirror of T4
    T11 = FreeCAD.Vector(15250, 0, 1233)  # Mirror of T3
    T12 = FreeCAD.Vector(16825, 0, 1116)  # Mirror of T2
    T13 = FreeCAD.Vector(18300, 0, 1000)  # Mirror of T1

    def create_member(name, start, end, profile_size):
        """Create a line representing a structural member."""
        line = Part.makeLine(start, end)
        member = doc.addObject("Part::Feature", name)
        member.Shape = line
        return member

    # Create lists for each member type
    chord_members = []
    web_members = []

    # === BOTTOM CHORD (SHS 100x100x8) ===
    # Left half
    chord_members.append(create_member("BC_N1_N2", N1, N2, "SHS100x100x8"))
    chord_members.append(create_member("BC_N2_N3", N2, N3, "SHS100x100x8"))
    chord_members.append(create_member("BC_N3_N4", N3, N4, "SHS100x100x8"))
    # Right half (mirrored)
    chord_members.append(create_member("BC_N4_N5", N4, N5, "SHS100x100x8"))
    chord_members.append(create_member("BC_N5_N6", N5, N6, "SHS100x100x8"))
    chord_members.append(create_member("BC_N6_N7", N6, N7, "SHS100x100x8"))

    # === TOP CHORD (SHS 100x100x8) ===
    # Left half
    chord_members.append(create_member("TC_T1_T2", T1, T2, "SHS100x100x8"))
    chord_members.append(create_member("TC_T2_T3", T2, T3, "SHS100x100x8"))
    chord_members.append(create_member("TC_T3_T4", T3, T4, "SHS100x100x8"))
    chord_members.append(create_member("TC_T4_T5", T4, T5, "SHS100x100x8"))
    chord_members.append(create_member("TC_T5_T6", T5, T6, "SHS100x100x8"))
    chord_members.append(create_member("TC_T6_T7", T6, T7, "SHS100x100x8"))
    # Right half (mirrored)
    chord_members.append(create_member("TC_T7_T8", T7, T8, "SHS100x100x8"))
    chord_members.append(create_member("TC_T8_T9", T8, T9, "SHS100x100x8"))
    chord_members.append(create_member("TC_T9_T10", T9, T10, "SHS100x100x8"))
    chord_members.append(create_member("TC_T10_T11", T10, T11, "SHS100x100x8"))
    chord_members.append(create_member("TC_T11_T12", T11, T12, "SHS100x100x8"))
    chord_members.append(create_member("TC_T12_T13", T12, T13, "SHS100x100x8"))

    # === VERTICAL MEMBERS (SHS 90x90x8) ===
    # Left half
    web_members.append(create_member("V_N1_T1", N1, T1, "SHS90x90x8"))
    web_members.append(create_member("V_N2_T3", N2, T3, "SHS90x90x8"))
    web_members.append(create_member("V_N3_T5", N3, T5, "SHS90x90x8"))
    web_members.append(create_member("V_N4_T7", N4, T7, "SHS90x90x8"))
    # Right half (mirrored)
    web_members.append(create_member("V_N5_T9", N5, T9, "SHS90x90x8"))
    web_members.append(create_member("V_N6_T11", N6, T11, "SHS90x90x8"))
    web_members.append(create_member("V_N7_T13", N7, T13, "SHS90x90x8"))

    # === DIAGONAL MEMBERS (SHS 90x90x8) ===
    # Left half
    web_members.append(create_member("D_N1_T2", N1, T2, "SHS90x90x8"))
    web_members.append(create_member("D_N2_T2", N2, T2, "SHS90x90x8"))
    web_members.append(create_member("D_N2_T4", N2, T4, "SHS90x90x8"))
    web_members.append(create_member("D_N3_T4", N3, T4, "SHS90x90x8"))
    web_members.append(create_member("D_N3_T6", N3, T6, "SHS90x90x8"))
    web_members.append(create_member("D_N4_T6", N4, T6, "SHS90x90x8"))
    # Right half (mirrored)
    web_members.append(create_member("D_N4_T8", N4, T8, "SHS90x90x8"))
    web_members.append(create_member("D_N5_T8", N5, T8, "SHS90x90x8"))
    web_members.append(create_member("D_N5_T10", N5, T10, "SHS90x90x8"))
    web_members.append(create_member("D_N6_T10", N6, T10, "SHS90x90x8"))
    web_members.append(create_member("D_N6_T12", N6, T12, "SHS90x90x8"))
    web_members.append(create_member("D_N7_T12", N7, T12, "SHS90x90x8"))

    # Set colors for visualization
    # Chords - Blue
    for member in chord_members:
        if hasattr(member, 'ViewObject') and member.ViewObject:
            member.ViewObject.LineColor = (0.0, 0.4, 0.8)
            member.ViewObject.LineWidth = 3.0

    # Web members - Orange
    for member in web_members:
        if hasattr(member, 'ViewObject') and member.ViewObject:
            member.ViewObject.LineColor = (0.9, 0.5, 0.1)
            member.ViewObject.LineWidth = 2.0

    # Create a group to organize the truss
    truss_group = doc.addObject("App::DocumentObjectGroup", "SteelRoofTruss")
    for m in chord_members + web_members:
        truss_group.addObject(m)

    # Fit view if GUI is available
    if FreeCAD.GuiUp:
        import FreeCADGui
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        FreeCADGui.ActiveDocument.ActiveView.viewFront()

    # Print summary
    print("=" * 60)
    print("STEEL ROOF TRUSS MODEL CREATED")
    print("=" * 60)
    print(f"Total Span: 18300mm (18.3m)")
    print(f"Height at Apex: 1700mm (1.7m)")
    print(f"Symmetry Axis: X = 9150mm")
    print("-" * 60)
    print("MEMBER COUNT:")
    print(f"  Bottom Chord segments: 6 (SHS 100x100x8)")
    print(f"  Top Chord segments: 12 (SHS 100x100x8)")
    print(f"  Vertical members: 7 (SHS 90x90x8)")
    print(f"  Diagonal members: 12 (SHS 90x90x8)")
    print(f"  TOTAL MEMBERS: {len(chord_members) + len(web_members)}")
    print("-" * 60)
    print("PROFILES:")
    print("  Chords (Blue): SHS 100x100x8")
    print("  Webs (Orange): SHS 90x90x8")
    print("=" * 60)

    return truss_group, chord_members, web_members


if __name__ == "__main__":
    create_steel_roof_truss()
