import os
from .abc import *
from .io import unpack
from mathutils import Vector, Matrix, Quaternion
from functools import cmp_to_key
import math
import copy
from .hash_ps2 import HashLookUp

#########################################################################################
# PS2 LTB Model Reader by Jake Breen
# 
# Heavily WIP and won't import much right now
# Based off the original ModelReader (now ABCModelReader)
# This will only work with NOLF1 for PS2. 
# If you're aware of other Lithtech PS2 games please notify me! 
# 
# See the 010 Editor Template file for the latest info on the format.
#########################################################################################

# Some constant values to make things slightly more readable:

# Required checks
# PS2 LTB
REQUESTED_FILE_TYPE = 2
# Version of the LTB
REQUESTED_VERSION = 16

# Model Types
MT_RIGID = 4
MT_SKELETAL = 5
MT_VERTEX_ANIMATED = 6

# Winding orders
WO_NORMAL = 0x412
WO_REVERSED = 0x8412

# Vif commands
# From various sources:
# https://gtamods.com/wiki/PS2_Native_Geometry
# https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Codes.cpp
VIF_FLUSH = 0x11
VIF_MSCALF = 0x15000000 # This one likes extra precision
VIF_DIRECT = 0x50 # This is not in the "CMD" spot, so it might just be an application specific data
VIF_UNPACK = 0x6C

FLOAT_COMPARE = 1e-04

# PS2 VIF Command
# Used to tell the ps2 what to do with the data I guess
class VIFCommand(object):
    def __init__(self):
        self.constant = 0
        self.variable = 0
        self.code = 0

    def read(self, f):
        self.constant = unpack('h', f)[0]
        self.variable = unpack('B', f)[0]
        self.code = unpack('B', f)[0]

class EndCommand(object):
    def __init__(self):
        self.code = 0

    def read(self, f):
        f.seek(4 * 3, 1)
        self.code = unpack('i', f)[0]

class LocalVertex(object):
    def __init__(self):
        self.id = 0
        self.merge_string = ""
        self.vertex = Vertex()
        self.associated_ids = []
        
class LocalFace(object):
    def __init__(self):
        self.group_id = 0
        self.face_vertex = FaceVertex()

# End Class

class VertexList(object):
    def __init__(self):
        self.auto_increment = 0
        self.groups = []

        # List of LocalVertex
        self.list = []

        # List of LocalFace
        self.face_verts = []

        # List of Faces (generated)
        self.faces = []
    
    def append(self, vertex, group_id, face_vertex, unknown_flag = False):

        # Create the "local vertex"
        # We store extra info so we can accurately merge duplicates while keeping the mesh set group ids
        local_vertex = LocalVertex()
        local_vertex.id = self.auto_increment
        local_vertex.vertex = vertex
        local_vertex.merge_string = self.generate_merge_string(vertex.location)
        local_vertex.associated_ids.append(group_id)

        # Assign the list count as the vertex index (This will be overridden later if this vertex is a dupe)
        local_face = LocalFace()
        local_face.group_id = group_id

        # Check if the vertex is already in the list (dupe check)
        # If it is, we want the id
        vertex_index = self.find_in_list(local_vertex.merge_string)

        #print("Got Vertex ID: ",vertex_index)

        # Either append our unique vertex, or adjust the face vertex's index with the originals.
        if vertex_index == -1:
            #print("Appending ", local_vertex)
            self.list.append(local_vertex)

            # If the vert is not found, let's use our auto inc, and inc that after!
            vertex_index = self.auto_increment
            self.auto_increment += 1
        else:
            self.list[vertex_index].associated_ids.append(group_id)
            

        face_vertex.vertex_index = vertex_index

        # Finally append the face vertex to the local face
        local_face.face_vertex = face_vertex

        # Gross, but it'll do.
        self.groups.append(group_id)
        self.groups = list(set(self.groups))

        # Save the face vertex
        self.face_verts.append(local_face)


        

    # Loop through all our grouped faces and generate faces based off the vertex_index
    def generate_faces(self):
        faces = []

        print("------------------------------------")
        print("Generating Faces :) ")
        print("Groups: ",self.groups)
        
        for j in range( len(self.groups) ):
            # Generate the faces with alternating order
            flip = False
            group_id = self.groups[j]
            grouped_faces = []

            for i in range( len(self.face_verts) ):
                face_vert = self.face_verts[i]

                if face_vert.group_id != group_id:
                    continue

                grouped_faces.append(face_vert)
            # End Face Verts
            
            for i in range( len(grouped_faces) ):
                if i < 2:
                    continue

                face = Face()

                if grouped_faces[i].face_vertex.reversed:
                    if flip:
                        face.vertices = [ grouped_faces[i - 1].face_vertex, grouped_faces[i].face_vertex, grouped_faces[i - 2].face_vertex ]
                    else:
                        face.vertices = [ grouped_faces[i - 2].face_vertex, grouped_faces[i].face_vertex, grouped_faces[i - 1].face_vertex ]
                else:
                    if flip:
                        face.vertices = [ grouped_faces[i].face_vertex, grouped_faces[i - 1].face_vertex, grouped_faces[i - 2].face_vertex ]
                    else:
                        face.vertices = [ grouped_faces[i].face_vertex, grouped_faces[i - 2].face_vertex, grouped_faces[i - 1].face_vertex ]

                faces.append(face)
                flip = not flip
            # End Grouped Faces
        # End Groups

                
        # End For

        self.faces = faces
    # End of Generate Faces

    # Find the requested merge_string in a list
    # Return the position if true,
    # Return -1 if false.
    def find_in_list(self, merge_string):
        for i in range( len(self.list) ):
            if merge_string == self.list[i].merge_string:
                return i

        return -1

    def generate_merge_string(self, vector):
        return "%f/%f/%f" % (vector.x, vector.y, vector.z)


    def get_vertex_list(self):
        print("Getting vertex list! Length: %d" % len(self.list))
        out_list = []
        for i in range ( len(self.list) ):
            out_list.append(self.list[i].vertex)

        return out_list

    def get_face_list(self):
        return self.faces
# End Class

class PS2LTBModelReader(object):
    def __init__(self):
        self._file_type = 0
        self._version = 0
        self._node_count = 0
        self._lod_count = 0

        # Hack to count sockets
        self._socket_counter = 0

        # Hack to count animation names
        self._animations_processed = 0

        self._hasher = None

    # Leftovers from ABC Model Reader
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

    def _read_lod(self, f):
        lod = LOD()
        face_count = unpack('I', f)[0]
        lod.faces = [self._read_face(f) for _ in range(face_count)]
        vertex_count = unpack('I', f)[0]
        lod.vertices = [self._read_vertex(f) for _ in range(vertex_count)]
        return lod

    def _read_piece(self, f):
        piece = Piece()
        piece.material_index = unpack('H', f)[0]
        piece.specular_power = unpack('f', f)[0]
        piece.specular_scale = unpack('f', f)[0]
        if self._version > 9:
            piece.lod_weight = unpack('f', f)[0]
        piece.padding = unpack('H', f)[0]
        piece.name = self._read_string(f)
        piece.lods = [self._read_lod(f) for _ in range(self._lod_count)]
        return piece

    def _read_node(self, f):
        node = Node()
        node.name = self._read_string(f)
        node.bind_matrix = self._read_matrix(f)
        f.seek(4, 1) 
        node.child_count = unpack('I', f)[0]
        node.index = unpack('H', f)[0]
        # Not confirmed, but likely!
        #node.flag = unpack('H', f)[0]
        f.seek(2, 1)
        return node

    def _read_transform(self, f):

        transform = Animation.Keyframe.Transform()

        # Unpack and transform the values
        location = unpack('3h', f)
        location_small_scale = unpack('h', f)[0] # Flag
        rotation = unpack('4h', f)

        # Constants..kinda. If location small scale is 0, then SCALE_LOC can change.
        SCALE_ROT = 0x4000
        SCALE_LOC = 0x10

        if location_small_scale == 0:
            SCALE_LOC = 0x1000

        transform.location.x = location[0] / SCALE_LOC
        transform.location.y = location[1] / SCALE_LOC
        transform.location.z = location[2] / SCALE_LOC

        transform.rotation.x = rotation[0] / SCALE_ROT
        transform.rotation.y = rotation[1] / SCALE_ROT
        transform.rotation.z = rotation[2] / SCALE_ROT
        transform.rotation.w = rotation[3] / SCALE_ROT

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
        animation.name = "Animation_%d" % self._animations_processed
        animation.extents = self._read_vector(f)

        unknown_vector_maybe = self._read_vector(f)
        hashed_string = unpack('I', f)[0]
        animation.interpolation_time = unpack('I', f)[0]
        animation.keyframe_count = unpack('I', f)[0]
        animation.keyframes = [self._read_keyframe(f) for _ in range(animation.keyframe_count)]
        animation.node_keyframe_transforms = []
        for _ in range(self._node_count):
            start_marker = unpack('I', f)[0]
            animation.node_keyframe_transforms.append(
                [self._read_transform(f) for _ in range(animation.keyframe_count)])

        self._animations_processed += 1

        # Check if we can figure out the hashed string
        looked_up_value = self._hasher.lookup_hash(hashed_string, "animations")

        if (looked_up_value != None):
            animation.name = looked_up_value

        return animation
    # End Function

    
    def _read_socket(self, f):
        socket = Socket()
        # We don't know all the values here, so skip the ones we can't use yet.
        # Refer to the bt file for exact specs
        f.seek(4, 1)
        socket.rotation = self._read_quaternion(f)
        socket.location = self._read_vector(f)
        f.seek(4, 1)
        socket.node_index = unpack('I', f)[0]
        hashed_string = unpack('I', f)[0]

        f.seek(4, 1)

        # Fill in some missing data
        socket.name = "Socket" + str(self._socket_counter)
        self._socket_counter += 1

        # Check if we can figure out the hashed string
        looked_up_value = self._hasher.lookup_hash(hashed_string, "sockets")

        if (looked_up_value != None):
            socket.name = looked_up_value

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

    # Rough WIP
    def from_file(self, path):
        model = Model()
        model.name = os.path.splitext(os.path.basename(path))[0]

        with open(path, 'rb') as f:

            # Header
            self._file_type = unpack('i', f)[0]
            self._version = unpack('i', f)[0]

            print("-------------------------------")
            print("LithTech LTB (PS2) Model Reader")
            print("Loading ltb version %d" % self._version)

            # TODO: This should be done before ModelReader, 
            # so we can split off to ltb (pc) and ltb (ps2) as needed.
            if self._file_type is not REQUESTED_FILE_TYPE:
                message = "LTB Importer only supports PS2 LTB files."
                raise Exception(message)
                
            if self._version is not REQUESTED_VERSION:
                message = "LTB Importer only supports version %d." % REQUESTED_VERSION
                raise Exception(message)

            # Skip past the 3 unknown ints
            f.seek(12, 1)

            # The position for this offset section...
            offset_offset = unpack('i', f)[0]
            piece_offset = unpack('i', f)[0]
            node_offset = unpack('i', f)[0]
            child_model_offset = unpack('i', f)[0]
            animation_offset = unpack('i', f)[0]
            socket_offset = unpack('i', f)[0]
            file_size = unpack('i', f)[0]
            unknown = unpack('i', f)[0]
            # End Header

            # Model Info
            keyframe_count = unpack('i', f)[0]
            animation_count = unpack('i', f)[0]
            self._node_count = unpack('i', f)[0]
            piece_count = unpack('i', f)[0]
            child_model_count = unpack('i', f)[0]
            triangle_count = unpack('i', f)[0]
            vertex_count = unpack('i', f)[0]
            weight_count = unpack('i', f)[0]
            lod_count = unpack('i', f)[0]
            socket_count = unpack('i', f)[0]
            weight_set_count = unpack('i', f)[0]
            string_count = unpack('i', f)[0]
            string_length_count = unpack('i', f)[0]
            model_info_unknown = unpack('i', f)[0]
            
            model.command_string = self._read_string(f)
            model.internal_radius = unpack('f', f)[0]
            # End Model Info

            # Piece Header
            hash_magic_number = unpack('i', f)[0]
            f.seek(4 * 2, 1)
            # End Piece Header

            # Setup our hasher
            self._hasher = HashLookUp(hash_magic_number)


            # We can have multiple pieces!
            for piece_index in range( piece_count ):
                print("------------------------------------")
                print("New Piece!")

                # Used when loading the actual mesh data
                # If the previous chunk was 13kb+, 
                # then we need to peek and see if there's more data instead of the next piece
                check_for_more_data = False

                #########################################################################
                # FIXME: This probably isn't needed anymore.
                # HACK: Skip past any bone information, we're going to be looking for 0.8, 0.8, 0.8!
                # Skip past the unknown value
                f.seek(4, 1)

                exit_piece_early = False

                print ("HACK: Looking for Vector3 of 0.8f")
                while True:
                    try:
                        hero_eights = [ unpack('f', f)[0], unpack('f', f)[0], unpack('f', f)[0] ]

                        if math.isclose(hero_eights[0], 0.8, rel_tol=FLOAT_COMPARE) and math.isclose(hero_eights[1], 0.8, rel_tol=FLOAT_COMPARE) and math.isclose(hero_eights[2], 0.8, rel_tol=FLOAT_COMPARE):
                            print("Found 0.8,0.8,0.8")
                            break

                        # We only want to move up one!
                        f.seek(-4*2, 1)
                    except struct.error as err:
                        exit_piece_early = True
                        print("Could not find Vector3 of 0.8f, reached end of file.")
                        break
                        
                if exit_piece_early == True:
                    break

                # Revert back to our original position
                f.seek(-(4*5), 1) 
                # End Hack !
                #########################################################################

                # Piece
                f.seek(4 * 14, 1)

                # Handy!
                texture_index = unpack('i', f)[0]

                # Skip past 3 unknowns
                f.seek(4 * 3, 1)

                mesh_type = unpack('i', f)[0]
                # End Piece

                if mesh_type is MT_RIGID:
                    print("Rigid Mesh")
                elif mesh_type is MT_SKELETAL:
                    print("Skeletal Mesh")
                elif mesh_type is MT_VERTEX_ANIMATED: # Haven't tested or found a VA mesh!
                    print("Vertex Animated Mesh")

                # LODs
                finished_lods = False
    
                lod = LOD()
                vertex_list = VertexList()
                mesh_set_index = 1 # this gets multiplied
                mesh_index = 0 # triangle_count + vertex_count

                # Amount of shorts that make up the unknown section before vertex weighting information
                lod_skeletal_unk_sector_count = 0

                # There's two additional ints with skeletal meshes 
                if mesh_type is MT_SKELETAL:
                    f.seek( 4 , 1)
                    lod_skeletal_unk_sector_count = unpack('i', f)[0]

                # These are used for our vertex weights!
                lod_vertex_count = unpack('i', f)[0]
                lod_weighted_nodes_count = unpack('i', f)[0]

                # Haven't mapped out pieces yet...
                piece_object = Piece()
                piece_object.name = "Piece %d" % piece_index
                piece_object.material_index = texture_index

                print("Piece %d " % piece_index)

                # For Each lod (Not really implemented like that right now..)
                while finished_lods == False:

                    peek_amount = 0

                    # If they reached about 13kb of data
                    # then check ahead to see if they have an unpack VIF command
                    # that *usually* signifies there's more data.
                    if check_for_more_data == True:
                        print("Checking for more data...")

                        # SizeOf(LODGlue)
                        peek_amount += 28

                        f.seek(peek_amount, 1)
                        vif_cmd = VIFCommand()
                        vif_cmd.read(f)

                        # Okay move back to the start
                        f.seek(-(peek_amount + 4), 1)

                        # If it's not our magic info (Unpack Signal) then there's probably no more data here.
                        if (vif_cmd.constant is not VIF_DIRECT or vif_cmd.code is not VIF_UNPACK):
                            print("No more data found!")
                            finished_lods = True
                            break
                        # End If

                        print("Found an additional batch of data!")
                        check_for_more_data = False
                    # End If

                    # LOD Glue 
                    unknown_command = VIFCommand()
                    # 4 Bytes
                    unknown_command.read(f)

                    # Skip unknown
                    f.seek(4, 1)

                    # This will either be a flush command, or 0
                    flush_command = VIFCommand()
                    # 4 Bytes
                    flush_command.read(f)

                    # Skip past 4 unknown ints
                    f.seek(4 * 4, 1)

                    # End LOD Glue

                    # LOD
                    unpack_command = VIFCommand()
                    # 4 Bytes
                    unpack_command.read(f)

                    mesh_set_count = unpack('i', f)[0]
                    mesh_data_count = unpack('i', f)[0]

                    # Skip past two zeros
                    f.seek(4 * 2, 1)

                    # End LOD

                    running_mesh_set_count = 0

                    size_start = f.tell()

                    # For Each MeshSet

                    # FIXME: This should be correct but it seems to be missing some sets.
                    # Oddly secure to just check for the unknown flag being 128. :thinking:
                    #while running_mesh_set_count < mesh_set_count:
                    while True:
                        #print("Mesh Set %d" % mesh_set_index)
                        #print("Running Count / Total : %d/%d" % (running_mesh_set_count, mesh_set_count) )
                        data_count = int.from_bytes(unpack('c', f)[0], 'little')

                        # Commonly 0, but occasionally 128. Rarely another value...
                        unknown_flag = int.from_bytes(unpack('c', f)[0], 'little')

                        #print("Data Count / Unknown Flag %d/%d" % (data_count, unknown_flag) )


                        # Skip past the unknown short
                        f.seek(2, 1)
                        # Skip past 3 unknown floats (they're sometimes not int :thinking:)
                        #print("Three Unknown Ints [%d/%d/%d]" % (unpack('I', f)[0],unpack('I', f)[0],unpack('I', f)[0]))
                        #f.seek(4 * 3, 1)
                        unknown_val_1 = unpack('I', f)[0]
                        face_winding_order = unpack('I', f)[0]
                        unknown_val_2 = unpack('I', f)[0]



                        # Mesh Set
                        triangle_counter = 0
                        for i in range(data_count):
                            #print("Data i/count", i, data_count)

                            # TODO: Determine why there's sometimes just an empty line 
                            # For now we must look for the vertex_padding. It seems to ALWAYS be 1.0f
                            
                            # Skip past three zeros + one unknown large uint                        
                            f.seek(4 * 3, 1)

                            constant_one = unpack('f', f)[0]

                            # If we have our constant, then we need to rewind back to the start
                            if constant_one == 1.0:
                                f.seek(-(4 * 4), 1)
                            # else, we're already here!

                            vertex = Vertex()
                            
                            # There's no lods, so no need to keep track of this
                            vertex.sublod_vertex_index = 0xCDCD

                            vertex_data = self._read_vector(f)
                            vertex_padding = unpack('f', f)[0]
                            normal_data = self._read_vector(f)
                            normal_padding = unpack('f', f)[0]

                            uv_data = Vector()
                            uv_data.x = unpack('f', f)[0]
                            uv_data.y = unpack('f', f)[0]

                            vertex_index = unpack('f', f)[0]
                            unknown_padding = unpack('f', f)[0]

                            # Create our FaceVert
                            face_vertex = FaceVertex()
                            face_vertex.texcoord = uv_data
                            face_vertex.vertex_index = mesh_index

                            # 0x412 and 0x8412
                            # Here we check to see if it's 0x8412, 
                            # and if it is our FaceBuilder2000 will reverse the winding order when building the face
                            face_vertex.reversed = face_winding_order == WO_REVERSED

                            vertex.location = vertex_data
                            vertex.normal = normal_data

                            # Local set list
                            vertex_list.append(vertex, mesh_set_index, face_vertex, False)

                            mesh_index += 1
                        # End For `i in range(data_count)`

                        mesh_set_index += 1
                        running_mesh_set_count += 1

                        # This is a total hack, but it works..
                        if unknown_flag == 128:
                            print("Breaking from loop!")
                            break


                    # End While `running_mesh_data_count < mesh_data_count`

                    #####################################################################
                    # HACK: Sometimes there's a 4*4 bytes row before the end command
                    # So let's look for our end command, and if it's not found skip 4*4!
                    end_command_peek = [ unpack('i', f)[0], unpack('i', f)[0], unpack('i', f)[0], unpack('i', f)[0] ]

                    # Well if it is our end command, then go back into the past so we can properly grab it
                    # otherwise we just skipped the junk!
                    if end_command_peek[0] == 0 and end_command_peek[1] == 0 and end_command_peek[2] == 0 and end_command_peek[3] == VIF_MSCALF:
                        print("Found End Command!")
                        f.seek(-(4*4), 1)
                    else:
                        print("Skipped junk at the end!")

                    #####################################################################

                    # 0x15 = call micro program
                    # This probably yells at the GS to read the last VIF packet
                    end_command = EndCommand()
                    # 4 Bytes
                    end_command.read(f)

                    print("End Command ", end_command.__dict__)

                    size_end = f.tell()

                    # MeshSet size in bytes
                    size = size_end - size_start
                    print("size (%d) = size_end (%d) - size_start (%d)" % (size, size_end, size_start))

                    # If we're bigger than 13kb then check for additional data
                    # 13kb seems to be about the limit per meshset batch. 
                    if size > 13000:
                        print("Batch was over 13kb, checking for more data, size: %d" % size)
                        check_for_more_data = True
                    else:
                        print("No more data expected in this batch, size: %d" % size)
                        finished_lods = True
                        break
                # End While `finished_lods == False`

                # Fill up the LOD
                lod.vertices += vertex_list.get_vertex_list()
                vertex_list.generate_faces()
                lod.faces += vertex_list.get_face_list()


                if mesh_type is MT_SKELETAL:


                    unk_sector_start = f.tell()
                    unk_sector_finished = False
                    while True:
                        unk_amount_to_skip = unpack('H', f)[0]

                        # This section stores a count and then various values (all in shorts)
                        # So skip the count * 2 (length of a short in this case)
                        f.seek(+(unk_amount_to_skip * 2), 1)

                        # The current count in short.
                        current_total = (f.tell() - unk_sector_start) / 2
                        # Oh we're done?..nope. We need to skip some padding first!
                        if current_total >= lod_skeletal_unk_sector_count:
                            #print("(%d/%d) Finished!" % (current_total, lod_skeletal_unk_sector_count))
                            # Okay, loop through and look for 1.0f 3*4 bytes away!
                            while True:
                                test_values = unpack('4f', f)
                                #print("Testing 4th value %f at %d" % (test_values[3], f.tell()))

                                if test_values[3] == 1.0:
                                    unk_sector_finished = True
                                    # Go back 4*4 bytes
                                    f.seek(-4*4, 1)
                                    break
                            
                                # Go back 14 bytes (We want to crawl up 2 bytes at a time)
                                f.seek(-14, 1)
                        
                        if unk_sector_finished:
                            break
                                    

                    #
                    # Here we want to build a list of ordered vertices. 
                    # After that will come the ordered weights
                    # We can then do a double loop
                    # that we can add the weights to the already processed verts
                    #
                    ordered_vertices = []

                    class OrderedVertex(object):
                        def __ini__(self):
                                self.location = Vector()
                                self.location_padding = 0
                                self.normal = Vector()
                                self.normal_padding = 1

                    print("Before Ordered Vertex %d, vertex count: %d" % (f.tell(), lod_vertex_count))

                    for vi in range(lod_vertex_count):
                        ov = OrderedVertex()
                        ov.location = self._read_vector(f)
                        ov.location_padding = unpack('f', f)[0]
                        ov.normal = self._read_vector(f)
                        ov.normal_padding = unpack('f', f)[0]
                        ordered_vertices.append(ov)
                    # End for `vi in range(lod_vertex_count)`

                    # Ok we need to go through and figure out which bones map to which index
                    node_map = []

                    print("Currently at %d" % f.tell())

                    # Go through and capture every int
                    # These are the node indexes
                    for wni in range(lod_weighted_nodes_count):
                        node_map.append(unpack('i', f)[0])

                    print("Node map: ", node_map)
                    
                    for wi in range(lod_vertex_count):
                        weights = unpack('4h', f)
                        node_indexes = unpack('4b', f)

                        #print("WEIGHTS     :",wi, weights)
                        #print("NODE INDEXES: ",wi, node_indexes)
                        
                        normalized_weights = []

                        # Normlize our weights from 0..4096 to 0..1
                        for weight in weights:
                            if weight == 0:
                                continue

                            normalized_weights.append( float(weight) / 4096.0 )
                            #print (normalized_weights)

                        processed_weights = []

                        for j in range( len(normalized_weights) ):
                            weight = Weight()
                            # Set the normalized weight bias
                            weight.bias = normalized_weights[j]
                            weight.node_index = node_indexes[j]

                            if weight.node_index != 0:
                                weight.node_index /= 4
                                weight.node_index = int(weight.node_index)

                            # Find the proper node!
                            weight.node_index = node_map[weight.node_index]
                            
                            processed_weights.append(weight)

                        ordered_vertex = ordered_vertices[wi]

                        for vi in range( len(lod.vertices) ):
                            vertex = lod.vertices[vi]

                            if ordered_vertex.location == vertex.location:
                                lod.vertices[vi].weights = copy.copy(processed_weights)

                                for i in range(len(lod.vertices[vi].weights)):
                                    lod.vertices[vi].weights[i].location = (ordered_vertex.location @ Matrix())

                                #print("Setting vertex weights ! ", lod.vertices[vi].weights[0].__dict__, processed_weights[0].__dict__)
                                break
                        # End for `vi in range( len(lod.vertices) )`
                    # End for `wi in range(lod_vertex_count)`
                # End for Skeletal Mesh

                # Add the LOD to the piece
                piece_object.lods = [lod]

                # Add the piece to the model!
                model.pieces.append(piece_object) 
            # End For `piece_index in range( piece_count )`

            print("Final verticies ", len(lod.vertices))
            print("Final faces ", len(lod.faces))

            # Handle Nodes!
            f.seek(node_offset)

            model.nodes = [self._read_node(f) for _ in range(self._node_count)]
            build_undirected_tree(model.nodes)

            # Handle Animations!
            f.seek(animation_offset)
            local_animation_count = unpack('I', f)[0]
            model.animations = [self._read_animation(f) for _ in range(local_animation_count)]

            # Handle Sockets!
            f.seek(socket_offset)
            model.sockets = [self._read_socket(f) for _ in range(socket_count)]

        return model
