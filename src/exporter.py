from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, EnumProperty
from .builder import ModelBuilder
from .writer_abc_pc import ABCModelWriter
from .writer_lta_pc import LTAModelWriter


class ExportOperatorABC(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "io_scene_lithtech.abc_export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Lithtech ABC"

    # ExportHelper mixin class uses this
    filename_ext = ".ABC"

    filter_glob: StringProperty(
        default="*.abc",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def item_cb(self, context):
        armatures_iter = filter(lambda x: x.type == 'ARMATURE', context.scene.objects)
        return [(x.name, x.name, '', 'OUTLINER_OB_ARMATURE', 0) for x in armatures_iter]

    armature: EnumProperty(
        name="Armature",
        description="Choose an amarture to export",
        items=item_cb,
    )

    def execute(self, context):
        armature_object = context.scene.objects[self.armature]
        model = ModelBuilder().from_armature(armature_object)
        ABCModelWriter().write(model, self.filepath)
        return {'FINISHED'}

    def menu_func_export(self, context):
        self.layout.operator(ExportOperatorABC.bl_idname, text='Lithtech ABC (.abc)')

class ExportOperatorLTA(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "io_scene_lithtech.lta_export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Lithtech LTA"

    # ExportHelper mixin class uses this
    filename_ext = ".LTA"

    filter_glob: StringProperty(
        default="*.lta",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def item_cb(self, context):
        armatures_iter = filter(lambda x: x.type == 'ARMATURE', context.scene.objects)
        return [(x.name, x.name, '', 'OUTLINER_OB_ARMATURE', 0) for x in armatures_iter]

    armature: EnumProperty(
        name="Armature",
        description="Choose an amarture to export",
        items=item_cb,
    )

    def execute(self, context):
        armature_object = context.scene.objects[self.armature]
        model = ModelBuilder().from_armature(armature_object)
        LTAModelWriter().write(model, self.filepath)
        return {'FINISHED'}

    def menu_func_export(self, context):
        self.layout.operator(ExportOperatorLTA.bl_idname, text='Lithtech LTA (.lta)')
