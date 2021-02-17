from .abc import *
from math import pi, radians, floor
from mathutils import Vector, Matrix, Quaternion, Euler
import bpy

class ModelBuilder(object):
    def __init__(self):
        pass

    #
    # Set Keyframe Timings
    # Handles setting up the dictionary struct if it's the first time through a particular bone.
    #
    @staticmethod
    def set_keyframe_timings(keyframe_dictionary, bone, time, transform_type):
        # Set up the small struct, if it's not already done
        if bone not in keyframe_dictionary:
            keyframe_dictionary[bone] = {
                'rotation_quaternion': [],
                'location': []
            }
        # End If

        # Append our key time
        keyframe_dictionary[bone][transform_type].append(time)

        return keyframe_dictionary
    # End Function

    @staticmethod
    def from_armature(armature_object):
        print("--------------------------")
        print("Building from Armature")
        assert (armature_object.type == 'ARMATURE')
        armature = armature_object.data
        mesh_objects = [child for child in armature_object.children if child.type == 'MESH']

        if not mesh_objects:
            raise Exception('{} has no children of type \'MESH\'.'.format(armature_object.name))

        model = Model()
        model.internal_radius = int(max(armature_object.dimensions))

        ''' Pieces '''
        for mesh_object in mesh_objects:
            mesh = mesh_object.data
            modifiers = [modifier for modifier in mesh_object.modifiers if
                         modifier.type == 'ARMATURE' and modifier.object == armature_object]
            ''' Ensure that the mesh object has an armature modifier. '''
            if len(modifiers) == 0:
                raise Exception(
                    '\'{}\' does not have a modifier of type \'ARMATURE\' with object {}'.format(mesh_object.name,
                                                                                                 armature_object.name))
            elif len(modifiers) > 1:
                raise Exception(
                    '\'{}\' has more than one modifier of type \'ARMATURE\' with object {}'.format(mesh_object.name,
                                                                                                   armature_object.name))

            ''' Ensure that the mesh has UV layer information. '''
            if mesh.uv_layers.active is None:
                raise Exception('\'{}\' does not have an active UV layer'.format(mesh_object.name))

            ''' Build a dictionary of vertex groups to bones. '''
            vertex_group_nodes = dict()
            for vertex_group in mesh_object.vertex_groups:
                try:
                    vertex_group_nodes[vertex_group] = armature.bones[vertex_group.name]  # okay
                except KeyError:
                    vertex_group_nodes[vertex_group] = None

            piece = Piece()
            piece.name = mesh_object.name

            # TODO: multiple LODs
            lod = LOD()

            bone_indices = dict()
            for i, bone in enumerate(armature.bones):
                bone_indices[bone] = i

            ''' Vertices '''
            for (vertex_index, vertex) in enumerate(mesh.vertices):
                weights = []
                for vertex_group in mesh_object.vertex_groups:

                    # Location is used in Lithtech 2.0 games, but is not in ModelEdit.
                    try:
                        bias = vertex_group.weight(vertex_index)
                        bone = vertex_group_nodes[vertex_group]

                        bone_matrix = armature_object.matrix_world @ bone.matrix_local

                        location = (vertex.co @ mesh_object.matrix_world) @ bone_matrix.transposed().inverted()
                        if bias != 0.0 and bone is not None:
                            weight = Weight()
                            weight.node_index = bone_indices[bone]
                            weight.bias = bias
                            weight.location = location
                            weights.append(weight)
                    except RuntimeError:
                        pass


                # Note: This corrects any rotation done on import
                rot = Matrix.Rotation(radians(-180), 4, 'Z') @ Matrix.Rotation(radians(90), 4, 'X')

                v = Vertex()
                v.location = vertex.co @ rot
                v.normal = vertex.normal
                v.weights.extend(weights)
                lod.vertices.append(v)

            ''' Faces '''
            material_count = {}
            for polygon in mesh.polygons:
                if len(polygon.loop_indices) > 3:
                    raise Exception('Mesh \'{}\' is not triangulated.'.format(
                        mesh.name))  # TODO: automatically triangulate the mesh, and have this be reversible
                face = Face()
                face.normal=polygon.normal

                for loop_index in polygon.loop_indices:
                    uv = mesh.uv_layers.active.data[loop_index].uv.copy()  # TODO: use "active"?
                    uv.y = 1.0 - uv.y
                    face_vertex = FaceVertex()
                    face_vertex.texcoord.x = uv.x
                    face_vertex.texcoord.y = uv.y
                    face_vertex.vertex_index = mesh.loops[loop_index].vertex_index
                    face.vertices.append(face_vertex)

                # We're going to keep a running total to see which material index is the main one to use
                if polygon.material_index in material_count:
                    material_count[polygon.material_index] = material_count[polygon.material_index] + 1
                else:
                    material_count[polygon.material_index] = 0

                lod.faces.append(face)

            piece.material_index = max(material_count)
            piece.lods.append(lod)

            model.pieces.append(piece)

        ''' Nodes '''
        for bone_index, bone in enumerate(armature.bones):
            node = Node()
            node.name = bone.name
            node.index = bone_index
            node.flags = 0
            if bone_index == 0:  # DEBUG: set removable?
                node.is_removable = True

            matrix = armature_object.matrix_world @ bone.matrix_local

            node.bind_matrix = matrix

            # ABC v6 specific
            # FIXME: disgusting, can this be done better?
            for piece in model.pieces:
                for lod in piece.lods:
                    for vertex in lod.vertices:
                        if vertex.weights[0].node_index==bone_index:
                            node.bounds_min=Vector((min(node.bounds_min.x, vertex.location.x), min(node.bounds_min.y, vertex.location.y), min(node.bounds_min.z, vertex.location.z)))
                            node.bounds_max=Vector((max(node.bounds_min.x, vertex.location.x), max(node.bounds_min.y, vertex.location.y), max(node.bounds_min.z, vertex.location.z)))

            #print("Processed", node.name, node.bind_matrix)
            node.child_count = len(bone.children)
            model.nodes.append(node)

        build_undirected_tree(model.nodes)

        ''' Sockets '''
        for obj in bpy.data.objects:
            print("Obj Type %s and name %s" % (obj.type, obj.name))
            if obj.type == 'EMPTY' and obj.name.startswith("s_"):
                node_index = 0
                for node in model.nodes:
                    if node.name == obj.constraints.active.subtarget:
                        node_index = node.index
                        break

                socket = Socket()
                socket.name = obj.name[2:]
                socket.node_index = node_index
                socket.location = obj.location
                socket.rotation = obj.rotation_quaternion
                model.sockets.append(socket)

        ''' ChildModels '''
        child_model = ChildModel()

        for _ in model.nodes:
            child_model.transforms.append(Animation.Keyframe.Transform())
        model.child_models.append(child_model)

        ''' Animations '''
        for action in bpy.data.actions:
            print("Processing animation %s" % action.name)
            animation = Animation()
            animation.name = action.name

            armature_object.animation_data.action = action

            # This is only one action fyi!
            fcurves = armature_object.animation_data.action.fcurves

            # Keyframe dictionary
            # Stores the keyframe timings
            keyframe_timings = {}

            # How much we need to skip, because we already loaded the next n fcurves
            current_skip_count = 0

            fcurve_index = 0
            fcurves_count = len(fcurves)

            # Loop through every fcurve,
            # these are basically keyed parts of a transformation
            while fcurve_index < fcurves_count:
                current_type = 'unknown'
                current_skip_count = 0

                fcurve = fcurves[fcurve_index]
                bone_name = fcurve.data_path.split("\"")[1]

                if 'rotation_quaternion' in fcurve.data_path:
                    current_type = 'rotation_quaternion'
                    current_skip_count = 4
                elif 'location' in fcurve.data_path:
                    current_type = 'location'
                    current_skip_count = 3
                elif 'scale' in fcurve.data_path:
                    current_skip_count = 3
                    fcurve_index += current_skip_count
                    continue
                # End If

                # Assume if one part of the transform changes, the entire thing changes
                for keyframe in fcurve.keyframe_points:
                    ModelBuilder.set_keyframe_timings(keyframe_timings, bone_name, keyframe.co.x, current_type)
                # End For

                # Make sure we don't have any unknown types
                # TODO: We should probably support other rotation types in the future...
                assert(current_type != 'unknown')

                fcurve_index += current_skip_count
            # End For

            # First let's setup our keyframes
            # For now we can just use the first node!
            for time in keyframe_timings[model.nodes[0].name]['rotation_quaternion']:
                # Expand our time
                scaled_time = time * (1.0/0.024)
                bpy.context.scene.frame_set(time, subframe=time-floor(time))

                keyframe = Animation.Keyframe()
                keyframe.time = scaled_time
                animation.keyframes.append(keyframe)

                keyframe.bounds_min=Vector(mesh_object.bound_box[0]) # will using mesh_object here break if there's multiple mesh
                keyframe.bounds_max=Vector(mesh_object.bound_box[6]) # objects using the same armature as a parent? DON'T DO THAT

            animation.bounds_min=max([keyframe.bounds_min for keyframe in animation.keyframes])
            animation.bounds_max=max([keyframe.bounds_max for keyframe in animation.keyframes])

            # Okay let's start processing our transforms!
            for node_index, (node, pose_bone) in enumerate(zip(model.nodes, armature_object.pose.bones)):
                transforms = list()

                keyframe_timing = keyframe_timings[pose_bone.name]

                # FIXME: In the future we may trim off timing with no rotation/location changes
                # So we'd have to loop through each keyframe timing, but for now this should work!
                for time in keyframe_timing['rotation_quaternion']:
                    # Expand our time
                    scaled_time = time * (1.0/0.024)
                    bpy.context.scene.frame_set(time, subframe=time-floor(time))

                    transform = Animation.Keyframe.Transform()

                    matrix = pose_bone.matrix

                    # Apply the inverse parent bone matrix to get relative positioning
                    if pose_bone.parent != None:
                        matrix = pose_bone.parent.matrix.inverted() @ matrix
                    # End If

                    transform.matrix = matrix

                    transforms.append(transform)
                # End For
                animation.node_keyframe_transforms.append(transforms)
            # End For

            model.animations.append(animation)
        # End For

        ''' AnimBindings '''
        anim_binding = AnimBinding()
        anim_binding.name = 'base'
        anim_binding.extents = Vector((10, 10, 10))
        model.anim_bindings.append(anim_binding)

        return model