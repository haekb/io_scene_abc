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
            next_section_offset = 0
            #while next_section_offset != -1:
            #f.seek(next_section_offset)



            # Header
            file_type = unpack('i', f)[0]
            self._version = unpack('i', f)[0]
            
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



                # HACK: Skip past any bone information, we're going to be looking for 0.8, 0.8, 0.8!
                

                print("Start! ", f.tell())
                # Skip past the unknown value
                f.seek(4, 1)

                exit_piece_early = False

                print ("Looking for hero eights...")
                while True:
                    hero_eights = [ unpack('f', f)[0], unpack('f', f)[0], unpack('f', f)[0] ]
                    #print("Value: ", hero_eights)
                    #print("Close to 0.8? " , math.isclose(hero_eights[0], 0.8, rel_tol=1e-04))
                    if math.isclose(hero_eights[0], 0.8, rel_tol=1e-04) and math.isclose(hero_eights[1], 0.8, rel_tol=1e-04) and math.isclose(hero_eights[2], 0.8, rel_tol=1e-04):
                        print("Found 0.8,0.8,0.8")
                        break

                    # We only want to move up one!
                    f.seek(-4*2, 1)

                if exit_piece_early == True:
                    break


                # Revert back to our original position
                f.seek(-(4*5), 1) 
                # End Hack !

                # Piece
                f.seek(4 * 18, 1)
                mesh_type = unpack('i', f)[0]
                # End Piece

                print("Mesh Type:")
                print(mesh_type)

                # LODs
                finished_lods = False

                                
                # There's only one LOD per piece!
                lod = LOD()
                vertex_list = VertexList()
                while finished_lods == False:

                    

                    # Skip past 11 unknown ints
                    f.seek(4* 11, 1)
                    
                    # If we're a skeletal mesh, skip past the two unknown ints
                    if mesh_type == 5:
                        f.seek(4 * 2, 1)

                    mesh_data_count = unpack('i', f)[0]
                    
                    # Skip past two zero ints
                    # f.seek(4 * 2, 1)

                    zero_check_1 = -1
                    zero_check_2 = -1

                    zero_check_1 = unpack('i', f)[0]
                    zero_check_2 = unpack('i', f)[0]

                    if (zero_check_1 != 0 or zero_check_2 != 0):
                        print("Found the end of mesh data!")
                        finished_lods = True
                        break

                    # Okay, we're going to loop until we find the unknown flag's 128!
                    found_end_flag = False

                    # Haven't mapped out pieces yet...
                    piece_object = Piece()
                    piece_object.name = "Piece %d" % piece_index


                    mesh_set_index = 1 # this gets multiplied
                    mesh_index = 0 # triangle_count + vertex_count
                    order = [0, 1, 3, 2]

                    running_mesh_data_count = 0




                    print("------------------------------------")
                    print("Piece %d " % piece_index)

                    while found_end_flag == False:

                        #print("MESH SET START ----", mesh_set_index)

                        f.seek(4, 1)

                        mesh_set_constant = unpack('I', f)[0]

                        # I'm not sure the correct way of doing this,
                        # but 808337408 seems to be a constant value on these 'mesh sets'
                        # So check if that value is there, otherwise it could be a weird junky line.
                        if mesh_set_constant == 808337408:
                            # Re-align us back to our original position
                            f.seek(-(4*2), 1)
                        else:
                            # Skip four ints
                            f.seek(4 * 4, 1)


                        data_count = int.from_bytes(unpack('c', f)[0], 'little')

                        running_mesh_data_count += data_count

                        # I've seen it filled with other values, however 128 seems to signify that it's the last mesh set
                        unknown_flag = int.from_bytes(unpack('c', f)[0], 'little')

                        #if unknown_flag == 128:
                        #    found_end_flag = True

                        print("Mesh Data Current/Total: ",running_mesh_data_count, mesh_data_count, )

                        # We hit the total mesh data count!
                        if running_mesh_data_count >= mesh_data_count:
                            found_end_flag = True

                        # Skip past the unknown short
                        f.seek(2, 1)
                        # Skip past 3 unknown floats (they're sometimes not int :thinking:)
                        f.seek(4 * 3, 1)

                        # Mesh Set
                        face = Face()

                        faces_list = []

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
                            
                            # Save our current face vertex to our list-o-face verts
                            face.vertices.append(face_vertex)

                            faces_list.append(face_vertex)

                            vertex.location = vertex_data
                            vertex.normal = normal_data

                            # Local set list
                            vertex_list.append(vertex, mesh_set_index, face_vertex)


                            mesh_index += 1
                            # End For 

                        mesh_set_index += 1

                        #print ("MESH SET END ----")
                        # End Mesh Set

                    # Skip the 3 trailing zeros
                    #f.seek(4 * 3, 1)

                    
                    # HACK: We only care about piece 1 right now
                    #if piece_index != 1:
                    #    continue

                    #print("Appending vertices", vertex_list.get_vertex_list())


                    #for i in range( len(face_list) ):
                    #    pass
                # End Piece
                lod.vertices += vertex_list.get_vertex_list()

                vertex_list.generate_faces()

                lod.faces += vertex_list.get_face_list()

                piece_object.lods = [lod]
                model.pieces.append(piece_object)

            #for i in range( len(lod.vertices) ):
            #    print ("Test: " ,i, lod.vertices[i].__dict__)


            

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
