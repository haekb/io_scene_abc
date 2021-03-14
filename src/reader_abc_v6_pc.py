import os
from .abc import *
from .io import unpack
from mathutils import Vector, Matrix, Quaternion
import copy

#
# ABC Model Format Version 6
# Spec: https://web.archive.org/web/20170905023149/http://www.bop-mod.com/download/docs/LithTech-ABC-v6-File-Format.html
#
class ABCV6ModelReader(object):
    def __init__(self):
        self._version_constant = "MonolithExport Model File v6"
        # Node Flags
        self._flag_null = 1
        self._flag_tris = 2 # This node contains triangles
        self._flag_deformation = 4 # This node contains deformation (vertex animation). Used in combo with flag_tris
        # Might be Lithtech 1.5 only flags
        self._flag_env_map = 8
        self._flag_env_map_only = 16
        self._flag_scroll_tex_u = 32
        self._flag_scroll_tex_v = 64

        # Version is actually a string in this format
        # it should always equal `self._version_constant`
        self._version = ""
        self._node_count = 0
        self._lod_count = 0

        self._model = None

    #
    # Helpers
    # TODO: Move to utils
    #
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

    #
    # Format Specific
    #

    def _read_vertex(self, f):
        vertex = Vertex()
        vertex.location = self._read_vector(f)

        vertex_normal_chars = unpack('3b', f)

        vertex.normal.x = vertex_normal_chars[0]
        vertex.normal.y = vertex_normal_chars[1]
        vertex.normal.z = vertex_normal_chars[2]

        weight = Weight()

        # It seems "pieces" are split by node index..
        weight.node_index = unpack('b', f)[0]
        weight.bias = 1.0

        vertex.weights = [ weight ]

        # Jake: From the notes...
        # indices of the model vertices that this vertex replaces -- only really used for 'extra' vertices:  vertices that got added for extra LODs
        vertex_replacements = unpack('2H', f)

        return vertex

    def _read_face_vertex(self, f):
        face_vertex_list = [FaceVertex(), FaceVertex(), FaceVertex()]

        face_vertex_list[0].texcoord.xy = unpack('2f', f)
        face_vertex_list[1].texcoord.xy = unpack('2f', f)
        face_vertex_list[2].texcoord.xy = unpack('2f', f)

        face_vertex_list[0].vertex_index = unpack('H', f)[0]
        face_vertex_list[1].vertex_index = unpack('H', f)[0]
        face_vertex_list[2].vertex_index = unpack('H', f)[0]

        # Jake: Not needed?
        face_normal = unpack('3b', f)

        return face_vertex_list

    def _read_face(self, f):
        face = Face()
        face.vertices = self._read_face_vertex(f)
        return face

    # TODO: Figure out how to extract LOD info
    def _read_lod(self, f):

        vertex_start_number = [ unpack('H', f)[0] for _ in range(self._lod_count + 1) ]

        lod_list = []

        main_lod = LOD()
        face_count = unpack('I', f)[0]
        main_lod.faces = [self._read_face(f) for _ in range(face_count)]
        vertex_count = unpack('I', f)[0]

        # Non-LOD vertex count
        normal_count = unpack('I', f)[0]

        # FIXME: I can't figure out how the face data relates to LODs, so let's just load the top LOD for now!
        for i in range(self._lod_count + 1):
            lod = LOD()

            if (i == self._lod_count):
                count = normal_count
            else:
                continue
                #count = vertex_start_number[i + 1] - vertex_start_number[i]

            lod.faces = copy.deepcopy(main_lod.faces)
            lod.vertices = [self._read_vertex(f) for _ in range(count)]

            lod_list.append(lod)
        # End For

        return lod_list

    # Note: Only ever 1 piece
    def _read_piece(self, f):
        piece = Piece()
        piece.material_index = 0
        piece.specular_power = 0
        piece.specular_scale = 1
        piece.name = "Piece"

        # Jake: Where do I stick these? hmmm
        bounds_min = self._read_vector(f)
        bounds_max = self._read_vector(f)

        self._lod_count = unpack('I', f)[0]

        # Lod returns a list of lods now!
        piece.lods = self._read_lod(f)

        return piece

    def _read_node(self, f):
        node = Node()

        # These may be needed to calculate the position...
        node.bounds_min = self._read_vector(f)
        node.bounds_max = self._read_vector(f)

        # Bind matrix is set after we read in animations!

        node.name = self._read_string(f)
        node.index = unpack('H', f)[0]
        node.flags = unpack('b', f)[0]

        # Vertex animations I think!
        node.md_vert_count = unpack('I', f)[0]
        node.md_vert_list = [unpack('H', f)[0] for _ in range(node.md_vert_count)]

        node.child_count = unpack('I', f)[0]

        return node

    def _read_transform(self, f):
        transform = Animation.Keyframe.Transform()
        transform.location = self._read_vector(f)
        transform.rotation = self._read_quaternion(f)
        return transform

    def _read_vertex_transform(self, f):
        transform = Animation.Keyframe.VertexTransform()
        # Unpack the bytes and shove them into a vector
        # Note: These aren't usable until we process them later on!
        location = unpack('3B', f)
        transform.location = Vector( (location[0], location[1], location[2]) )
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
        bounds_min = self._read_vector(f)
        bounds_max = self._read_vector(f)
        keyframe.string = self._read_string(f)
        return keyframe

    def _read_animation(self, f):

        animation = Animation()
        animation.name = self._read_string(f)
        animation_length = unpack('I', f)[0]
        animation.bounds_min = self._read_vector(f)
        animation.bounds_max = self._read_vector(f)

        # ?
        animation.extents = animation.bounds_max

        animation.keyframe_count = unpack('I', f)[0]
        animation.keyframes = [self._read_keyframe(f) for _ in range(animation.keyframe_count)]

        animation.vertex_deformations = []
        for node_index in range(self._node_count):
            animation.node_keyframe_transforms.append( [self._read_transform(f) for _ in range(animation.keyframe_count)] )

            md_vert_count = self._model.nodes[node_index].md_vert_count

            # Temp store the unprocessed vertex deformations
            if (md_vert_count > 0):
                animation.vertex_deformations.append( [self._read_vertex_transform(f) for _ in range(animation.keyframe_count * md_vert_count)]  )
            else:
                # Empty!
                animation.vertex_deformations.append([])
            # End

            # Only used with vertex animations
            scale = self._read_vector(f)
            transform = self._read_vector(f)

            vertex_len = len(animation.vertex_deformations[node_index])

            # Process the vertex deformations
            for i in range(vertex_len):
                deformation = animation.vertex_deformations[node_index][i].location

                # To get the proper coordinates we must multiply our 0-255 vertex deformation by the scale value, then add the transform
                # Oddly enough this is exactly how Quake 2 does it..HMMM...
                deformation.x = (deformation.x * scale.x) + transform.x
                deformation.y = (deformation.y * scale.y) + transform.y
                deformation.z = (deformation.z * scale.z) + transform.z
        # End For

        return animation
    # End Function

    def _read_animation_dims(self, f):
        # We're not using animation dims right now,
        # so we'll just read it and ignore it!
        animation_count = len(self._model.animations)
        animation_dims = []
        for _ in range(animation_count):
            animation_dims.append( self._read_vector(f) )
    # End Function

    def _read_transform_info(self, f):
        flip_geom = unpack('I', f)[0]
        flip_anim = unpack('I', f)[0]

        return (flip_geom, flip_anim)
    # End Function


    def from_file(self, path):
        self._model = Model()
        self._model.name = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'rb') as f:
            next_section_offset = 0
            while next_section_offset != -1:
                f.seek(next_section_offset)
                section_name = self._read_string(f)
                next_section_offset = unpack('i', f)[0]

                # Header Section
                if section_name == 'Header':

                    self._version = self._read_string(f)
                    if self._version != self._version_constant:
                        raise Exception('Unsupported file version ({}).'.format(self._version))

                    self._model.version = 6
                    self._model.command_string = self._read_string(f)

                # Geometry Section
                elif section_name == 'Geometry':
                    self._model.pieces = [ self._read_piece(f) ]

                # Node Section
                elif section_name == 'Nodes':

                    # Depth first ordered,
                    # Just keep track of a running total of children
                    # once it hits zero, we can exit.
                    children_left = 1
                    while children_left != 0:
                        # increment our node count!
                        self._node_count += 1


                        children_left -= 1
                        node = self._read_node(f)
                        children_left += node.child_count
                        self._model.nodes.append(node)

                    build_undirected_tree(self._model.nodes)
                # End

                # Animation Section
                elif section_name == 'Animation':
                    animation_count = unpack('I', f)[0]
                    self._model.animations = [self._read_animation(f) for _ in range(animation_count)]

                # Animation Dims Section
                elif section_name == 'AnimDims':
                    self._read_animation_dims(f)

                # Transform Info Section
                elif section_name == 'TransformInfo':
                    flip_geom, flip_anim = self._read_transform_info(f)
                    # See the model details for info on these flags
                    self._model.flip_geom = flip_geom
                    self._model.flip_anim = flip_anim
        # End

        # Okay we're going to use the first animation's location and rotation data for our node's bind_matrix
        for node_index in range(len(self._model.nodes)):
            node = self._model.nodes[node_index]
            reference_transform = self._model.animations[0].node_keyframe_transforms[node_index][0]

            mat_scale = Matrix()

            if self._model.flip_anim:
                reference_transform.rotation.conjugate()
            # End

            mat_rot = reference_transform.rotation.to_matrix()
            mat_loc = Matrix.Translation(reference_transform.location)
            mat = mat_loc @ mat_rot.to_4x4() @ mat_scale

            parent_matrix = Matrix()

            if node.parent:
                parent_matrix = node.parent.bind_matrix
            # End

            # Apply it!
            node.bind_matrix = parent_matrix @ mat
            node.inverse_bind_matrix = node.bind_matrix.inverted()
        # End

        # Ok now we're going to apply out mesh offset
        vert_index = 0
        for vert in self._model.pieces[0].lods[0].vertices:
            node_index = vert.weights[0].node_index
            md_vert_count = self._model.nodes[node_index].md_vert_count

            # Apply the first frame of vertex animation deformation
            if md_vert_count > 0:

                # Find the position of the vertex we're going to deform
                md_vert = self._model.nodes[node_index].md_vert_list.index(vert_index)

                # Grab are transformed deformation
                vertex_transform = self._model.animations[0].vertex_deformations[node_index][md_vert].location

                vert.location = self._model.nodes[node_index].bind_matrix @ vertex_transform
            else:
                vert.location = self._model.nodes[node_index].bind_matrix @ vert.location
            # End

            vert.normal = self._model.nodes[node_index].bind_matrix @ vert.normal
            vert_index += 1
        # End

        return self._model
