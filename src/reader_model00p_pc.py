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

# Animation processing values
ANIM_No_Compression = 0
ANIM_Compression = 1
ANIM_Carry_Over = 2

Invalid_Bone = 255

#
# Supports Model00p v33 (FEAR)
#
class PCModel00PackedReader(object):
    def __init__(self):
        self.is_little_endian = True
    
        self.version = 0
        self.node_count = 0
        self.lod_count = 0
        self.string_table = ""

    #
    # Wrapper around .io.unpack that can eventually handle big-endian reads.
    #
    def _unpack(self, fmt, f):

        # Force big endian if we're not little!
        if self.is_little_endian == False:
            fmt = '>%s' % fmt

        return unpack(fmt, f)

    def _get_string_from_table(self, offset):
        value = self.string_table[offset:]

        # Okay we need to find the next null character now!
        null_terminator = -1
        for (index, char) in enumerate(value):
            if char == '\x00':
                null_terminator = index
                break

        # Make sure we actually ran through the string
        assert(null_terminator != -1)

        length = offset + null_terminator
            
        return self.string_table[offset:length]

    def _read_matrix(self, f):
        data = self._unpack('16f', f)
        rows = [data[0:4], data[4:8], data[8:12], data[12:16]]
        return Matrix(rows)

    def _read_short_vector(self, f):
        x,y,z = self._unpack('3H', f)
        return [x,y,z]

    def _read_vector(self, f):
        return Vector(self._unpack('3f', f))

    def _read_short_quaternion(self, f):
        x, y, z, w = self._unpack('4H', f)
        return [w,x,y,z]

    def _read_quaternion(self, f):
        x, y, z, w = self._unpack('4f', f)
        return Quaternion((w, x, y, z))

    def _read_string(self, f):
        return f.read(self._unpack('H', f)[0]).decode('ascii')

    def _read_fixed_string(self, length, f):
        return f.read(length).decode('ascii')

    def _read_weight(self, f):
        weight = Weight()
        weight.node_index = self._unpack('I', f)[0]
        weight.location = self._read_vector(f)
        weight.bias = self._unpack('f', f)[0]
        return weight

    def _read_vertex(self, f):
        vertex = Vertex()
        weight_count = self._unpack('H', f)[0]
        vertex.sublod_vertex_index = self._unpack('H', f)[0]
        vertex.weights = [self._read_weight(f) for _ in range(weight_count)]
        vertex.location = self._read_vector(f)
        vertex.normal = self._read_vector(f)
        return vertex

    def _read_face_vertex(self, f):
        face_vertex = FaceVertex()
        face_vertex.texcoord.xy = self._unpack('2f', f)
        face_vertex.vertex_index = self._unpack('H', f)[0]
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

                    vertex.weights.append(weight)

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

                    weights.append(weight)

                    vertex.weights = weights
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
            for vertex_index in range(index_start, index_start + index_count):
                vertex = lod.vertices[vertex_index]

                # We need to re-build the weight list for our vertex
                weights = []

                for (index, bone_index) in enumerate(bone_list):
                    # If we've got an invalid bone (255) then ignore it
                    if bone_index == Invalid_Bone:
                        continue
                    # End If

                    vertex.weights[index].node_index = bone_index
                    # Keep this one!
                    weights.append(vertex.weights[index])
                # End For

                total = 0.0
                for weight in weights:
                    total += weight.bias

                assert(total != 0.0)

                vertex.weights = weights
            #End For
        # End For

        return lod

    def _read_lod(self, f):
        lod = LOD()

        lod.texture_count = unpack('I', f)[0]
        lod.textures = unpack('4I', f)
        lod.render_style = unpack('I', f)[0]
        lod.render_priority = unpack('b', f)[0]

        lod.type = unpack('I', f)[0]

        # Check if it's a null mesh, it skips a lot of the data...
        if lod.type == LTB_Type_Null_Mesh:
            # Early return here, because there's no more data...
            lod = self._read_null_mesh(lod, f)
        else:
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

        # Just use the first LODs first texture
        if lod_count > 0:
            piece.material_index = piece.lods[0].textures[0]

        return piece

    def _read_node(self, f):
        node = Node()
        name_offset = self._unpack('I', f)[0]
        node.name = self._get_string_from_table(name_offset)
        node.index = self._unpack('H', f)[0]
        node.flags = self._unpack('b', f)[0]

        node.location = self._read_vector(f)
        node.rotation = self._read_quaternion(f)

        # Transform location/rotation into a bind matrix!
        mat_rot = node.rotation.to_matrix()
        mat_loc = Matrix.Translation(node.location)
        node.bind_matrix = mat_loc @ mat_rot.to_4x4()

        node.inverse_bind_matrix = node.bind_matrix.inverted()
        node.child_count = self._unpack('I', f)[0]
        return node

    def _read_uncompressed_transform(self, f):
        transform = Animation.Keyframe.Transform()

        transform.location = self._read_vector(f)
        transform.rotation = self._read_quaternion(f)

        return transform

    def _process_compressed_vector(self, compressed_vector):
        return Vector( (compressed_vector[0] / 16.0, compressed_vector[1] / 16.0, compressed_vector[2] / 16.0) )

    def _process_compressed_quat(self, compressed_quat):
        return Quaternion( (compressed_quat[3] / 0x7FFF, compressed_quat[0] / 0x7FFF, compressed_quat[1] / 0x7FFF, compressed_quat[2] / 0x7FFF) )

    def _read_compressed_transform(self, compression_type, keyframe_count, f):
        
        node_transforms = []

        for _ in range(self.node_count):
            # RLE!
            key_position_count = unpack('I', f)[0]

            compressed_positions = []
            if compression_type == CMP_Relevant or compression_type == CMP_Relevant_Rot16:
                compressed_positions = [self._read_vector(f) for _ in range(key_position_count)]
            elif compression_type == CMP_Relevant_16:
                compressed_positions = [self._process_compressed_vector(unpack('3h', f)) for _ in range(key_position_count)]
            # End If

            key_rotation_count = unpack('I', f)[0]

            compressed_rotations = []
            if compression_type == CMP_Relevant:
                compressed_rotations = [self._read_quaternion(f) for _ in range(key_rotation_count)]
            elif compression_type == CMP_Relevant_16 or compression_type == CMP_Relevant_Rot16:
                compressed_rotations = [self._process_compressed_quat(unpack('4h', f)) for _ in range(key_rotation_count)]
            # End If

            transforms = []

            previous_position = Vector( (0, 0, 0) )
            previous_rotation = Quaternion( (1, 0, 0, 0) )

            # RLE animations, if it doesn't change in any additional keyframe,
            # then it we can just use the last known pos/rot!
            for i in range(keyframe_count):
                transform = Animation.Keyframe.Transform()

                try:
                    transform.location = compressed_positions[i]
                except IndexError:
                    transform.location = previous_position

                try:
                    transform.rotation = compressed_rotations[i]
                except IndexError:
                    transform.rotation = previous_rotation

                previous_position = transform.location
                previous_rotation = transform.rotation

                transforms.append(transform)
            # End For

            node_transforms.append(transforms)
        # End For

        return node_transforms

    def _read_child_model(self, f):
        child_model = ChildModel()
        child_model.name = self._read_string(f)
        return child_model

    def _read_keyframe(self, f):
        keyframe = Animation.Keyframe()
        keyframe.time = unpack('I', f)[0]
        string_offset = unpack('I', f)[0]
        keyframe.string = self._get_string_from_table(string_offset)
        return keyframe

    def _read_animation(self, f):
        animation = Animation()
        animation.extents = self._read_vector(f)
        animation.name = self._read_string(f)
        animation.compression_type = unpack('i', f)[0]
        animation.interpolation_time = unpack('I', f)[0]
        animation.keyframe_count = unpack('I', f)[0]
        animation.keyframes = [self._read_keyframe(f) for _ in range(animation.keyframe_count)]
        animation.node_keyframe_transforms = []

        if animation.compression_type == CMP_None:
            for _ in range(self.node_count):
                animation.is_vertex_animation = unpack('b', f)[0]

                # We don't support vertex animations yet, so alert if we accidentally load some!
                assert(animation.is_vertex_animation == 0)

                animation.node_keyframe_transforms.append(
                    [self._read_uncompressed_transform(f) for _ in range(animation.keyframe_count)])
            # End For
        else:
            animation.node_keyframe_transforms = self._read_compressed_transform(animation.compression_type, animation.keyframe_count, f)
        # End If

        return animation

    def _read_socket(self, f):
        socket = Socket()
        socket.node_index = unpack('I', f)[0]
        socket.name = self._read_string(f)
        socket.rotation = self._read_quaternion(f)
        socket.location = self._read_vector(f)
        socket.scale = self._read_vector(f)
        return socket

    def _read_anim_binding(self, f):
        anim_binding = AnimBinding()

        anim_binding.extents = self._read_vector(f)
        
        anim_binding.radius = self._unpack('f', f)[0]

        name_offset = self._unpack('I', f)[0]
        anim_binding.name = self._get_string_from_table(name_offset)

        anim_binding.interpolation_time = self._unpack('I', f)[0]

        anim_binding.animation_header_index = self._unpack('I', f)[0]
        anim_binding.data_position = self._unpack('I', f)[0]
        anim_binding.is_compressed = self._unpack('I', f)[0]

        fin = True

        return anim_binding

    def _read_anim_info(self, f):
        anim_info = AnimInfo()

        anim_info.binding = self._read_anim_binding(f)

        anim_info.animation.extents = anim_info.binding.extents 
        anim_info.animation.interpolation_time = anim_info.binding.interpolation_time
        anim_info.animation.name = anim_info.binding.name
        anim_info.animation.keyframe_count = self._unpack('I', f)[0]
        anim_info.animation.keyframes = [self._read_keyframe(f) for _ in range(anim_info.animation.keyframe_count)]

        return anim_info

    def _read_weight_set(self, f):
        weight_set = WeightSet()
        weight_set.name = self._read_string(f)
        node_count = unpack('I', f)[0]
        weight_set.node_weights = [unpack('f', f)[0] for _ in range(node_count)]
        return weight_set

        
    def _read_flag(self, is_location, current_track, data_length):
        # Location data (Not Compressed and Compressed)
        if data_length == 0xC:
            return { 'type': 'location', 'track': current_track, 'process': ANIM_No_Compression }
        elif data_length == 0x6:
            return { 'type': 'location', 'track': current_track, 'process': ANIM_Compression }
        # Rotation data (Compressed)
        elif data_length == 0x8:
            return { 'type': 'rotation', 'track': current_track, 'process': ANIM_Compression }
        # Carry overs
        elif data_length == 0xFFFF and is_location:
            return { 'type': 'location', 'track': current_track, 'process': ANIM_Carry_Over }
        elif data_length == 0xFFFF and not is_location:
            return { 'type': 'rotation', 'track': current_track, 'process': ANIM_Carry_Over }

        # Fallback in-case data is out of line!
        raise Exception("Invalid data length (%d) for current track (%d). Is location flag (%d)" % (data_length, current_track, is_location))
    # End Def

    def _read_animation_schema(self, f):
        # Basically a map for how we'll read a particular animation
        # We return this data at the end of this function
        compression_schema = []

        # Data counters
        total_data_read = 0
        track_data_read = [0, 0]

        # Generally the data flip flops between Location/Rotation/etc...
        is_location = True

        track_1_size = self._unpack('H', f)[0]
        track_2_size = self._unpack('H', f)[0]

        total_track_size = track_1_size + track_2_size

        # Safety, this shouldn't happen!
        assert(total_track_size != 0)

        # By default start on track 1
        current_track = 1

        # Special case, in case the first flag is 0xFFFF
        if track_2_size > 0 and track_1_size == 0:
            current_track = 2

        # This almost works. It turns out everything is location/rotation
        # But we just need to determine if the file is compressed...
        flag_position = f.tell()
        is_compressed = False
        
        # Hacky way to figure out if we're dealing with compressed location data
        # Some special cases up front, then a quick peak at the data to determine if compression is used!
        if total_track_size == 0x6:
            # If we're simply one location entry, and it's 0x6..then we're compressed!
            is_compressed = True
        elif total_track_size == 0x8:
            # We don't actually care about location here, as it's not used!
            is_compressed = False
        else:
            _total = 0
            # Run ahead a bit and check
            while True:
                flag = self._unpack('H', f)[0]
                
                if flag == 0xFFFF:
                    continue

                if flag >= 0x8000:
                    flag -= 0x8000

                flag -= _total

                if flag == 0x6:
                    is_compressed = True
                    break
                elif flag == 0xC:
                    is_compressed = False
                    break

                _total += flag
            # End While

        # Move back to the flag position
        f.seek(flag_position, 0)

        # Use is_compressed to determine what we're stepping up by, and swap location = not location!
        while True: #not wrap_up and total_data_read < total_track_size:
            debug_ftell = f.tell()

            # Read the next flag
            flag = self._unpack('H', f)[0]

            if flag == 0xFFFF:
                compression_schema.append(self._read_flag(is_location, current_track, flag))
                is_location = not is_location
                continue
            # End condition
            elif total_data_read == total_track_size:
                # Okay no more flags? Then move back one flag's worth of bytes, and quit
                f.seek(-2, 1)
                break

            # So if we're at or above 0x8000, we're on track 1
            # To get the real bytes written, we need to remove the 0x8000 bit...
            if flag >= 0x8000:
                current_track = 1
            else:
                current_track = 2


            # If rotation
            data_length = 0x8

            if is_location:
                if is_compressed:
                    data_length = 0x6
                else:
                    data_length = 0xC

            compression_schema.append(self._read_flag(is_location, current_track, data_length))

            is_location = not is_location

            total_data_read += data_length
            track_data_read[ current_track - 1 ] += data_length
        # End While

        ##
        # DEBUG

        location_count = 0
        rotation_count = 0

        for schema in compression_schema:
            if schema['type'] == 'location':
                location_count += 1
            else:
                rotation_count += 1
        # End For

        print("Testing out count: %d == %d ?" % (location_count, rotation_count))
        assert(location_count == rotation_count)

        ##

        return compression_schema
    # End Def

    def from_file(self, path):
        model = Model()
        model.name = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'rb') as f:

            file_format = self._read_fixed_string(4, f)

            # Are we big-endian?
            if file_format == "LDOM":
                print("!! Big-endian Model00p loaded. Haven't tested this yet, may be bugs!!!")
                self.is_little_endian = False
            # No, then make sure we're little endian
            elif file_format != "MODL":
                raise Exception('Unsupported File Format! Only Model00p files are supported.')
            # End If

            self.version = self._unpack('I', f)[0]

            # Fear and Condemned
            if self.version not in [33, 34]:
                raise Exception('Unsupported File Version! Importer currently only supports v33/v34.')
            # End If

            model.version = self.version

            keyframe_count = self._unpack('I', f)[0]
            animation_count = self._unpack('I', f)[0]
            self.node_count = self._unpack('I', f)[0]
            piece_count = self._unpack('I', f)[0]
            child_model_count = self._unpack('I', f)[0]
            self.lod_count = self._unpack('I', f)[0]
            socket_count = self._unpack('I', f)[0]
            animation_weight_count = self._unpack('I', f)[0]
            animation_schema_count = self._unpack('I', f)[0]
            string_data_length = self._unpack('I', f)[0]
            physics_weight_count = self._unpack('I', f)[0]
            physics_shape_count = self._unpack('I', f)[0]
            unk_12 = self._unpack('I', f)[0] # ??
            unk_13 = self._unpack('I', f)[0] # ??
            # Physics Constraints
            stiff_sprint_constraint_count = self._unpack('I', f)[0]
            hinge_constraint_count = self._unpack('I', f)[0]
            limited_hinge_constraint_count = self._unpack('I', f)[0]
            ragdoll_constraint_count = self._unpack('I', f)[0]
            wheel_constraint_count = self._unpack('I', f)[0]
            prismatic_constraint_count = self._unpack('I', f)[0]
            # End
            animation_data_length = self._unpack('I', f)[0]
            self.string_table = self._read_fixed_string(string_data_length, f)

            #
            # Nodes
            #
            model.nodes = [self._read_node(f) for _ in range(self.node_count)]
            build_undirected_tree(model.nodes)

            #
            # Animations
            #
            unknown = self._unpack('I', f)[0]

            # What is it? We'll find out...one day...
            if unknown != 0:
                print("Unknown animation value is not 0! It's %d" % unknown)

            # RLE
            # Process lists, TRUE if the value is there, FALSE if it's assumed data.
            # Dictionary per animation, Location/Rotation
            animation_schemas = []

            for _ in range(animation_schema_count):
                animation_schemas.append(self._read_animation_schema(f))

            # Okay save the current position, and read ahead to the keyframe data
            animation_position = f.tell()

            # Skip ahead to keyframes!
            f.seek(animation_data_length , 1)

            #model.anim_bindings = [self._read_anim_binding(f) for _ in range(animation_binding_count)]
            anim_infos = [self._read_anim_info(f) for _ in range(animation_count)] 

            animation_binding_position = f.tell()
            f.seek(animation_position, 0)

            #########################################################################
            # Animation Pass

            # Special case read
            locations = []
            rotations = []

            default_locations = []
            default_rotations = []

            # Note: Defaults should be the node transform values, not Vector(0,0,0) for example.

            for node in model.nodes:
                default_locations.append(node.location)
                default_rotations.append(node.rotation)

            def decompress_vec(compressed_vec):
                for i in range(len(compressed_vec)):
                    if compressed_vec[i] != 0:
                        compressed_vec[i] /= 64.0

                return Vector( compressed_vec )

            # Not really it, but a starting point!
            def decompres_quat(compresed_quat):
                # Find highest number, assume that's 1.0
                largest_number = -1
                for quat in compresed_quat:
                    if quat > largest_number:
                        largest_number = quat

                for i in range(len(compresed_quat)):
                    if compresed_quat[i] != 0:
                        compresed_quat[i] /= largest_number

                return Quaternion( compresed_quat )

            # Small helper function
            def handle_carry_over(flag_type, keyframe_list, defaults_list, keyframe_index, node_index):
                if keyframe_index == 0:
                    return defaults_list[node_index]

                transform = keyframe_list[ keyframe_index - 1 ]

                if flag_type == 'location':
                    return transform.location

                return transform.rotation
                

            # Should match up with animation count...
            for anim_info in anim_infos:
                # For ... { 'type': 'location', 'track': current_track, 'process': ANIM_No_Compression }

                section = animation_schemas[anim_info.binding.animation_header_index]
                
                for keyframe_index in range(anim_info.animation.keyframe_count):
                    section_index = 0
                    for node_index in range(self.node_count):

                        # Make sure we have space here...
                        try:
                            anim_info.animation.node_keyframe_transforms[node_index]
                        except:
                            anim_info.animation.node_keyframe_transforms.append([])
                        
                        transform = Animation.Keyframe.Transform()

                        # Flags are per keyframe
                        flags = [ section[ section_index ], section[ section_index + 1 ] ]
                        section_index += 2

                        # Let's assume that it's always Location/Rotation
                        for flag in flags:
                            debug_ftell = f.tell()
                            
                            process = flag['process']

                            if flag['type'] == 'location':
                                if process == ANIM_No_Compression:
                                    transform.location = self._read_vector(f)
                                elif process == ANIM_Compression:
                                    transform.location = decompress_vec(self._read_short_vector(f))
                                elif process == ANIM_Carry_Over:
                                    transform.location = handle_carry_over( flag['type'], anim_info.animation.node_keyframe_transforms[node_index], default_locations, keyframe_index, node_index )
                            else:
                                if process == ANIM_Compression:
                                    transform.rotation = decompres_quat(self._read_short_quaternion(f))
                                elif process == ANIM_Carry_Over:
                                    transform.rotation = handle_carry_over( flag['type'], anim_info.animation.node_keyframe_transforms[node_index], default_rotations, keyframe_index, node_index )
                        # End For (Flag)

                        # Insert the transform 
                        anim_info.animation.node_keyframe_transforms[node_index].append(transform)
                    
                    # End For (Node)
                # End For (Keyframe)
                
                model.animations.append(anim_info.animation)

            

            # End Pass
            #########################################################################


            return model
#old
            # #
            # # HEADER
            # #
            # file_format = unpack('H', f)[0]
            # file_version = unpack('H', f)[0]

            # if file_type is not 1:
            #     raise Exception('Unsupported File Type! Only mesh LTB files are supported.')
            # # End If

            # if file_version is not 9:
            #     raise Exception('Unsupported File Version! Importer currently only supports v9.')
            # # End If

            # # Skip 4 ints
            # f.seek(4 * 4, 1)

            # self.version = unpack('i', f)[0]

            # if self.version not in [23, 24, 25]:
            #     raise Exception('Unsupported file version ({}).'.format(self.version))
            # # End If

            # model.version = self.version

            # keyframe_count = unpack('i', f)[0]
            # animation_count = unpack('i', f)[0]
            # self.node_count = unpack('i', f)[0]
            # piece_count = unpack('i', f)[0]
            # child_model_count = unpack('i', f)[0]
            # face_count = unpack('i', f)[0]
            # vertex_count = unpack('i', f)[0]
            # vertex_weight_count = unpack('i', f)[0]
            # lod_count = unpack('i', f)[0]
            # socket_count = unpack('i', f)[0]
            # weight_set_count = unpack('i', f)[0]
            # string_count = unpack('i', f)[0]
            # string_length = unpack('i', f)[0]
            # vertex_animation_data_size = unpack('i', f)[0]
            # animation_data_size = unpack('i', f)[0]

            # model.command_string = self._read_string(f)

            # model.internal_radius = unpack('f', f)[0]

            # #
            # # OBB Information
            # #
            # obb_count = unpack('i', f)[0]

            # obb_size = 64

            # if self.version > 23:
            #     obb_size += 4

            # # OBB information is a matrix per each node
            # # We don't use it anywhere, so just skip it.
            # f.seek(obb_size * obb_count, 1)

            # #
            # # Pieces
            # # 

            # # Yep again!
            # piece_count = unpack('i', f)[0]
            # model.pieces = [self._read_piece(f) for _ in range(piece_count)]

            # #
            # # Nodes
            # #
            # model.nodes = [self._read_node(f) for _ in range(self.node_count)]
            # build_undirected_tree(model.nodes)
            # weight_set_count = unpack('I', f)[0]
            # model.weight_sets = [self._read_weight_set(f) for _ in range(weight_set_count)]

            # #
            # # Child Models
            # # 
            # child_model_count = unpack('I', f)[0]
            # model.child_models = [self._read_child_model(f) for _ in range(child_model_count - 1)]

            # #
            # # Animations
            # # 
            # animation_count = unpack('I', f)[0]
            # model.animations = [self._read_animation(f) for _ in range(animation_count)]

            # #
            # # Sockets
            # # 
            # socket_count = unpack('I', f)[0]
            # model.sockets = [self._read_socket(f) for _ in range(socket_count)]

            # #
            # # Animation Bindings
            # #
            # anim_binding_count = unpack('I', f)[0]

            # #model.anim_bindings = [self._read_anim_binding(f) for _ in range(anim_binding_count)]

            # for _ in range(anim_binding_count):
            #     # Some LTB animation binding information can be incorrect...
            #     # Almost like the mesh was accidentally cut off, very odd!
            #     try:
            #         model.anim_bindings.append(self._read_anim_binding(f))
            #     except Exception:
            #         pass

            # return model
