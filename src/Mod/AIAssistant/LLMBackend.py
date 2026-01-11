# SPDX-License-Identifier: LGPL-2.1-or-later
"""
LLM Backend - Handles communication with AI services.
Supports Nakle API (default), with extensibility for other providers.
"""

import json
import urllib.request
import urllib.error
import FreeCAD

# Default API endpoint (Nakle)
DEFAULT_API_URL = "http://20.64.149.209/chat/completions"
DEFAULT_MODEL = "sonnet"

SYSTEM_PROMPT = """You are an AI assistant integrated into FreeCAD, a parametric 3D CAD modeler.
Your task is to convert natural language requests into executable FreeCAD Python code.

CRITICAL RULES:
1. Return ONLY executable Python code - no markdown, no explanations, no comments explaining what you're doing
2. Always ensure a document exists: doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
3. Always end with doc.recompute()
4. Use millimeters for all dimensions (FreeCAD default unit)
5. Use descriptive object names

AVAILABLE MODULES AND PATTERNS:

## Basic Shapes (Part module)
```
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
box = Part.makeBox(length, width, height)
Part.show(box, "MyBox")
doc.recompute()
```

Part primitives:
- Part.makeBox(length, width, height)
- Part.makeCylinder(radius, height)
- Part.makeCone(radius1, radius2, height)
- Part.makeSphere(radius)
- Part.makeTorus(radius1, radius2)

## Positioning Objects
```
# Move an object
shape.translate(FreeCAD.Vector(x, y, z))

# After Part.show(), access via document
doc.getObject("Name").Placement.Base = FreeCAD.Vector(x, y, z)
```

## Boolean Operations
```
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
box = Part.makeBox(100, 100, 100)
cylinder = Part.makeCylinder(30, 120)
cylinder.translate(FreeCAD.Vector(50, 50, -10))

# Boolean operations on shapes
result = box.cut(cylinder)      # Subtraction
result = box.fuse(cylinder)     # Union
result = box.common(cylinder)   # Intersection

Part.show(result, "BooleanResult")
doc.recompute()
```

## Multiple Objects
```
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
for i in range(5):
    box = Part.makeBox(20, 20, 100)
    box.translate(FreeCAD.Vector(i * 40, 0, 0))
    Part.show(box, f"Column_{i}")
doc.recompute()
```

## BIM/Architecture (Arch module)
```
import Arch
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
wall = Arch.makeWall(None, length=4000, width=200, height=3000)
doc.recompute()
```

## Precast Concrete (BIM.ArchPrecast)
```
from BIM import ArchPrecast
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
beam = ArchPrecast.makePrecast("Beam", length=2000, width=300, height=400)
pillar = ArchPrecast.makePrecast("Pillar", length=400, width=400, height=3000)
slab = ArchPrecast.makePrecast("Slab", length=6000, width=1200, height=200, slabtype="Champagne")
doc.recompute()
```

## Extrusions
```
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
# Create a circle and extrude it
circle = Part.makeCircle(50)
wire = Part.Wire(circle)
face = Part.Face(wire)
solid = face.extrude(FreeCAD.Vector(0, 0, 100))
Part.show(solid, "ExtrudedCircle")
doc.recompute()
```

Remember: Output ONLY the Python code, nothing else."""


class LLMBackend:
    """Handles LLM API communication."""

    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = api_url or self._get_pref("ApiUrl", DEFAULT_API_URL)
        self.model = model or self._get_pref("Model", DEFAULT_MODEL)

    def _get_pref(self, key: str, default: str) -> str:
        """Get preference value."""
        try:
            return FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/AIAssistant"
            ).GetString(key, default)
        except Exception:
            return default

    def chat(self, user_message: str, context: str = "", history: list = None) -> str:
        """
        Send a message to the LLM and get a response.

        Args:
            user_message: The user's natural language request
            context: Optional document context string
            history: Optional conversation history

        Returns:
            Generated Python code as a string
        """
        # Build system prompt with context
        system = SYSTEM_PROMPT
        if context:
            system += f"\n\nCURRENT DOCUMENT STATE:\n{context}"

        # Build messages array
        messages = [{"role": "system", "content": system}]

        # Add conversation history (last few exchanges)
        if history:
            messages.extend(history[-6:])  # Last 3 exchanges

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Make API request
        payload = {
            "model": self.model,
            "messages": messages,
            "timeout": 120
        }

        headers = {"Content-Type": "application/json"}

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.api_url, data=data, headers=headers)

            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
                return self._clean_response(result["choices"][0]["message"]["content"])

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()[:200]
            FreeCAD.Console.PrintError(f"AIAssistant API Error: {e.code} - {error_body}\n")
            return f"# API Error {e.code}: {error_body}"

        except urllib.error.URLError as e:
            FreeCAD.Console.PrintError(f"AIAssistant Connection Error: {e.reason}\n")
            return f"# Connection Error: {e.reason}"

        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant Error: {e}\n")
            return f"# Error: {e}"

    def _clean_response(self, response: str) -> str:
        """Clean up the response - remove markdown code blocks if present."""
        response = response.strip()

        # Remove markdown code fences
        if response.startswith("```python"):
            response = response[9:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        return response.strip()
