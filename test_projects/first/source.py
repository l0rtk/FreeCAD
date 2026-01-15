# FreeCAD AI Source - Unnamed
# Created: 2026-01-15 20:04:31
#
# This script can regenerate the document.
# Run in FreeCAD's Python console or as a macro.
#

import FreeCAD
import Part

doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")


# === 2026-01-15 20:04:52 ===
box = doc.addObject("Part::Box", "Box")
box.Label = "Box"
box.Length = 100
box.Width = 100
box.Height = 100

doc.recompute()

# === 2026-01-15 20:05:11 ===
# Create a pyramid with square base matching the box (100x100) and height 100
# Position it above the box (at Z=100)
base_size = 100
height = 100

# Define pyramid vertices: 4 base corners + 1 apex
v0 = FreeCAD.Vector(0, 0, 100)          # base corner
v1 = FreeCAD.Vector(100, 0, 100)        # base corner
v2 = FreeCAD.Vector(100, 100, 100)      # base corner
v3 = FreeCAD.Vector(0, 100, 100)        # base corner
v4 = FreeCAD.Vector(50, 50, 200)        # apex (centered above base)

# Create faces
face1 = Part.Face(Part.makePolygon([v0, v1, v4, v0]))  # front
face2 = Part.Face(Part.makePolygon([v1, v2, v4, v1]))  # right
face3 = Part.Face(Part.makePolygon([v2, v3, v4, v2]))  # back
face4 = Part.Face(Part.makePolygon([v3, v0, v4, v3]))  # left
face5 = Part.Face(Part.makePolygon([v0, v3, v2, v1, v0]))  # base

# Create solid from shell
shell = Part.Shell([face1, face2, face3, face4, face5])
solid = Part.Solid(shell)

pyramid = doc.addObject("Part::Feature", "Pyramid")
pyramid.Label = "Pyramid"
pyramid.Shape = solid

doc.recompute()

# === 2026-01-15 20:06:10 ===
# Box with doubled height (100x100x200)
box = doc.addObject("Part::Box", "Box")
box.Label = "Box"
box.Length = 100
box.Width = 100
box.Height = 200

# Pyramid above the taller box
v0 = FreeCAD.Vector(0, 0, 200)
v1 = FreeCAD.Vector(100, 0, 200)
v2 = FreeCAD.Vector(100, 100, 200)
v3 = FreeCAD.Vector(0, 100, 200)
v4 = FreeCAD.Vector(50, 50, 300)

face1 = Part.Face(Part.makePolygon([v0, v1, v4, v0]))
face2 = Part.Face(Part.makePolygon([v1, v2, v4, v1]))
face3 = Part.Face(Part.makePolygon([v2, v3, v4, v2]))
face4 = Part.Face(Part.makePolygon([v3, v0, v4, v3]))
face5 = Part.Face(Part.makePolygon([v0, v3, v2, v1, v0]))

shell = Part.Shell([face1, face2, face3, face4, face5])
solid = Part.Solid(shell)

pyramid = doc.addObject("Part::Feature", "Pyramid")
pyramid.Label = "Pyramid"
pyramid.Shape = solid

doc.recompute()

# === 2026-01-15 20:06:29 ===
doc.removeObject("Box")

doc.recompute()
