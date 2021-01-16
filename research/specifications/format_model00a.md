# Format
Model00a files are simply LTA files wrapped with some extra data.

# Physics
Lithtech Jupiter EX integrates the Havok physics engine. It appears support wasn't extended to modders, I've heard reports of Havok/Physics part of the mesh exporter are just broken because of unincluded havok sdk files. Good news though, it appears to be a very simple thing to support.

## Nodes
`model-physics` 
Wraps the entire physics data

`physics-properties`
- `model-weight` - The mass of this physical shape in kilogram.
- `model-density` - The density of this object measured in grams per cubic centimeter that is used for buoyancy. Water has a density of 1 gram per cubic centimeter.
- `vis-node` - Center of visibility when the model is in a physically simulated state.
- `vis-radius` - Radius of vis-node.
Contains various properties affecting the entire mesh.

`physics-shapes`
A list of `node-shape-list` items.

`node-shape-list`
 - `node-name` - Name of the node this shape should be based from.
 - `cor` - Coefficient of restitution value of the shape.
 - `friction` - Friction of the shape.
 - `collision-group` - This affects which physics items will collide with other physics items.
An item within the `physics-shapes` list.

`node-shapes`
A list of `physics-shape` items.

`physics-shape`
- `name` - Name of the physics shape.
- `type` - What shape type to use. (sphere or capsule.)
- `length` - The length of the shape (capsule specific?)
- `radius` - The radius of the shape.
- `mass-percent` - How heavy this particular shape is (from the total mesh?)
- `density-scale` - How dense this particular shape is.
- `offset` - Offset XYZ from the assigned node.
- `orientation` - Orientation XYZW from the assigned node. (capsule specific?)
The actual physics mesh data along with some physical defining properties.

`physics-constraints`
A list of `constraint` items.

(I haven't poked around with constraints that much!)
`constraint`
- `name` - Name of the physics constraint.
- `node1` - The first node this constraint affects.
- `position1` - Position XYZ from the model root for the first node.
- `node2` - The second node this constraint affects.
- `position2` - Position XYZ from the `position1`.
- `shape1` - The physics shape name.
- `shape2` - The physics shape name.
- `type` - The type of constraint (hinge, limited-hinge, point, prismatic, ragdoll, stiff-spring, or wheel.)
- `hinge-axis1` - XYZ (hinge specific)
- `hinge-axis2` - XYZ (hinge specific)
- `hinge-forward1` - Forward Axis XYZ (hinge specific)
- `hinge-forward2` - Forward Axis XYZ (hinge specific)
- `angle-min` - The minimum angle that the hinge can rotate around the forward axis relative to the up axis. For example -30 means it can rotate counterclockwise up to 30 degrees (hinge specific?)
- `angle-max` - The maximum angle that the hinge can rotate around the forward axis relative to the up axis. For example 30 means it can rotate clockwise up to 30 degrees (hinge specific?)
- `plane-axis1` - XYZ (ragdoll specific?)
- `plane-axis2` - XYZ (ragdoll specific?)
- `twist-axis1` - XYZ (ragdoll specific?)
- `twist-axis2` - XYZ (ragdoll specific?)
- `twist-min` - The minimum angle that the body can twist around the forward axis relative to the up axis. For example -30 means it can rotate counterclockwise up to 30 degrees (ragdoll specific)
- `twist-max` - The minimum angle that the body can twist around the forward axis relative to the up axis. For example -0 means it can rotate clockwise up to 30 degrees (ragdoll specific)
- `cone-min` - The angle of the cone of movement around the forward axis of the constraint (ragdoll specific)
- `cone-max` - The angle of the cone of movement around the forward axis of the constraint (ragdoll specific)
- `pos-angle` - The radius of the cone of restriction around the positive X axis of the constraint (ragdoll specific)
- `neg-angle` - The radius of the cone of restriction around the negative X axis of the constraint (ragdoll specific)
- `friction` - The amount of friction to apply as the object moves. This number should be obtained through experimentation, but larger numbers mean more friction
Constraints force the ragdoll shapes to behave in a specific way. These can help with making human bodies move correctly and not clip into themselves, or allow doors to only open in one direction.

`physics-weight-sets`
List of `physics-weight-set` items.

`physics-weight-set`
- `name` - Name of the weight set
- `node-list` a list of `node-weight`s. 
unknown!

`node-weight`
- `node` - The node in question
- `physics` - unknown
- `velocity-gain` - unknown
- `hierarchy-gain` - unknown`
unknown!