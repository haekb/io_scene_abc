'''
This is a work-around to get PS2 NOLF models into PC NOLF format.
This mainly a total hack, and probably will be removed once animations and exporting is fixed.
'''
import bpy
import bpy_extras
import bmesh
import os
import math
from math import pi
from mathutils import Vector, Matrix, Quaternion, Euler
from bpy.props import StringProperty, BoolProperty, FloatProperty
from .dtx import DTX
from .utils import show_message_box
from .abc import *

from .reader_ltb_ps2 import PS2LTBModelReader
from .writer import ModelWriter


class ConvertLTBToABC(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = 'io_scene_lithtech.ltb_convert'  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = 'Convert Lithtech LTB to ABC'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    # ImportHelper mixin class uses this
    filename_ext = ".ltb"

    filter_glob: StringProperty(
        default="*.ltb",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        # Import the model
        model = PS2LTBModelReader().from_file(self.filepath)
        model.name = os.path.splitext(os.path.basename(self.filepath))[0]

        # Fill in some parts of the model we currently dont..
        stubber = ModelStubber()
        model = stubber.execute(model)

        ltb_path = self.filepath
        abc_path = self.filepath.replace('ltb', 'abc')

        print ("Converting %s to %s" % (ltb_path, abc_path) )

        ModelWriter().write(model, abc_path)

        return {'FINISHED'}

    @staticmethod
    def menu_func_import(self, context):
        self.layout.operator(ConvertLTBToABC.bl_idname, text='Convert PS2 LTB to ABC.')

class ModelStubber(object):
    def execute(self, model):

        # Set the first node as removable
        model.nodes[0].is_removable = True

        # First node seems to be off...
        model.nodes[0].bind_matrix = Matrix()

        model.nodes[0].bind_matrix[0][0] = -1.0
        model.nodes[0].bind_matrix[0][1] = 0.0
        model.nodes[0].bind_matrix[0][2] = 0.0
        model.nodes[0].bind_matrix[0][3] = 0.0

        model.nodes[0].bind_matrix[1][0] = 0.0
        model.nodes[0].bind_matrix[1][1] = -1.0
        model.nodes[0].bind_matrix[1][2] = 0.0
        model.nodes[0].bind_matrix[1][3] = -1.543487

        model.nodes[0].bind_matrix[2][0] = 0.0
        model.nodes[0].bind_matrix[2][1] = 0.0
        model.nodes[0].bind_matrix[2][2] = 1.0
        model.nodes[0].bind_matrix[2][3] = 0.0

        model.nodes[0].bind_matrix[3][0] = 0.0
        model.nodes[0].bind_matrix[3][1] = 0.0
        model.nodes[0].bind_matrix[3][2] = 0.0
        model.nodes[0].bind_matrix[3][3] = 1.0

        '''
        This function will just create fake parts of the model
        Because LithTech needs at least something in every section!
        '''
        animation = Animation()
        animation.name = 'ConvertedFromPS2'
        animation.extents = Vector((10, 10, 10))
        animation.keyframes.append(Animation.Keyframe())
        for node_index, (node) in enumerate(model.nodes):
            transforms = list()
            for _ in animation.keyframes:
                transform = Animation.Keyframe.Transform()
                transforms.append(transform)
            animation.node_keyframe_transforms.append(transforms)
        model.animations.append(animation)

        ''' ChildModels '''
        child_model = ChildModel()

        for _ in model.nodes:
            child_model.transforms.append(Animation.Keyframe.Transform())
        model.child_models.append(child_model)

        ''' AnimBindings '''
        anim_binding = AnimBinding()
        anim_binding.name = 'base'
        animation.extents = Vector((10, 10, 10))
        model.anim_bindings.append(anim_binding)

        # Save me some time renaming stuff..
        # PS2 doesn't have names for sockets
        human_socket_list = ["RightHand", "Head", "Eyes", "Back", "Nose", "Chin", "LeftHand", "LeftFoot", "RightFoot", "Snowmobile", "Motorcycle"]

        print( len(model.sockets) , len(human_socket_list))

        if len(model.sockets) == len(human_socket_list):
            for i in range( len(model.sockets) ):
                model.sockets[i].name = human_socket_list[i]
            
        print(model.sockets[0])

        return model