import bpy
import bpy_extras
import bmesh
import os
import math
from math import pi
from mathutils import Vector, Matrix, Quaternion, Euler
from bpy.props import StringProperty, BoolProperty, FloatProperty
from .dtx import DTX
from .reader import ModelReader
from . import utils


class ModelImportOptions(object):
    def __init__(self):
        self.should_import_animations = False
        self.should_import_sockets = False
        self.bone_length_min = 0.1
        self.should_import_lods = False
        self.should_merge_pieces = False
        self.images = []


def import_model(model, options):
    # utils.delete_all_objects()

    # This seems to be the rage these days
    Context = bpy.context
    Data = bpy.data
    Ops = bpy.ops

    # Create our new collection. This will help us later on..
    collection = Data.collections.new(model.name)
    # Add our collection to the scene
    Context.scene.collection.children.link(collection)

    # TODO: clear the orphan list for ultra name purity
    sun = Data.lights.new(name="Sun", type='SUN')
    sun_object = Data.objects.new("Sun", sun)
    collection.objects.link(sun_object)

    # Create the armature
    armature = bpy.data.armatures.new(model.name)
    armature_object = bpy.data.objects.new(model.name, armature)
    armature_object.data.display_type = 'STICK'
    armature_object.show_in_front = True

    collection.objects.link(armature_object)
    armature_object.select_set(True)
    #armature_object.edit_bones()

    Context.view_layer.objects.active = armature_object
    Ops.object.mode_set(mode='EDIT')

    for node in model.nodes:
        bone = armature.edit_bones.new(node.name)
        '''
        We can be assured that the parent will always be found because
        the node list is in the same order as a depth-first traversal of the
        node hierarchy.
        '''
        bone.parent = armature.edit_bones[node.parent.name] if node.parent else None
        bone.tail = (1, 0, 0)
        bone.transform(node.bind_matrix)

        if bone.parent is not None:
            bone.use_connect = bone.parent.tail == bone.head
            print(bone.use_connect, node.is_removable)

        '''
        Get the forward, left, and up vectors of the bone (used later for determining the roll).
        '''

        '''
        Lithtech uses a left-handed coordinate system where:
            X+: Right
            Y+: Up
            Z+: Forward
        '''
        (forward, right, up) = map(lambda x: -x.xyz, node.bind_matrix.col[0:3])

        if node.children:
            '''
            This bone has children. To determine the tail position of this bone,
            we check if all child bone head locations are sufficiently collinear to this
            direction vector of this bone.
            '''
            is_collinear = True
            collinearity_epsilon = 0.00001

            for child in node.children:
                child_dir = child.bind_matrix.translation - bone.head
                dot_product = forward.dot(child_dir.normalized())
                if (1.0 - dot_product) > collinearity_epsilon:
                    is_collinear = False
                    break

            if is_collinear:
                '''
                All child bone head locations are collinear to the directionality of
                the bone. Set the tail of this bone to the nearest child bone whose
                head is not concurrent with the head of the current bone (i.e. we shouldn't have zero-length bones!)
                '''
                sorted_children = node.children[:]
                sorted_children.sort(key=lambda c: (bone.head - c.bind_matrix.translation).length_squared)
                bone.tail = sorted_children[0].bind_matrix.translation
                # TODO: this could still be generating zero-length bones
            else:
                '''
                One or more child bone head locations are not collinear. Simply project
                the bone out along it's forward vector a reasonable distance.
                '''
                dot_products = map(lambda x: forward.dot(child.bind_matrix.translation - bone.head), node.children)
                dot_products = list(filter(lambda x: x > 0, dot_products))
                bone_length = max(options.bone_length_min,
                                  min(dot_products) if dot_products else options.bone_length_min)
                bone.tail = bone.head + bone_length * forward
        else:
            '''
            There is no child node to connect to, so we make a guess
            as to an appropriate length of the bone (half the length
            of the previous bone).
            '''
            if bone.parent is not None:
                bone_length = max(options.bone_length_min, bone.parent.length * 0.5)
            else:
                bone_length = options.bone_length_min
            bone.tail = bone.head + bone_length * forward

            # TODO: Now calculate the roll of the bone.

    Ops.object.mode_set(mode='OBJECT')

    ''' Add sockets as empties with a child-of constraint to the appropriate bone. '''
    if options.should_import_sockets:
        for socket in model.sockets:
            empty_object = Data.objects.new(socket.name, None)
            empty_object.location = socket.location
            empty_object.rotation_quaternion = socket.rotation
            empty_object.empty_display_type = 'PLAIN_AXES'
            child_of_constraint = empty_object.constraints.new('CHILD_OF')
            child_of_constraint.target = armature_object
            child_of_constraint.subtarget = model.nodes[socket.node_index].name
            empty_object.parent = armature_object
            collection.objects.link(empty_object)

    ''' Determine the amount of LODs to import. '''
    lod_import_count = model.lod_count if options.should_import_lods else 1

    ''' Create materials. '''
    materials = []

    for i, piece in enumerate(model.pieces):
        while len(materials) <= piece.material_index:
            ''' Create a material for the new piece. '''
            material = Data.materials.new(piece.name)
            material.specular_intensity = piece.specular_power / 100

            material.use_nodes = True

            # TODO: maybe put something in here for the specular scale?
            materials.append(material)

            ''' Create texture. '''
            
            # Swapped over to nodes
            bsdf = material.node_tree.nodes["Principled BSDF"]
            texImage = material.node_tree.nodes.new('ShaderNodeTexImage')
            material.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])

            texture = Data.textures.new(piece.name, type='IMAGE')

            # Note: Texture image names are stored in ModelButes.txt
            if options.image is not None:
                texture.image = bpy.data.images.new(piece.name, width=options.image.width, height=options.image.height, alpha=True) # TODO: get real name
                texture.image.pixels[:] = options.image.pixels[:]

            texImage.image = texture.image


    ''' Create a mesh for each piece of each LOD level that we are importing. '''
    for lod_index in range(lod_import_count):
        for piece_index, piece in enumerate(model.pieces):
            lod = piece.lods[lod_index]

            ''' Create the object and mesh. '''
            mesh_name = piece.name
            if options.should_import_lods:
                mesh_name += '.LOD{0!s}'.format(lod_index)
            mesh = Data.meshes.new(model.name)
            mesh_object = Data.objects.new(mesh_name, mesh)

            ''' Add materials to mesh. '''
            for material in materials:
                ''' Create UV map. '''
                '''
                uv_texture = mesh.uv_textures.new()
                mesh.materials.append(material)
                material.texture_slots[0].uv_layer = uv_texture.name
                '''
                uv_texture = mesh.uv_layers.new()
                mesh.materials.append(material)
                # material.uv_layers[0].name = uv_texture.name

            ''' Create a vertex group for each node. '''
            for node in model.nodes:
                mesh_object.vertex_groups.new(name=node.name)

            # TODO: these need to be reset for each mesh
            vertex_offset = 0
            face_offset = 0

            ''' Populate the actual mesh data. '''
            bm = bmesh.new()
            bm.from_mesh(mesh)

            for vertex in lod.vertices:
                bm.verts.new(vertex.location)

            bm.verts.ensure_lookup_table()
            duplicate_face_indices = []
            for face_index, face in enumerate(lod.faces):
                face = [bm.verts[vertex_offset + vertex.vertex_index] for vertex in face.vertices]
                try:
                    bmface = bm.faces.new(face)
                except ValueError:
                    '''
                    This face is a duplicate of another face, which is disallowed by Blender.
                    Mark this face for deletion after iteration.
                    '''
                    duplicate_face_indices.append(face_index)
                    continue
                '''
                Assign the material index of face based on the piece's material index.
                '''
                bmface.material_index = model.pieces[piece_index].material_index
                bmface.smooth = True

            bm.faces.ensure_lookup_table()

            '''
            Warn the user of the number of duplicate faces detected, if any.
            '''
            if len(duplicate_face_indices) > 0:
                print('WARNING: {} duplicate faces detected.'.format(len(duplicate_face_indices)))

            '''
            Delete any of the duplicate faces from the mesh.
            '''
            for face_index in reversed(sorted(duplicate_face_indices)):
                del lod.faces[face_index]

            vertex_offset += len(lod.vertices)
            face_offset += len(lod.faces)

            bm.to_mesh(mesh)

            '''
            Assign texture coordinates.
            '''
            material_face_offsets = [0] * len(mesh.materials)
            uv_texture = mesh.uv_layers[piece.material_index]

            # Set the correct UV as active
            uv_texture.active_render = True

            for face_index, face in enumerate(lod.faces):
                material_face_offset = material_face_offsets[0]  # TODO: is this right?
                texcoords = [vertex.texcoord for vertex in face.vertices]
                for i in range(3):
                    uv = texcoords[i][0], 1.0 - texcoords[i][1]
                    uv_texture.data[(material_face_offset + face_index) * 3 + i].uv = uv
            material_face_offsets[0] += len(lod.faces)

            ''' Assign normals '''
            face_offset = 0
            polygons = mesh.polygons[face_offset:face_offset + len(lod.faces)]
            for face_index, (face, polygon) in enumerate(zip(lod.faces, polygons)):
                vertices = lod.get_face_vertices(face_index)
                for vertex, loop_index in zip(vertices, polygon.loop_indices):
                    # TODO: this might not actually set the normal properly
                    n = Vector(vertex.normal)
                    mesh.loops[loop_index].normal = n
            face_offset += len(lod.faces)

            mesh.validate(clean_customdata=False)
            mesh.update(calc_edges=False)

            # add it to our collection c:
            collection.objects.link(mesh_object)

            if Ops.object.mode_set.poll():
                Ops.object.mode_set(mode='OBJECT')
            Ops.object.select_all(action='DESELECT')

            ''' Add an armature modifier. '''
            armature_modifier = mesh_object.modifiers.new(name='Armature', type='ARMATURE')
            armature_modifier.object = armature_object

            ''' Assign vertex weighting. '''
            vertex_offset = 0
            for (vertex_index, vertex) in enumerate(lod.vertices):
                for weight in vertex.weights:
                    vertex_group_name = model.nodes[weight.node_index].name
                    vertex_group = mesh_object.vertex_groups[vertex_group_name]
                    vertex_group.add([vertex_offset + vertex_index], weight.bias, 'REPLACE')
            vertex_offset += len(lod.vertices)

            ''' Parent the mesh to the armature. '''
            mesh_object.parent = armature_object

    ''' Animations '''
    if options.should_import_animations:
        for ob in bpy.context.scene.objects:
            ob.animation_data_clear()

        assert (len(armature.bones) == len(model.nodes))

        armature_object.animation_data_create()

        actions = []

        index = 0
        for animation in model.animations:
            print("Processing ", animation.name)
            if(index > 0):
                break

            index  = index + 1
            # Create a new action with the animation name
            action = bpy.data.actions.new(name=animation.name)
            
            # Temp set
            armature_object.animation_data.action = action

            # For every keyframe
            for keyframe_index, keyframe in enumerate(animation.keyframes):
                # Set keyframe time - Scale it down because it's way too slow for testing
                Context.scene.frame_set(keyframe.time * 0.01)
           
                '''
                Recursively apply transformations to a nodes children
                Notes: It carries everything (nodes, pose_bones..) with it, because I expected it to not be a child of this scope...oops!
                '''
                def recursively_apply_transform(nodes, node_index, pose_bones, parent_matrix):
                    # keyframe_index = 0
                    node = nodes[node_index]
                    pose_bone = pose_bones[node_index]
                    original_index = node_index

                    #print("[",node_index,"] Applying transform to : ", node.name)


                    # Get the current transform
                    transform = animation.node_keyframe_transforms[node_index][keyframe_index]

                    # Correct-ish
                    # rotation = Quaternion( (transform.rotation.w, -transform.rotation.z, -transform.rotation.x, transform.rotation.y) )


                    rotation = Quaternion( (transform.rotation.w, -transform.rotation.z, -transform.rotation.x, transform.rotation.y) )

                    matrix = rotation.to_matrix().to_4x4() # transform.rotation.to_matrix().to_4x4()

                    # Apply the translation
                    matrix.Translation(transform.location.xzy)
    
                    
                    # Use a matrix instead!
                    pose_bone.matrix = parent_matrix @ matrix

                    # Recursively apply our transform to our children!
                    # print("[",node_index,"] Found children count : ", node.child_count)

                    #if (node.child_count):
                    #    print("[",original_index,"] Recurse Start --- ",node.name)

                    for index in range(0, node.child_count):
                        node_index = node_index + 1
                        #print("[",original_index,"] Applying transform to child : ", nodes[node_index].name)

                        node_index = recursively_apply_transform(nodes, node_index, pose_bones, pose_bone.matrix)
                    
                    #if (node.child_count):
                    #    print("[",original_index,"] Recurse End   --- ",node.name)

                    return node_index
                '''
                Func End
                '''

                recursively_apply_transform(model.nodes, 0, armature_object.pose.bones, Matrix())

                # For every bone
                for bone, node in zip(armature_object.pose.bones, model.nodes):
                    bone.keyframe_insert('location')
                    bone.keyframe_insert('rotation_quaternion')

            # Add to actions array
            actions.append(action)

        # Add our actions to animation data
        armature_object.animation_data.action = actions[0]

    # Set our keyframe time to 0
    Context.scene.frame_set(0)

    # TODO: make an option to convert to blender coordinate system
    # armature_object.rotation_euler.x = math.radians(90)
    # armature_object.scale.x = -1.0

    return {'FINISHED'}


class ImportOperator(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = 'io_scene_abc.abc_import'  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = 'Import Lithtech ABC'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    # ImportHelper mixin class uses this
    filename_ext = ".abc"

    filter_glob = StringProperty(
        default="*.abc",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    bone_length_min = FloatProperty(
        name='Bone Length',
        default=0.1,
        description='The minimum bone length',
        min=0.01
    )

    should_import_lods = BoolProperty(
        name="Import LODs",
        description="When checked, LOD meshes will be imported (suffixed with .LOD0, .LOD1 etc.)",
        default=False,
    )

    should_import_animations = BoolProperty(
        name="Import Animations (not yet working)",
        description="When checked, animations will be imported as actions.",
        default=False,
    )

    should_import_sockets = BoolProperty(
        name="Import Sockets",
        description="When checked, sockets will be imported as Empty objects.",
        default=True,
    )

    should_merge_pieces = BoolProperty(
        name="Merge Pieces (not yet working)",
        description="When checked, pieces that share a material index will be merged.",
        default=False,
    )

    should_import_textures = BoolProperty(
        name="Import Textures (WIP)",
        description="When checked, pieces that share a material index will be merged.",
        default=False,
    )

    should_clear_scene = BoolProperty(
        name="Clear Scene",
        description="When checked, the scene will be cleared before the model is imported.",
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text='Nodes')
        box.row().prop(self, 'bone_length_min')
        box.row().prop(self, 'should_import_sockets')

        box = layout.box()
        box.label(text='Meshes')
        box.row().prop(self, 'should_import_lods')
        box.row().prop(self, 'should_merge_pieces')

        box = layout.box()
        box.label(text='Materials')
        box.row().prop(self, 'should_import_textures')
        # box.row().prop(self, 'should_assign_materials')

        box = layout.box()
        box.label(text='Animations')
        box.row().prop(self, 'should_import_animations')

        box = layout.box()
        box.label(text='Misc')
        box.row().prop(self, 'should_clear_scene')

    def execute(self, context):
        # Load the model
        model = ModelReader().from_file(self.filepath)
        model.name = os.path.splitext(os.path.basename(self.filepath))[0]
        image = None
        if self.should_import_textures:
            filename = os.path.splitext(os.path.basename(self.filepath))[0]
            skins_directory = os.path.join(os.path.dirname(self.filepath), '..', 'SKINS')
            texture = os.path.join(skins_directory, filename + '.DTX')
            try:
                image = DTX(texture)
            except IOError:
                pass
        options = ModelImportOptions()
        options.bone_length_min = self.bone_length_min
        options.should_import_lods = self.should_import_lods
        options.should_import_animations = self.should_import_animations
        options.should_import_sockets = self.should_import_sockets
        options.should_merge_pieces = self.should_merge_pieces
        options.should_clear_scene = self.should_clear_scene
        options.image = image
        import_model(model, options)
        return {'FINISHED'}

    @staticmethod
    def menu_func_import(self, context):
        self.layout.operator(ImportOperator.bl_idname, text='Lithtech ABC (.abc)')
