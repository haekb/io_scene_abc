Vertex animations utilize the shape key feature of Blender.

An example .blend can be found [here](./abc-v6-export-basics/minimal_abc-v6_vert_anim.blend)

## Basics
The exporter will ignore vertex animations entirely if you have less than 2 shape keys.

![](./abc-v6-vert-anim-basics/action_list.png)

For every action, you need to add shape keys equal to the number of keyframes in that action. They should be named the same as the corresponding action, eg. if you have an alt_fire animation, your shape keys should be named alt_fire_0, alt_fire_1, alt_fire_2, and so on.
**Note:** the names after the action name don't matter, but the order does. If alt_fire_2 is the highest in the list it will be attached to the first keyframe.

![](./abc-v6-vert-anim-basics/shape_keys.png)

Even if you don't want vertex animations for a certain action you'll have to create shape keys for it.

# Issues
- Currently there's a bug that affects few vertex animated nodes, they export with a slightly incorrect rotation or translation.

## Misc. Tips
- I usually set the shape key to absolute, and add "d_" prefixed actions to animate the shape keys.