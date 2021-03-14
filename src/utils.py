import bpy
import bmesh
from enum import Enum

# Blender default: 25fps = frame 0-24 for our purposes
def get_framerate():
    return (bpy.context.window.scene.render.fps) / 1000

# Enums
class LTAVersion(Enum):
    TALON = 'lithtech-talon'
    LT22 = 'lithtech-2.2'
    # Not supported...yet
    JUPITER = 'lithtech-jupiter'
    JUPITER_EX = 'lithtech-jupiter-ex'

    @staticmethod
    def get_text(version):
        if version == LTAVersion.TALON.value:
            return 'Lithtech Talon'
        elif version == LTAVersion.LT22.value:
            return 'Lithtech 2.2'
        elif version == LTAVersion.JUPITER.value:
            return 'Lithtech Jupiter (Not Supported)'
        elif version == LTAVersion.JUPITER_EX.value:
            return 'Lithtech Jupiter EX (Not Supported)'
        # End If
        return 'Unknown Version'

class ABCVersion(Enum):
    ABC12 = 'abc-12'
    ABC6 = 'abc-6'
    # Not supported...yet
    ABC13 = 'abc-13'

    @staticmethod
    def get_text(version):
        if version == ABCVersion.ABC12.value:
            return 'ABC v12 (Lithtech 2.1/Talon)'
        elif version == ABCVersion.ABC13.value:
            return 'ABC v13 (Not Supported)'
        elif version == ABCVersion.ABC6.value:
            return 'ABC v6 (Lithtech 1.0)' #1.0/1.5?
        # End If
        return 'Unknown Version'

# Helper functions

# Displays a message box that's immensely more helpful than errors
def show_message_box(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def delete_all_objects():
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def make_suzanne():
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # bpy.ops.view3d.snap_cursor_to_center()
    mesh = bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))
    bpy.ops.object.armature_add(location=(0, 0, 0))

    mesh = bpy.context.scene.objects['Suzanne']
    armature = bpy.context.scene.objects['Armature']

    mesh.select = True
    bpy.context.scene.objects.active = mesh

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)

    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)
    bm.to_mesh(mesh.data)
    bm.free()

    material = bpy.data.materials.new('Placeholder')
    mesh.data.materials.append(material)

    mesh.select = True
    armature.select = True
    bpy.context.scene.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')