import struct
from mathutils import Vector, Quaternion, Matrix

'''
REFERENCE LIST:
    http://www.fallout.bplaced.net/dedit/tutorials/dedit_docs_nolf/ModelEdit.htm
    https://web.archive.org/web/20080605043638/http://bop-mod.com:80/download/docs/ABC-Format-v6.html

TODO LIST:
    * Figure out what the [-1, 0, 18] flag is at the end of animation bounds. 
    * Add the ability to optionally merge import meshes
    * Add the ability to import textures automatically
'''


'''
This is a depth-first iterator. The weird `idx` array is used because
integers cannot be pass-by-reference.
'''
def node_iterator(nodes, nit=None, parent=None):
    if nit is None:
        nit = iter(nodes)
    node = next(nit)
    yield (node, parent)
    for i in range(node.child_count):
        yield from node_iterator(nodes, nit, node)


def build_undirected_tree(nodes):
    for (node, parent) in node_iterator(nodes):
        node.parent = parent
        node.children = []
        if parent is not None:
            parent.children.append(node)


'''
DATA BLOCKS
'''
class Weight(object):
    def __init__(self):
        self.node_index = 0
        self.location = Vector()
        self.bias = 0.0


class Vertex(object):
    def __init__(self):
        self.sublod_vertex_index = 0xCDCD
        self.weights = []
        self.location = Vector()
        self.normal = Vector()

        # LTB specific
        self.colour = 0


class FaceVertex(object):
    def __init__(self):
        self.texcoord = Vector()
        self.vertex_index = 0
        self.reversed = False

        # LTB specific

        # Supports up to 4 UVs, so let's add some more!
        self.extra_texcoords = [Vector(), Vector(), Vector()]


class Face(object):
    def __init__(self):
        self.vertices = []


class LOD(object):
    def __init__(self):
        self.faces = []
        self.vertices = []

        # LTB specific
        self.texture_count = 0
        self.render_style = 0
        self.render_priority = 0
        self.textures = [] # Order?
        self.type = 7 # Null

        self.max_bones_per_face = 0
        self.max_bones_per_vert = 0
        self.vert_count = 0
        self.face_count = 0

        # Basis Vector???
        self.s = Vector()
        self.t = Vector()

        # Model00p specific
        self.distance = 0.0
        self.texture_index = 0
        self.translucent = 0
        self.cast_shadow = 0
        self.piece_count = 0
        self.piece_index_list = []

    def get_face_vertices(self, face_index):
        return [self.vertices[vertex.vertex_index] for vertex in self.faces[face_index].vertices]


class Piece(object):
    
    @property
    def weight_count(self):
        return sum([len(vertex.weights) for lod in self.lods for vertex in lod.vertices])
    
    def __init__(self):
        self.material_index = 0
        self.specular_power = 0.0
        self.specular_scale = 0.0
        self.lod_weight = 1.0
        self.name = ''
        self.lods = []

        # LTB specific
        self.lod_min = 0.0
        self.lod_max = 0.0
        self.lod_distances = []
    
class Node(object):
    
    @property
    def is_removable(self):
        return (self.flags & 1) != 0
    
    @is_removable.setter
    def is_removable(self, b):
        self.flags = (self.flags & ~1) | (1 if b else 0)

    @property
    def uses_relative_location(self):
        return (self.flags & 2) != 0
    
    def __init__(self):
        self.name = ''
        self.index = 0
        self.flags = 0
        self.bind_matrix = Matrix()
        self.child_count = 0

        # Version 6 specific
        self.md_vert_count = 0
        self.md_vert_list = []

        # Model00p specific
        self.location = Vector()
        self.rotation = Quaternion((1, 0, 0, 0))
    
    def __repr__(self):
        return self.name


class WeightSet(object):
    def __init__(self):
        self.name = ''
        self.node_weights = []


class Socket(object):
    def __init__(self):
        self.node_index = 0
        self.name = ''
        self.rotation = Quaternion()
        self.location = Vector()

        # LTB specific
        self.scale = Vector()


class Animation(object):
    class Keyframe(object):

        # We only care about location for Vertex transforms
        class VertexTransform(object):
            def __init__(self):
                self.location = Vector()
        # End Class

        class Transform(object):
            def __init__(self):
                self.location = Vector()
                self.rotation = Quaternion((1, 0, 0, 0))
            
            @property
            def matrix(self):
                return Matrix.Translation(self.location) * self.rotation.to_matrix().to_4x4()
            
            @matrix.setter
            def matrix(self, m):
                self.location, self.rotation, _ = m.decompose()
        
        def __init__(self):
            self.time = 0
            self.string = ''

    def __init__(self):
        self.extents = Vector()
        self.name = ''
        self.unknown1 = -1
        self.interpolation_time = 200
        self.keyframes = []
        self.keyframe_count = 0
        self.node_keyframe_transforms = []

        # Version 6 specific

        # Note this should line up with md_vert_list, and go on for md_vert_count * keyframe_count
        # List of 3 chars (verts)
        self.vertex_deformations = []
        # List of Vector (verts)
        # Scaled by the animation bounding box
        self.transformed_vertex_deformations = []

        # LTB specific
        self.compression_type = 0
        self.is_vetex_animation = 0


class AnimBinding(object):
    def __init__(self):
        self.name = ''
        self.extents = Vector()
        self.origin = Vector()

        # Model00p specific
        self.radius = 1.0
        self.rotation = Vector() # Eulers?
        self.interpolation_time = 200

        self.animation_header_index = -1
        self.data_position = -1
        self.is_compressed = -1 # Location compression only! Rotation data is always compressed.
        
class AnimInfo(object):
    def __init__(self):
        self.animation = Animation()
        self.binding = AnimBinding()

class ChildModel(object):
    def __init__(self):
        self.name = ''
        self.build_number = 0
        self.transforms = []
#
# Model00p+ specific
#
class PhysicsShape(object):
    def __init__(self):
        self.index = 0
        self.offset = Vector()
        self.orientation = Quaternion()
        self.cor = 0.0
        self.friction = 0.0
        self.collision_group = 0
        self.node_index = 0
        self.mass = 0.0
        self.density = 0.0 # Scaled
        self.radius = 0.0

        # Capsule specific
        # If Orientation.w != 0.0
        self.unk_1 = 0
        self.length_pt1 = 0.0
        self.unk_2 = 0
        self.unk_3 = 0
        self.length_pt2 = 0.0
        self.unk_4 = 0
        # End If

class PhysicsConstraint(object):
    TYPE_LIMITED_HINGE = 3
    TYPE_RAGDOLL = 4

    def __init__(self):
        self.type = 0
        self.shape_index = 0
        self.unk_1 = 0
        self.data = [] # Length: Type 3 == 18, Type 4 == 24
        self.friction = 0.0
        # If Type == 3
        self.unk_2 = 0.0
        self.unk_3 = 0.0
        # End If

class PhysicsNodeWeights(object):
    def __init__(self):
        self.physics = 0
        self.velocity_gain = 1.0
        self.hiearchy_gain = 0.0

class PhysicsWeightSet(object):
    def __init__(self):
        self.name = ""
        self.node_weights = [] #...PhysicsNodeWeights


class Physics(object):
    def __init__(self):
        self.vis_node_index = 0
        self.vis_radius = 0.0
        
        # Physics Shapes
        self.shape_count = 0
        self.shapes = [] #...PhysicsShape

        self.constraint_count = 0
        self.contraints = [] #...PhysicsConstraint

        self.weight_set_count = 0
        self.weight_sets = [] # ...PhysicsWeightSet

class Model(object):
    def __init__(self):
        self.version = 0
        self.name = ''
        self.pieces = []
        self.nodes = []
        self.child_models = []
        self.animations = []
        self.sockets = []
        self.command_string = ''
        self.internal_radius = 0.0
        self.lod_distances = []
        self.weight_sets = []
        self.anim_bindings = []
        
        # ABC v6 specific

        # By default it's true, this is only used when self.version == 6!

        # Flip geomtry
        self.flip_geom = True

        # Flip animation keyframes
        self.flip_anim = True

        # LTB specific

        # Model00p specific
        self.physics = Physics()

        
    @property
    def keyframe_count(self):
        return sum([len(animation.keyframes) for animation in self.animations])

    @property
    def face_count(self): #TODO: this is actually probably per LOD as well
        return sum([len(lod.faces) for piece in self.pieces for lod in piece.lods])
    
    @property
    def vertex_count(self):
        return sum([len(lod.vertices) for piece in self.pieces for lod in piece.lods])

    @property
    def weight_count(self):
        return sum([len(vertex.weights) for piece in self.pieces for lod in piece.lods for vertex in lod.vertices])
    
    @property
    def lod_count(self):
        return len(self.pieces[0].lods)
