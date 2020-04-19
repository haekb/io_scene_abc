import os
from .abc import *
from .io import unpack
from mathutils import Vector, Matrix, Quaternion
from functools import cmp_to_key
import math
import copy

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

# PS2 VIF Command, not entirely sure on all the codes but here's a few..
# VIFCodes: https://gtamods.com/wiki/PS2_Native_Geometry
#
# 0x11 = Flush - wait for end of microprogram and GIF transfer
# 0x15 = MSCALF - call micro program
# 0x6C = Unpack? - unpack the following data and write to VU memory
#
class VIFCommand(object):
    def __init__(self):
        self.constant = 0
        self.variable = 0
        self.code = 0

    def read(self, f):
        self.constant = unpack('h', f)[0]
        self.variable = unpack('B', f)[0]
        self.code = unpack('B', f)[0]

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
    
    def append(self, vertex, group_id, face_vertex):
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


        

    def generate_faces(self):
        # Loop through every face vert
        # Then loop through every group
        # Or maybe opposite...
        # 
        #
        faces = []

        print("------------------------------------")
        print("Generating Faces :) ")
        print("Groups: ",self.groups)


        
        #for group_id in self.groups:
        flip = False
        for j in range( len(self.groups) ):
            group_id = self.groups[j]
            #print("Group ID: ", group_id)

            # TEST
            #if group_id != 3:
                #continue

            grouped_faces = []


            for i in range( len(self.face_verts) ):
                
                face_vert = self.face_verts[i]

                if face_vert.group_id != group_id:
                    continue

                grouped_faces.append(face_vert)
            # End Face Verts
            
            #print("Grouped Faces: ", grouped_faces)

            for i in range( len(grouped_faces) ):
                if i < 2:
                    continue

                face = Face()
                #print("Flipped? ",flip)

                if flip:
                    face.vertices = [ grouped_faces[i - 1].face_vertex, grouped_faces[i - 2].face_vertex, grouped_faces[i].face_vertex ]
                else:
                    face.vertices = [ grouped_faces[i - 2].face_vertex, grouped_faces[i - 1].face_vertex, grouped_faces[i].face_vertex ]

                faces.append(face)
                flip = not flip
            # End Grouped Faces
        # End Groups

                
        # End For

        self.faces = faces
    # End of Generate Faces

    def find_in_list(self, merge_string):

        #print("Is %s in our list? " % merge_string)
        for i in range( len(self.list) ):
            if merge_string == self.list[i].merge_string:
                #print("Yes!")
                return i

        #print("No!")
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

                        # # Okay if we're a triangle, then save the current face and pop the first face vert off.
                        # if len( face.vertices ) == 3:

                        #     # print("Appending Face", face.__dict__)
                        #     # Save our current face!

                        #     # FIXME: Uncomment when face merging is done
                        #     lod.faces.append(face)

                        #     # We need to deep copy to prevent modifying the face already in the list
                        #     # This took me hours to figure out ugh.
                        #     face = copy.deepcopy(face)
                        #     face.vertices.pop(0)
                        #     # End If
# End Class

class PS2LTBModelReader(object):
    def __init__(self):
        self._file_type = 0
        self._version = 0
        self._node_count = 0
        self._lod_count = 0

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
            if self._file_type is not 2:
                raise Exception('LTB Importer only supports PS2 LTB files.')
                
            if self._version is not 16:
                raise Exception('LTB Importer only supports version 16.')

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
            node_count = unpack('i', f)[0]
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
            f.seek(4 * 3, 1)
            # End Piece Header

            # We can have multiple pieces!
            for piece_index in range( piece_count ):
                print("------------------------------------")
                print("Dawn of a new piece!")

                # Used when loading the actual mesh data
                # If the previous chunk was 13kb+, 
                # then we need to peek and see if there's more data instead of the next piece
                check_for_more_data = False

                #########################################################################
                # HACK: Skip past any bone information, we're going to be looking for 0.8, 0.8, 0.8!
                # Skip past the unknown value
                f.seek(4, 1)

                exit_piece_early = False

                print ("Looking for hero eights...")
                while True:
                    try:
                        hero_eights = [ unpack('f', f)[0], unpack('f', f)[0], unpack('f', f)[0] ]
                        #print("Value: ", hero_eights)
                        #print("Close to 0.8? " , math.isclose(hero_eights[0], 0.8, rel_tol=1e-04))
                        if math.isclose(hero_eights[0], 0.8, rel_tol=1e-04) and math.isclose(hero_eights[1], 0.8, rel_tol=1e-04) and math.isclose(hero_eights[2], 0.8, rel_tol=1e-04):
                            print("Found 0.8,0.8,0.8")
                            break

                        # We only want to move up one!
                        f.seek(-4*2, 1)
                    except struct.error as err:
                        exit_piece_early = True
                        print("Could not find hero eights, reached end of file.")
                        break
                        
                if exit_piece_early == True:
                    break

                # Revert back to our original position
                f.seek(-(4*5), 1) 
                # End Hack !
                #########################################################################

                # Piece
                f.seek(4 * 18, 1)
                mesh_type = unpack('i', f)[0]
                # End Piece

                if mesh_type is 4:
                    print("Rigid Mesh")
                elif mesh_type is 5:
                    print("Skeletal Mesh")
                elif mesh_type is 6: # Haven't tested or found a VA mesh!
                    print("Vertex Animated Mesh")

                # LODs
                finished_lods = False
    
                lod = LOD()
                vertex_list = VertexList()
                mesh_set_index = 1 # this gets multiplied
                mesh_index = 0 # triangle_count + vertex_count

                # There's two additional ints with skeletal meshes 
                if mesh_type is 5:
                    f.seek( 4 * 2, 1)

                lod_vertex_count = unpack('i', f)[0]
                lod_unknown = unpack('i', f)[0]

                # Haven't mapped out pieces yet...
                piece_object = Piece()
                piece_object.name = "Piece %d" % piece_index

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
                        if (vif_cmd.constant is not 0x50 or vif_cmd.code is not 0x6C):
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

                    running_mesh_data_count = 0

                    size_start = f.tell()

                    # For Each MeshSet
                    while running_mesh_data_count < mesh_data_count:
                        print("Running Count / Total : %d/%d" % (running_mesh_data_count, mesh_data_count) )
                        data_count = int.from_bytes(unpack('c', f)[0], 'little')

                        # Commonly 0, but occasionally 128. Rarely another value...
                        unknown_flag = int.from_bytes(unpack('c', f)[0], 'little')

                        # Skip past the unknown short
                        f.seek(2, 1)
                        # Skip past 3 unknown floats (they're sometimes not int :thinking:)
                        f.seek(4 * 3, 1)

                        # Mesh Set

                        for i in range(data_count):
                            print("Data i/count", i, data_count)

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
                            
                            vertex_data = self._read_vector(f)
                            vertex_padding = unpack('f', f)[0]
                            normal_data = self._read_vector(f)
                            normal_padding = unpack('f', f)[0]

                            uv_data = Vector()
                            uv_data.xy = unpack('2f', f)[0]

                            vertex_index = unpack('f', f)[0]
                            unknown_padding = unpack('f', f)[0]

                            # Create our FaceVert
                            face_vertex = FaceVertex()
                            face_vertex.texcoord = uv_data
                            face_vertex.vertex_index = mesh_index

                            vertex.location = vertex_data
                            vertex.normal = normal_data

                            # Local set list
                            vertex_list.append(vertex, mesh_set_index, face_vertex)

                            mesh_index += 1
                        # End For `i in range(data_count)`

                        running_mesh_data_count += data_count
                    # End While `running_mesh_data_count < mesh_data_count`

                    # 0x15 = call micro program
                    # This probably yells at the GS to read the last VIF packet
                    end_command = VIFCommand()
                    # 4 Bytes
                    end_command.read(f)

                    size_end = f.tell()

                    # MeshSet size in bytes
                    size = size_end - size_start

                    # If we're bigger than 13kb then check for additional data
                    # 13kb seems to be about the limit per meshset batch. 
                    if size > 13000:
                        print("Batch was over 13kb, checking for more data...")
                        check_for_more_data = True
                    else:
                        print("No more data expected in this batch")
                        finished_lods = True
                        break
                # End While `finished_lods == False`

                # Fill up the LOD
                lod.vertices += vertex_list.get_vertex_list()
                vertex_list.generate_faces()
                lod.faces += vertex_list.get_face_list()

                # Add the LOD to the piece
                piece_object.lods = [lod]

                # Add the piece to the model!
                model.pieces.append(piece_object) 

            # End For `piece_index in range( piece_count )`



            print("Final verticies ", len(lod.vertices))
            print("Final faces ", len(lod.faces))

            # section_name = self._read_string(f)
            # next_section_offset = unpack('i', f)[0]
            # if section_name == 'Header':
            #     self._version = unpack('I', f)[0]
            #     if self._version not in [9, 10, 11, 12]:
            #         raise Exception('Unsupported file version ({}).'.format(self._version))
            #     f.seek(8, 1)
            #     self._node_count = unpack('I', f)[0]
            #     f.seek(20, 1)
            #     self._lod_count = unpack('I', f)[0]
            #     f.seek(4, 1)
            #     self._weight_set_count = unpack('I', f)[0]
            #     f.seek(8, 1)
            #     model.command_string = self._read_string(f)
            #     model.internal_radius = unpack('f', f)[0]
            #     f.seek(64, 1)
            #     model.lod_distances = [unpack('f', f)[0] for _ in range(self._lod_count)]
            # elif section_name == 'Pieces':
            #     weight_count, pieces_count = unpack('2I', f)
            #     model.pieces = [self._read_piece(f) for _ in range(pieces_count)]
            # elif section_name == 'Nodes':
            #     model.nodes = [self._read_node(f) for _ in range(self._node_count)]
            #     build_undirected_tree(model.nodes)
            #     weight_set_count = unpack('I', f)[0]
            #     model.weight_sets = [self._read_weight_set(f) for _ in range(weight_set_count)]
            # elif section_name == 'ChildModels':
            #     child_model_count = unpack('H', f)[0]
            #     model.child_models = [self._read_child_model(f) for _ in range(child_model_count)]
            # elif section_name == 'Animation':
            #     animation_count = unpack('I', f)[0]
            #     model.animations = [self._read_animation(f) for _ in range(animation_count)]
            # elif section_name == 'Sockets':
            #     socket_count = unpack('I', f)[0]
            #     model.sockets = [self._read_socket(f) for _ in range(socket_count)]
            # elif section_name == 'AnimBindings':
            #     anim_binding_count = unpack('I', f)[0]
            #     model.anim_bindings = [self._read_anim_binding(f) for _ in range(anim_binding_count)]
        return model
