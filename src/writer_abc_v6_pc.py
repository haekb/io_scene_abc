import struct
import itertools
from mathutils import Vector, Matrix, Quaternion

class ABCV6ModelWriter(object):
    @staticmethod
    def _string_to_bytes(string):
        return struct.pack('H{0}s'.format(len(string)), len(string), string.encode('ascii'))

    @staticmethod
    def _vector_to_bytes(vector):
        return struct.pack('3f', vector.x, vector.y, vector.z)

    @staticmethod
    def _quaternion_to_bytes(quaternion):
        return struct.pack('4f', quaternion.x, quaternion.y, quaternion.z, quaternion.w)

    def _transform_to_bytes(self, transform):
        # TODO: this if fixed size, convert to bytes instead of bytearray
        buffer = bytearray()
        buffer.extend(self._vector_to_bytes(transform.location))
        buffer.extend(self._quaternion_to_bytes(transform.rotation))
        return bytes(buffer)

    @staticmethod
    def _get_unique_strings(model):
        strings = set()
        strings.add(model.command_string)
        strings.update([node.name for node in model.nodes])
        strings.update([child_model.name for child_model in model.child_models])
        strings.update([animation.name for animation in model.animations])
        strings.update([keyframe.string for animation in model.animations for keyframe in animation.keyframes])
        strings.discard('')
        return strings

    def __init__(self):
        self._version = 'not-set'

        # Copied from reader_abc_v6_pc.py, should probably be in an import
        # Node Flags
        self._flag_null = 1
        self._flag_tris = 2 # This node contains triangles
        self._flag_deformation = 4 # This node contains deformation (vertex animation). Used in combo with flag_tris
        # Might be Lithtech 1.5 only flags
        self._flag_env_map = 8
        self._flag_env_map_only = 16
        self._flag_scroll_tex_u = 32
        self._flag_scroll_tex_v = 64

    def write(self, model, path, version):
        class Section(object):
            def __init__(self, name, data):
                self.name = name
                self.data = data

        self._version = version

        ''' Reverse X Preprocess '''
        # TODO: reverse mesh and animations

        sections = []

        ''' Header '''
        unique_strings = self._get_unique_strings(model)

        buffer = bytearray()
        buffer.extend(self._string_to_bytes("MonolithExport Model File v6")) # version
        buffer.extend(self._string_to_bytes(model.command_string));

        sections.append(Section('Header', bytes(buffer)))

        ''' Geometry '''
        buffer = bytearray()

        buffer.extend(self._vector_to_bytes(Vector((-model.internal_radius / 2, -model.internal_radius / 2, -model.internal_radius / 2)))) # TODO: min bounds
        buffer.extend(self._vector_to_bytes(Vector((model.internal_radius / 2, model.internal_radius / 2, model.internal_radius / 2))))    # TODO: max bounds
        buffer.extend(struct.pack('Ih', 0, 0)) # TODO: lod count and lod array
        '''buffer.extend(struct.pack('I', model.lod_count))
        for lod in model.lod_count
            buffer.extend(struct.pack('H', lod))'''

        for piece in model.pieces: # TODO: error out on more than 1 piece?
            for lod in piece.lods:
                buffer.extend(struct.pack('I', model.face_count))
                for face in lod.faces:
                    buffer.extend(struct.pack('2f', face.vertices[0].texcoord.x, face.vertices[0].texcoord.y))
                    buffer.extend(struct.pack('2f', face.vertices[1].texcoord.x, face.vertices[1].texcoord.y))
                    buffer.extend(struct.pack('2f', face.vertices[2].texcoord.x, face.vertices[2].texcoord.y))
                    buffer.extend(struct.pack('3H', face.vertices[0].vertex_index, face.vertices[1].vertex_index, face.vertices[2].vertex_index))
                    normal = face.normal.normalized() * 127
                    buffer.extend(struct.pack('3b', int(normal.x), int(-normal.y), int(normal.z)))

                buffer.extend(struct.pack('I', model.vertex_count))
                buffer.extend(struct.pack('I', len(lod.vertices))) # lod[0].vert_count
                for vertex in lod.vertices:
                    buffer.extend(self._vector_to_bytes(vertex.weights[0].location))
                    normal = vertex.normal.normalized() * 127
                    buffer.extend(struct.pack('3b', int(normal.x), int(-normal.y), int(normal.z)))
                    buffer.extend(struct.pack('B', vertex.weights[0].node_index)) # TODO: error out on more than a single weight?
                    buffer.extend(struct.pack('2H', 0, 0)) # TODO: lod related, I think?

        sections.append(Section('Geometry', bytes(buffer)))

        ''' Nodes '''
        buffer = bytearray()

        for node in model.nodes:
            buffer.extend(self._vector_to_bytes(node.bounds_min))
            buffer.extend(self._vector_to_bytes(node.bounds_max))
            buffer.extend(self._string_to_bytes(node.name))
            buffer.extend(struct.pack('H', node.index))
            buffer.extend(struct.pack('B', node.flags))
            buffer.extend(struct.pack('I', node.md_vert_count))
            for md_vert in node.md_vert_list:
                buffer.extend(struct.pack('H', md_vert))
            buffer.extend(struct.pack('I', node.child_count))

        sections.append(Section('Nodes', bytes(buffer)));

        ''' Animation '''
        buffer = bytearray()

        buffer.extend(struct.pack('I', len(model.animations)))
        for anim_index, anim in enumerate(model.animations):
            buffer.extend(self._string_to_bytes(anim.name))
            buffer.extend(struct.pack('I', int(anim.keyframes[-1].time))) # playing past final keyframe's time seems unpredictable
            buffer.extend(self._vector_to_bytes(anim.bounds_min))
            buffer.extend(self._vector_to_bytes(anim.bounds_max))
            buffer.extend(struct.pack('I', len(anim.keyframes)))
            for keyframe in anim.keyframes:
                buffer.extend(struct.pack('I', int(keyframe.time)))
                buffer.extend(self._vector_to_bytes(keyframe.bounds_min))
                buffer.extend(self._vector_to_bytes(keyframe.bounds_max))
                buffer.extend(self._string_to_bytes(keyframe.string))

            for node_index, (node_transform_list, node) in enumerate(zip(anim.node_keyframe_transforms, model.nodes)):
                for keyframe_transform in node_transform_list:
                    if model.flip_anim:
                        keyframe_transform.rotation.conjugate()
                    buffer.extend(self._transform_to_bytes(keyframe_transform))

                for keyframe_index, keyframe in enumerate(anim.keyframes):
                    for md_vert_index, md_vert in enumerate(node.md_vert_list):
                        index = keyframe_index * node.md_vert_count + md_vert_index
                        buffer.extend(struct.pack('BBB', int(anim.vertex_deformations[node][index].x * 255), int(anim.vertex_deformations[node][index].y * 255), int(anim.vertex_deformations[node][index].z * 255)))

                scale = Vector((1, 1, 1))
                translation = Vector()
                if node in anim.vertex_deformation_bounds:
                    scale = (anim.vertex_deformation_bounds[node][1] - anim.vertex_deformation_bounds[node][0]) / 255
                    translation = anim.vertex_deformation_bounds[node][0]

                buffer.extend(self._vector_to_bytes(scale))
                buffer.extend(self._vector_to_bytes(translation))

        sections.append(Section('Animation', bytes(buffer)))

        ''' Animation Dimensions '''
        buffer = bytearray()

        for anim in model.animations:
            # use final frame's bounds because last frame is the same as first frame in a loop, and unique in a non-loop (the most likely candidate for collision in-engine)
            buffer.extend(self._vector_to_bytes((-anim.keyframes[-1].bounds_min + anim.keyframes[-1].bounds_max) / 2))

        sections.append(Section('AnimDims', bytes(buffer)))

        ''' Transform Information '''
        # TODO: I don't care about LithTech 1.5, conditional with UI toggle?
        '''buffer = bytearray()
        buffer.extend(struct.pack('II', model.flip_geom, model.flip_anim))
        sections.append(Section('TransformInfo', bytes(buffer)))'''

        with open(path, 'wb') as f:
            for idx, section in enumerate(sections):
                f.write(self._string_to_bytes(section.name))
                if idx + 1 == len(sections):
                    f.write(struct.pack('i', -1))
                else:
                    f.write(struct.pack('i', len(section.data) + f.tell() + 4))
                f.write(bytes(section.data))
