import struct
import itertools
from mathutils import Vector, Quaternion, Matrix
from .utils import LTAVersion

#
# LithTech Ascii Format
# ---------------------
# Basically this a pretty simple human readable model format. 
# Note: Names, attributes, and properties are not unique!
# --
# Each node is contained within braces `(` and `)`, the number of open braces determines depth.
# --
# Some nodes have attributes, these are on the same level as their name. 
# An example/ ( name "base" ), the node name is "name" and the attribute is "base".
# --
# Some nodes have properties, these are basically unnamed nodes with just attributes.
# An example/ ( dims (24.000000 53.000000 24.000000) ). "Dims" is the node, and "(24.000000 53.000000 24.000000 )" is a property. 
# There can be more than one property per node, they act like children, but should not have any additional children themselves.
# --
# And finally, nodes can have child nodes. 
# An example/ (lt-model-0 (on-load-cmds ( ... ) ). "lt-model-0" is our depth=0 node, and "on-load-cmds" is our depth=1 node, and a child node of "lt-model-0". 
#
class LTANode(object):

    def __init__(self, name='unnamed-node', attribute=None):
        self._name = name
        self._attribute = attribute
        self._depth = 0
        self._children = []

    # Originally its own node type, but it's basically a nameless child..so eh.
    def create_property(self, value=''):
        return self.create_child('', value)

    # Container is just an empty set of braces
    def create_container(self):
        return self.create_child('', None)

    def create_child(self, name, attribute=None):
        node = LTANode(name, attribute)

        # Increase the depth by one
        node._depth = self._depth + 1

        # Add it to this node's children list
        self._children.append(node)

        return node

    # Loop through all the children and write out their props and depth
    def serialize(self):
        output_string = ""

        # Add our current depth in tabs
        output_string += self._write_depth()

        output_string += "(%s " % self._name

        if self._attribute is not None:
            output_string += self._resolve_type(self._attribute)

        # If we have no children, let's early out
        if len(self._children) == 0:
            output_string += ")\n"
            return output_string

        # Ok add a new line for our children!
        output_string += "\n"

        for child in self._children:
            output_string += child.serialize()

        # Once again...add our current depth in tabs
        output_string += self._write_depth()

        output_string += ")\n"

        return output_string

    def _write_depth(self):
        output_string = ""
        for _ in range(self._depth):
            output_string += "\t"
        return output_string

    # Some handy private functions
    def _resolve_type(self, value):
        
        # Handle special cases if required
        if type(value) is str:
            return self._serialize_string(value)

        if type(value) is float:
            return self._serialize_float(value)

        if type(value) is Vector:
            return self._serialize_vector(value)

        if type(value) is Quaternion:
            return self._serialize_quat(value)

        if type(value) is Matrix:
            return self._serialize_matrix(value)

        if type(value) is list:
            return self._serialize_list(value)
        
        return str(value)

    def _serialize_string(self, value):
        return "\"%s\"" % value

    def _serialize_float(self, value):
        return "%.6f" % value

    def _serialize_vector(self, value):
        return "%.6f %.6f %.6f" % (value.x, value.y, value.z)

    def _serialize_quat(self, value):
        return "%.6f %.6f %.6f %.6f" % (value.x, value.y, value.z, value.w)

    def _serialize_matrix(self, value):
        output_string = ""

        for row in value:
            output_string += "\n"
            output_string += self._write_depth()
            output_string += "("
            for column in row:
                output_string += " "
                output_string += self._serialize_float(column)
            # End For
            output_string += " )"
        # End For

        output_string += "\n"
        output_string += self._write_depth()

        return output_string


    def _serialize_list(self, value):
        output_string = ""

        for i, item in enumerate(value):
            output_string += self._resolve_type(item)

            # If we're not the last item, add a space
            if i != len(value) - 1:
                output_string += " "
        # End For

        return output_string
# End Class

# Nodes are nested for as many children they have
# so it's easier to handle this in its own class.
class NodeWriter(object):
    def __init__(self):
        self._index = 0

    # Simply create a "children" node.
    def create_children_node(self, root_node):
        children_node = root_node.create_child('children')
        return children_node.create_container()

    def write_node_recursively(self, root_node, model):
        model_node = model.nodes[self._index]

        transform_node = root_node.create_child('transform', model_node.name)
        transform_node.create_child('matrix').create_property(model_node.bind_matrix)

        if model_node.child_count == 0:
            return
        # End If

        children_container_node = self.create_children_node(transform_node)

        for _ in range(model_node.child_count):
            self._index += 1
            self.write_node_recursively(children_container_node, model)
        # End For
# End Class

class LTAModelWriter(object):

    def __init__(self):
        self._version = 'not-set'

    def write(self, model, path, version):
        # Set the version
        self._version = version

        # This is the main node! Everything is a child of this duder.
        root_node = LTANode('lt-model-0')

        ##########################################################
        # META DATA
        ##########################################################
        on_load_cmds_node = root_node.create_child('on-load-cmds')

        ''' AnimBindings '''
        ab_list_node = on_load_cmds_node.create_child('anim-bindings')
        ab_container_node = ab_list_node.create_container()
        for i, anim_binding in enumerate(model.anim_bindings):
            anim_dims = anim_binding.extents

            # Earlier versions of Model Edit act weird if anim_dims is (0,0,0)
            if (anim_dims.magnitude == 0.0):
                anim_dims = Vector( (10.0, 10.0, 10.0) )

            ab_node = ab_container_node.create_child('anim-binding')
            ab_node.create_child('name', anim_binding.name)
            ab_node.create_child('dims').create_property(anim_dims)
            ab_node.create_child('translation').create_property(anim_binding.origin)
            # Gotta look for this one!
            ab_node.create_child('interp-time', model.animations[i].interpolation_time)

        ''' Node Flags '''
        snf_list_node = on_load_cmds_node.create_child('set-node-flags')
        snf_container = snf_list_node.create_container()
        for node in model.nodes:
            snf_container.create_property( [node.name, node.flags] )

        ''' Skeleton Deformers (Vertex Weights!) '''
        for piece in model.pieces:
            ad_node = on_load_cmds_node.create_child('add-deformer')
            sd_node = ad_node.create_child('skel-deformer')
            
            sd_node.create_child('target', piece.name)
            
            influences_node = sd_node.create_child('influences')

            weightsets_node = sd_node.create_child('weightsets')
            weightsets_container = weightsets_node.create_container()

            # This is a unique list of bone names used in this piece
            bone_influences = []

            # Ok...it's actually just a list of all bones in the majority of examples I've seen..
            for node in model.nodes:
                bone_influences.append(node.name)

            for lod in piece.lods:
                for vertex in lod.vertices:

                    weights = []

                    for weight in vertex.weights:
                        node_name = model.nodes[weight.node_index].name

                        new_node_index = bone_influences.index(node_name)

                        weights.append(new_node_index)
                        weights.append(weight.bias)

                    weightsets_container.create_property( weights )

            influences_node.create_property( bone_influences )
        # End For

        ''' Command String '''
        if model.command_string is None:
            model.command_string = ""

        on_load_cmds_node.create_child('set-command-string', model.command_string)

        ''' LODS '''
        # TODO

        ''' Radius '''
        on_load_cmds_node.create_child('set-global-radius', model.internal_radius)

        ''' Sockets '''
        if len(model.sockets) > 0:
            ad_node = on_load_cmds_node.create_child('add-sockets')
            for socket in model.sockets:
                parent_node_name = model.nodes[socket.node_index].name

                socket_node = ad_node.create_child('socket', socket.name)
                socket_node.create_child('parent', parent_node_name)
                socket_node.create_child('pos').create_property(socket.location)
                socket_node.create_child('quat').create_property(socket.rotation)
            # End For
        # End If

        ''' Child Models'''
        # Child models always includes a reference to the model itself
        # So we need to ignore that...
        if len(model.child_models) > 1:
            cm_node = on_load_cmds_node.create_child('add-childmodels')

            cm_container = cm_node

            # Jupiter requires child models to be in a wrapper
            if self._version == LTAVersion.JUPITER.value:
                cm_container = cm_node.create_container()

            for i, child_model in enumerate(model.child_models):
                if i == 0:
                    continue

                child_model_node = cm_container.create_child('child-model')
                child_model_node.create_child('filename', child_model.name)
                child_model_node.create_child('save-index', child_model.build_number)
            # End For
        # End If

        ''' Animation Weightsets '''
        if len(model.weight_sets) > 0:
            aws_node = on_load_cmds_node.create_child('anim-weightsets')
            weightsets_container = aws_node.create_container()
            for weight_set in model.weight_sets:
                weightset_node = weightsets_container.create_child('anim-weightset')
                weightset_node.create_child('name', weight_set.name)
                weightset_node.create_child('weights').create_property(weight_set.node_weights)
            # End For
        # End If

        ##########################################################
        # NODES
        ##########################################################

        h_node = root_node.create_child('hierarchy')

        # Let NodeWriter handle it!
        node_writer = NodeWriter()
        node_writer.write_node_recursively(node_writer.create_children_node(h_node), model)

        ##########################################################
        # GEOMETRY
        ##########################################################

        for piece in model.pieces:
            p_node = root_node.create_child('shape', piece.name)
            geometry_node = p_node.create_child('geometry')
            mesh_node = geometry_node.create_child('mesh', piece.name)

            vertex_node = mesh_node.create_child('vertex')
            vertex_container = vertex_node.create_container()

            normal_node = mesh_node.create_child('normals')
            # It's your everyday...
            normal_container = normal_node.create_container()

            uv_node = mesh_node.create_child('uvs')
            uv_container = uv_node.create_container()

            tex_fs_node = mesh_node.create_child('tex-fs')
            tri_fs_node = mesh_node.create_child('tri-fs')

            # For both tex and tri fs. Because I don't know why they'd be different..
            face_index_list = []
            uv_index_list = []

            for lod in piece.lods:
                for face in lod.faces:
                    for face_vertex in face.vertices:
                        texcoords = [ face_vertex.texcoord.x, face_vertex.texcoord.y ]
                        uv_container.create_property( texcoords )

                        face_index_list.append( face_vertex.vertex_index )
                    # End For    
                # End For

                for vertex in lod.vertices:
                    vertex_container.create_property( vertex.location )
                    normal_container.create_property( vertex.normal )
                # End For
            # End For


            # Okay this doesn't seem like the best way to do it, but it works..
            # We need a list filled with 0..Length of Face Index List.
            # I tried to squish this under face_index_list.append but it doesn't seem to like that.
            for i in range( len(face_index_list) ):
                uv_index_list.append(i)
            # End For

            # Okay now add the prop list
            tri_fs_node.create_property( face_index_list )
            tex_fs_node.create_property( uv_index_list )

            # Okay let's deal with Lithtech 2.2/Talon appearence node
            # Note: Talon's ModelEdit has a bug where it reads the data, and then discards it...
            appearance_node = p_node.create_child('appearance')

            pc_material_node = appearance_node.create_child('pc-mat')

            pc_material_node.create_child('specular-power', piece.specular_power)
            pc_material_node.create_child('specular-scale', piece.specular_scale)
            pc_material_node.create_child('texture-index', piece.material_index)

            # End If
        # End For

        ##########################################################
        # ANIMATIONS
        ##########################################################
        
        for animation in model.animations:
            as_node = root_node.create_child('animset', animation.name)


            # Nested keyframe nodes..I didn't build this spec, but I can sure give it a look.
            keyframe_node = as_node.create_child('keyframe')
            keyframe2_node = keyframe_node.create_child('keyframe')

            times_node = keyframe2_node.create_child('times')
            values_node = keyframe2_node.create_child('values')

            # Keyframe timing
            times_list = []
            # Keyframe strings
            values_list = []

            for keyframe in animation.keyframes:
                times_list.append( keyframe.time )

                if keyframe.string is None:
                    keyframe.string = ""

                values_list.append( keyframe.string )
            # End For

            # Append the properties!
            times_node.create_property( times_list )
            values_node.create_property( values_list ) 

            ###

            anims_node = as_node.create_child('anims')
            anims_container_node = anims_node.create_container()

            for i, node_keyframe_transform_list in enumerate(animation.node_keyframe_transforms):
                anim_node = anims_container_node.create_child('anim')
                anim_node.create_child('parent', model.nodes[i].name)

                frames_node = anim_node.create_child('frames')

                # Position / Quaternion
                posquat_node = frames_node.create_child('posquat')
                posquat_container = posquat_node.create_container()

                # Unlike every other property, each transform is it's own prop
                for keyframe_transform in node_keyframe_transform_list:

                    # Each transform seems to have its own empty wrapper
                    keyframe_container = posquat_container.create_container()

                    keyframe_container.create_property( keyframe_transform.location )
                    keyframe_container.create_property( keyframe_transform.rotation )
                # End For
            # End For
        # End For


        ##########################################################
        # WRITE TO FILE
        ##########################################################
        
        with open(path, 'w') as f:
            print("Serializing node list...")
            s_root_node = root_node.serialize()
            f.write(s_root_node)
            print("Finished serializing node list!")
        # End With
    # End Def
# End Class