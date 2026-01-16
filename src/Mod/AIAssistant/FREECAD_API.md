# FreeCAD Python API Quick Reference
# Extracted from src/Mod/Part/App/TopoShape.pyi and AppPartPy.cpp

## Creating Primitives

```python
Part.makeBox(length, width, height, pnt=Vector(0,0,0), dir=Vector(0,0,1))
Part.makeCylinder(radius, height, pnt=Vector(0,0,0), dir=Vector(0,0,1), angle=360)
Part.makeCone(radius1, radius2, height, pnt=Vector(0,0,0), dir=Vector(0,0,1), angle=360)
Part.makeSphere(radius, pnt=Vector(0,0,0), dir=Vector(0,0,1), angle1=-90, angle2=90, angle3=360)
Part.makeTorus(radius1, radius2, pnt=Vector(0,0,0), dir=Vector(0,0,1), angle1=0, angle2=360, angle=360)
```

## Boolean Operations (on shapes)

```python
shape.fuse(other)              # Union - returns new shape
shape.cut(other)               # Subtraction - returns new shape
shape.common(other)            # Intersection - returns new shape
shape.fuse((tool1, tool2))     # Multi-fuse
shape.cut((tool1, tool2))      # Multi-cut
```

## Fillets and Chamfers

```python
# IMPORTANT: These return NEW shapes, don't modify in place
# edgeList must be a list of Edge objects from shape.Edges

shape.makeFillet(radius, edgeList)              # Fillet with single radius
shape.makeFillet(radius1, radius2, edgeList)    # Variable radius fillet
shape.makeChamfer(size, edgeList)               # Chamfer with single size
shape.makeChamfer(size1, size2, edgeList)       # Asymmetric chamfer

# Example - fillet all edges of a box:
box = Part.makeBox(100, 100, 50)
filleted = box.makeFillet(5, box.Edges)  # 5mm radius on all edges
```

## Extrusion and Revolution

```python
shape.extrude(vector)                    # Extrude along vector
shape.revolve(center, axis, angle)       # Revolve around axis (angle in degrees)

# Example:
face.extrude(FreeCAD.Vector(0, 0, 100))  # Extrude face 100mm in Z
```

## Wire and Face Creation

```python
Part.makePolygon([pt1, pt2, pt3, pt1])   # Closed wire from points (repeat first point)
Part.makeLine(pt1, pt2)                   # Line edge
Part.makeCircle(radius, center=Vector(0,0,0), normal=Vector(0,0,1), angle1=0, angle2=360)
Part.Face(wire)                           # Create face from closed wire
```

## Document Objects (Parametric)

```python
# These create parametric objects in the document
doc.addObject("Part::Box", "Name")        # Has .Length, .Width, .Height
doc.addObject("Part::Cylinder", "Name")   # Has .Radius, .Height
doc.addObject("Part::Sphere", "Name")     # Has .Radius
doc.addObject("Part::Cone", "Name")       # Has .Radius1, .Radius2, .Height
doc.addObject("Part::Torus", "Name")      # Has .Radius1, .Radius2

# Boolean operations (parametric)
doc.addObject("Part::Cut", "Name")        # Set .Base and .Tool
doc.addObject("Part::Fuse", "Name")       # Set .Base and .Tool
doc.addObject("Part::Common", "Name")     # Set .Base and .Tool
doc.addObject("Part::MultiFuse", "Name")  # Set .Shapes = [obj1, obj2, ...]
doc.addObject("Part::MultiCommon", "Name")

# Generic Part (for computed shapes)
doc.addObject("Part::Feature", "Name")    # Set .Shape = computed_shape
```

## Placement

```python
obj.Placement.Base = FreeCAD.Vector(x, y, z)
obj.Placement.Rotation = FreeCAD.Rotation(axis, angle_degrees)
obj.Placement.Rotation = FreeCAD.Rotation(yaw, pitch, roll)  # Euler angles in degrees
```

## Common Patterns

```python
# Fillet a parametric box (must use Part::Feature for result)
box = doc.addObject("Part::Box", "Box")
box.Length, box.Width, box.Height = 100, 80, 50
doc.recompute()

filleted_shape = box.Shape.makeFillet(5, box.Shape.Edges)
result = doc.addObject("Part::Feature", "FilletedBox")
result.Shape = filleted_shape

# Boolean cut with door opening
wall = doc.addObject("Part::Box", "Wall")
door = doc.addObject("Part::Box", "DoorCutout")
wall_with_door = doc.addObject("Part::Cut", "WallWithDoor")
wall_with_door.Base = wall
wall_with_door.Tool = door
```
