import os
from .abc import *
from .io import unpack
from mathutils import Vector, Matrix, Quaternion

# LTB Mesh Types
LTB_Type_Rigid_Mesh = 4
LTB_Type_Skeletal_Mesh = 5
LTB_Type_Vertex_Animated_Mesh = 6
LTB_Type_Null_Mesh = 7

# Data stream flags
VTX_Position      = 0x0001
VTX_Normal        = 0x0002
VTX_Colour        = 0x0004
VTX_UV_Sets_1     = 0x0010
VTX_UV_Sets_2     = 0x0020
VTX_UV_Sets_3     = 0x0040
VTX_UV_Sets_4     = 0x0080
VTX_BasisVector   = 0x0100

# Animation Compression Types
CMP_None = 0
CMP_Relevant = 1
CMP_Relevant_16 = 2
CMP_Relevant_Rot16 = 3

Invalid_Bone = 255

#
# Supports LTB v23
#
class PCLTBModelReader(object):
    def __init__(self):
    
        self._version = 0
        self._node_count = 0
        self._lod_count = 0

    def _read_matrix(self, f):
        data = unpack('16f', f)
        rows = [data[0:4], data[4:8], data[8:12], data[12:16]]
        return Matrix(rows)

    def _read_vector(self, f):
        return Vector(unpack('3f', f))

    def _read_quaternion(self, f):
        x, y, z, w = unpack('4f', f)
        return Quaternion((w, x, y, z))

    def _read_string(self, f):
        return f.read(unpack('H', f)[0]).decode('ascii')

    def _read_weight(self, f):
        weight = Weight()
        weight.node_index = unpack('I', f)[0]
        weight.location = self._read_vector(f)
        weight.bias = unpack('f', f)[0]
        return weight

    def _read_vertex(self, f):
        vertex = Vertex()
        weight_count = unpack('H', f)[0]
        vertex.sublod_vertex_index = unpack('H', f)[0]
        vertex.weights = [self._read_weight(f) for _ in range(weight_count)]
        vertex.location = self._read_vector(f)
        vertex.normal = self._read_vector(f)
        return vertex

    def _read_face_vertex(self, f):
        face_vertex = FaceVertex()
        face_vertex.texcoord.xy = unpack('2f', f)
        face_vertex.vertex_index = unpack('H', f)[0]
        return face_vertex

    def _read_face(self, f):
        face = Face()
        face.vertices = [self._read_face_vertex(f) for _ in range(3)]
        return face

    def _read_null_mesh(self, lod, f):
        # No data here but a filler int!
        f.seek(4, 1)
        return lod

    def _read_rigid_mesh(self, lod, f):
        data_type = unpack('4I', f)
        bone = unpack('I', f)[0]

        # We need face vertex data alongside vertices!
        face_vertex_list = []

        for mask in data_type:
            for _ in range(lod.vert_count):
                vertex = Vertex()
                face_vertex = FaceVertex()

                # Dirty flags
                is_vertex_used = False
                is_face_vertex_used = False
            
                if mask & VTX_Position:
                    vertex.location = self._read_vector(f)
                    
                    # One bone per vertex
                    weight = Weight()
                    weight.node_index = bone
                    weight.bias = 1.0

                    #vertex.weights.append(weight)

                    is_vertex_used = True
                if mask & VTX_Normal:
                    vertex.normal = self._read_vector(f)
                    is_vertex_used = True
                if mask & VTX_Colour:
                    vertex.colour = unpack('i', f)[0]
                    is_vertex_used = True
                if mask & VTX_UV_Sets_1:
                    face_vertex.texcoord.xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_2:
                    face_vertex.extra_texcoords[0].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_3:
                    face_vertex.extra_texcoords[1].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_4:
                    face_vertex.extra_texcoords[2].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_BasisVector:
                    vertex.s = self._read_vector(f)
                    vertex.t = self._read_vector(f)
                    is_vertex_used = True
                # End If

                if is_vertex_used:
                    lod.vertices.append(vertex)

                if is_face_vertex_used:
                    face_vertex_list.append(face_vertex)
                 
            # End For
        # End For

        # Make sure our stuff is good!!
        print ("Vert Count Check: %d/%d" % (lod.vert_count, len(lod.vertices)))
        assert(lod.vert_count == len(lod.vertices))

        # We need a "global" face, we'll fill it and re-use it.
        face = Face()
        for _ in range(lod.face_count * 3):
            vertex_index = unpack('H', f)[0]

            face_vertex = face_vertex_list[vertex_index]
            face_vertex.vertex_index = vertex_index

            # If we have room, append!
            if len(face.vertices) < 3:
                face.vertices.append(face_vertex)
            # End If

            # If we're now over, then flush!
            if len(face.vertices) >= 3:
                lod.faces.append(face)
                # Make a new face, and append our face vertex
                face = Face()
            # End If
        # End For

        # Make sure our stuff is good!!
        print ("Face Count Check: %d/%d" % (lod.face_count, len(lod.faces)))
        assert(lod.face_count == len(lod.faces))

        return lod

    def _read_skeletal_mesh(self, lod, f):
        reindexed_bone = unpack('B', f)[0]
        data_type = unpack('4I', f)

        matrix_palette = unpack('B', f)[0]

        print("Matrix Palette? %d" % matrix_palette)

        # We need face vertex data alongside vertices!
        face_vertex_list = []

        for mask in data_type:
            for _ in range(lod.vert_count):
                vertex = Vertex()
                face_vertex = FaceVertex()

                # Dirty flags
                is_vertex_used = False
                is_face_vertex_used = False

                if mask & VTX_Position:
                    vertex.location = self._read_vector(f)
                    is_vertex_used = True

                    weights = []

                    weight = Weight()
                    weight.bias = 1.0

                    weights.append(weight)

                    for i in range(lod.max_bones_per_face):
                        # Skip the first one
                        if i == 0:
                            continue
                        # End If

                        # There's 3 additional blends, 
                        # If ... max_bones_per_face >= 2,3,4
                        if lod.max_bones_per_face >= (i+1):
                            blend = unpack('f', f)[0]
                            weight.bias -= blend

                            blend_weight = Weight()
                            blend_weight.bias = blend
                            weights.append(blend_weight)
                        # End If
                    # End For

                    vertex.weights = []#weights
                if mask & VTX_Normal:
                    vertex.normal = self._read_vector(f)
                    is_vertex_used = True
                if mask & VTX_Colour:
                    vertex.colour = unpack('i', f)[0]
                    is_vertex_used = True
                if mask & VTX_UV_Sets_1:
                    face_vertex.texcoord.xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_2:
                    face_vertex.extra_texcoords[0].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_3:
                    face_vertex.extra_texcoords[1].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_UV_Sets_4:
                    face_vertex.extra_texcoords[2].xy = unpack('2f', f)
                    is_face_vertex_used = True
                if mask & VTX_BasisVector:
                    vertex.s = self._read_vector(f)
                    vertex.t = self._read_vector(f)
                    is_vertex_used = True
                # End If

                if is_vertex_used:
                    lod.vertices.append(vertex)

                if is_face_vertex_used:
                    face_vertex_list.append(face_vertex)
                
            # End For
        # End For

        # Make sure our stuff is good!!
        print ("Vert Count Check: %d/%d" % (lod.vert_count, len(lod.vertices)))
        assert(lod.vert_count == len(lod.vertices))

        # We need a "global" face, we'll fill it and re-use it.
        face = Face()
        for _ in range(lod.face_count * 3):
            vertex_index = unpack('H', f)[0]

            face_vertex = face_vertex_list[vertex_index]
            face_vertex.vertex_index = vertex_index

            # If we have room, append!
            if len(face.vertices) < 3:
                face.vertices.append(face_vertex)
            # End If

            # If we're now over, then flush!
            if len(face.vertices) >= 3:
                lod.faces.append(face)
                # Make a new face, and append our face vertex
                face = Face()
            # End If
        # End For

        # Make sure our stuff is good!!
        print ("Face Count Check: %d/%d" % (lod.face_count, len(lod.faces)))
        assert(lod.face_count == len(lod.faces))

        bone_set_count = unpack('I', f)[0]

        for _ in range(bone_set_count):
            index_start = unpack('H', f)[0]
            index_count = unpack('H', f)[0]

            bone_list = unpack('4B', f)

            # ???
            index_buffer_index = unpack('I', f)[0]

            # Okay, now we can fill up our node indexes!
            # for vertex_index in range(index_start, index_count):
            #     vertex = lod.vertices[vertex_index]

            #     # We need to re-build the weight list for our vertex
            #     weights = []

            #     for (index, bone_index) in enumerate(bone_list):
            #         # If we've got an invalid bone (255) then ignore it
            #         if bone_index == Invalid_Bone:
            #             continue
            #         # End If

            #         vertex.weights[index].node_index = bone_index
            #         # Keep this one!
            #         weights.append(vertex.weights[index])
            #     # End For

            #     vertex.weights = weights
            # End For
        # End For

        return lod

    def _read_lod(self, f):
        lod = LOD()

        lod.texture_count = unpack('I', f)[0]
        lod.textures = unpack('4I', f)
        lod.render_style = unpack('I', f)[0]
        lod.render_priority = unpack('b', f)[0]

        lod.type = unpack('I', f)[0]

        # NULL Type
        if lod.type == LTB_Type_Null_Mesh:
            # Early return here, because there's no more data...
            return self._read_null_mesh(lod, f)
        
        # Some common data
        obj_size = unpack('I', f)[0]
        lod.vert_count = unpack('I', f)[0]
        lod.face_count = unpack('I', f)[0]
        lod.max_bones_per_face = unpack('I', f)[0]
        lod.max_bones_per_vert = unpack('I', f)[0]
        
        if lod.type == LTB_Type_Rigid_Mesh:
            lod = self._read_rigid_mesh(lod, f)
        elif lod.type == LTB_Type_Skeletal_Mesh:
            lod = self._read_skeletal_mesh(lod, f)

        nodes_used_count = unpack('B', f)[0]
        nodes_used = [unpack('B', f)[0] for _ in range(nodes_used_count)]

        return lod

    def _read_piece(self, f):
        piece = Piece()

        piece.name = self._read_string(f)
        lod_count = unpack('I', f)[0]
        piece.lod_distances = [unpack('f', f)[0] for _ in range(lod_count)]
        piece.lod_min = unpack('I', f)[0]
        piece.lod_max = unpack('I', f)[0]
        piece.lods = [self._read_lod(f) for _ in range(lod_count)]

        return piece

    def _read_node(self, f):
        node = Node()
        node.name = self._read_string(f)
        node.index = unpack('H', f)[0]
        node.flags = unpack('b', f)[0]
        node.bind_matrix = self._read_matrix(f)
        node.inverse_bind_matrix = node.bind_matrix.inverted()
        node.child_count = unpack('I', f)[0]
        return node

    def _read_transform(self, f):
        transform = Animation.Keyframe.Transform()
        transform.location = self._read_vector(f)
        transform.rotation = self._read_quaternion(f)

        # Two unknown floats!
        if self._version == 13:
            f.seek(8, 1)

        return transform

    def _read_child_model(self, f):
        child_model = ChildModel()
        child_model.name = self._read_string(f)
        child_model.build_number = unpack('I', f)[0]
        child_model.transforms = [self._read_transform(f) for _ in range(self._node_count)]
        return child_model

    def _read_keyframe(self, f):
        keyframe = Animation.Keyframe()
        keyframe.time = unpack('I', f)[0]
        keyframe.string = self._read_string(f)
        return keyframe

    def _read_animation(self, f):
        animation = Animation()
        animation.extents = self._read_vector(f)
        animation.name = self._read_string(f)
        animation.unknown1 = unpack('i', f)[0]
        animation.interpolation_time = unpack('I', f)[0] if self._version >= 12 else 200
        animation.keyframe_count = unpack('I', f)[0]
        animation.keyframes = [self._read_keyframe(f) for _ in range(animation.keyframe_count)]
        animation.node_keyframe_transforms = []
        for _ in range(self._node_count):

            # Skip past -1
            if self._version == 13:
                f.seek(4, 1)

            animation.node_keyframe_transforms.append(
                [self._read_transform(f) for _ in range(animation.keyframe_count)])
        return animation

    def _read_socket(self, f):
        socket = Socket()
        socket.node_index = unpack('I', f)[0]
        socket.name = self._read_string(f)
        socket.rotation = self._read_quaternion(f)
        socket.location = self._read_vector(f)
        return socket

    def _read_anim_binding(self, f):
        anim_binding = AnimBinding()
        anim_binding.name = self._read_string(f)
        anim_binding.extents = self._read_vector(f)
        anim_binding.origin = self._read_vector(f)
        return anim_binding

    def _read_weight_set(self, f):
        weight_set = WeightSet()
        weight_set.name = self._read_string(f)
        node_count = unpack('I', f)[0]
        weight_set.node_weights = [unpack('f', f)[0] for _ in range(node_count)]
        return weight_set

    def from_file(self, path):
        model = Model()
        model.name = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'rb') as f:

            #
            # HEADER
            #
            file_type = unpack('H', f)[0]
            file_version = unpack('H', f)[0]

            if file_type is not 1:
                raise Exception('Unsupported File Type! Only mesh LTB files are supported.')
            # End If

            if file_version is not 9:
                raise Exception('Unsupported File Version! Importer currently only supports v9.')
            # End If

            # Skip 4 ints
            f.seek(4 * 4, 1)

            self.version = unpack('i', f)[0]

            # Hope to support at least up to v25 someday!
            if self.version not in [23]:
                raise Exception('Unsupported file version ({}).'.format(self._version))
            # End If

            model.version = self.version

            keyframe_count = unpack('i', f)[0]
            animation_count = unpack('i', f)[0]
            node_count = unpack('i', f)[0]
            piece_count = unpack('i', f)[0]
            child_model_count = unpack('i', f)[0]
            face_count = unpack('i', f)[0]
            vertex_count = unpack('i', f)[0]
            vertex_weight_count = unpack('i', f)[0]
            lod_count = unpack('i', f)[0]
            socket_count = unpack('i', f)[0]
            weight_set_count = unpack('i', f)[0]
            string_count = unpack('i', f)[0]
            string_length = unpack('i', f)[0]
            vertex_animation_data_size = unpack('i', f)[0]
            animation_data_size = unpack('i', f)[0]

            model.command_string = self._read_string(f)

            model.internal_radius = unpack('f', f)[0]

            #
            # OBB Information
            #
            obb_count = unpack('i', f)[0]

            # TODO: Figure out OBB

            #
            # Pieces
            # 

            # Yep again!
            piece_count = unpack('i', f)[0]
            model.pieces = [self._read_piece(f) for _ in range(piece_count)]

            return model

            # OLD - Reference
            next_section_offset = 0
            while next_section_offset != -1:
                f.seek(next_section_offset)
                section_name = self._read_string(f)
                next_section_offset = unpack('i', f)[0]
                if section_name == 'Header':
                    self._version = unpack('I', f)[0]
                    if self._version not in [9, 10, 11, 12, 13]:
                        raise Exception('Unsupported file version ({}).'.format(self._version))
                    model.version = self._version
                    f.seek(8, 1)
                    self._node_count = unpack('I', f)[0]
                    f.seek(20, 1)
                    self._lod_count = unpack('I', f)[0]
                    f.seek(4, 1)
                    self._weight_set_count = unpack('I', f)[0]
                    f.seek(8, 1)

                    # Unknown new value
                    if self._version >= 13:
                        f.seek(4,1)

                    model.command_string = self._read_string(f)
                    model.internal_radius = unpack('f', f)[0]
                    f.seek(64, 1)
                    model.lod_distances = [unpack('f', f)[0] for _ in range(self._lod_count)]
                elif section_name == 'Pieces':
                    weight_count, pieces_count = unpack('2I', f)
                    model.pieces = [self._read_piece(f) for _ in range(pieces_count)]
                elif section_name == 'Nodes':
                    model.nodes = [self._read_node(f) for _ in range(self._node_count)]
                    build_undirected_tree(model.nodes)
                    weight_set_count = unpack('I', f)[0]
                    model.weight_sets = [self._read_weight_set(f) for _ in range(weight_set_count)]
                elif section_name == 'ChildModels':
                    child_model_count = unpack('H', f)[0]
                    model.child_models = [self._read_child_model(f) for _ in range(child_model_count)]
                elif section_name == 'Animation':
                    animation_count = unpack('I', f)[0]
                    model.animations = [self._read_animation(f) for _ in range(animation_count)]
                elif section_name == 'Sockets':
                    socket_count = unpack('I', f)[0]
                    model.sockets = [self._read_socket(f) for _ in range(socket_count)]
                elif section_name == 'AnimBindings':
                    anim_binding_count = unpack('I', f)[0]
                    model.anim_bindings = [self._read_anim_binding(f) for _ in range(anim_binding_count)]
        return model
