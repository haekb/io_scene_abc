from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty
from .builder import ModelBuilder
from .writer_abc_pc import ABCModelWriter
from .writer_abc_v6_pc import ABCV6ModelWriter
from .writer_lta_pc import LTAModelWriter
from .utils import ABCVersion, LTAVersion

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
        return [(x.name, x.name, x.name) for x in armatures_iter] #[(x.name, x.name, '', 'OUTLINER_OB_ARMATURE', 0) for x in armatures_iter]

    armature: EnumProperty(
        name="Armature",
        description="Choose an amarture to export",
        items=item_cb,
    )

    def item_abc_version(self, context):
        items = []
        for version in ABCVersion:
            value = version.value
            items.append( (value, ABCVersion.get_text(value), ABCVersion.get_text(value)) )
        # End For
        return items
    # End Func

    abc_version: EnumProperty(
        name="ABC Version",
        description="Choose a version of ABC to export",
        items = item_abc_version,
    )

    should_export_transform: BoolProperty(
        name="Export V6 Transform Info (Not Implemented)",
        description="When checked, will append TransformInfo section for Lithtech 1.5",
        default=False,
    )

    def execute(self, context):
        if self.abc_version in [ABCVersion.ABC13.value]:
            raise Exception('Not implemented ({}).'.format(ABCVersion.get_text(self.abc_version)))

        armature_object = context.scene.objects[self.armature]
        model = ModelBuilder().from_armature(armature_object)

        if self.abc_version == ABCVersion.ABC6.value:
            ABCV6ModelWriter().write(model, self.filepath, self.abc_version)
        else:
            ABCModelWriter().write(model, self.filepath, self.abc_version)

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

    def item_lta_version(self, context):
        items = []
        for version in LTAVersion:
            value = version.value
            items.append( (value, LTAVersion.get_text(value), LTAVersion.get_text(value)) )
        # End For
        return items
    # End Func

    lta_version: EnumProperty(
        name="LTA Version",
        description="Choose a version of LTA to export",
        items = item_lta_version,
    )

    def execute(self, context):
        if self.lta_version in [LTAVersion.JUPITER.value, LTAVersion.JUPITER_EX.value]:
            raise Exception('Not implemented ({}).'.format(LTAVersion.get_text(self.lta_version)))

        armature_object = context.scene.objects[self.armature]
        model = ModelBuilder().from_armature(armature_object)
        LTAModelWriter().write(model, self.filepath, self.lta_version)
        return {'FINISHED'}

    def menu_func_export(self, context):
        self.layout.operator(ExportOperatorLTA.bl_idname, text='Lithtech LTA (.lta)')
