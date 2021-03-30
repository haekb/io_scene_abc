Vertex animations utilize the shape key feature of Blender.

An example .blend can be found [here](./abc-v6-export-basics/minimal_abc-v6_vert_anim.blend)

## Basics
The exporter will ignore vertex animations entirely if you have less than 2 shape keys.
The exporter will ignore any "d_" prefixed actions, they're expected to contain animation of shape keys themselves, or bones that drive shape keys, etc.

![](./abc-v6-vert-anim-basics/shape_keys.png)

## Misc. Tips
- Nothing here yet

![](./abc-v6-vert-anim-basics/action_list.png)