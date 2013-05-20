# IQE Exporter (Inter-Quake Export)

bl_info = {
	"name": "Inter-Quake Export (.iqe)",
	"description": "Export IQE (Inter-Quake Export)",
	"author": "Tor Andersson",
	"version": (2013, 1, 6),
	"blender": (2, 6, 5),
	"location": "File > Export > Inter-Quake Export",
	"wiki_url": "http://github.com/ccxvii/asstools",
	"category": "Import-Export",
}

import bpy, math, struct, os, sys

from bpy.props import *
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix, Quaternion, Vector

def quote(str):
	if " " in str:
		return "\"%s\"" % str
	return str

def make_blend(data, vertex_groups, bones):
	raw = []
	total = 0.0
	for g in data:
		name = vertex_groups[g.group].name
		if name in bones:
			raw.append((g.weight, bones[name]))
			total += g.weight
	raw.sort()
	raw.reverse()
	vb = []
	if total == 0.0:
		total = 1.0
	for w, i in raw:
		if w > 0.0:
			vb.append(i)
			vb.append(w / total)
	if len(vb) == 0:
		print("warning: vertex with no bone weights")
		return (0,1)
	return tuple(vb)

def make_group(data, vertex_groups):
	vg = [0] * len(vertex_groups)
	for g in data:
		vg[g.group] = g.weight
	return tuple(vg)

def gather_custom_layers(file, mesh, vertex_groups=None, bones=None, custom={}):
	custom["UVMap"] = "vt"
	custom["Col"] = "vc"

	for layer in mesh.tessface_uv_textures:
		if layer.name != 'UVMap' and layer.name not in custom:
			i = len(custom) - 2
			custom[layer.name] = "v%d" % i
			if i == 0: file.write("\n")
			file.write("vertexarray custom%d float 2 %s\n" % (i, quote(layer.name)))

	for layer in mesh.tessface_vertex_colors:
		if layer.name != 'Col' and layer.name not in custom:
			i = len(custom) - 2
			custom[layer.name] = "v%d" % i
			if i == 0: file.write("\n")
			file.write("vertexarray custom%d ubyte 4 %s\n" % (i, quote(layer.name)))

	if not bones:
		for group in vertex_groups:
			if group.name not in custom:
				i = len(custom) - 2
				custom[group.name] = "v%d" % i
				if i == 0: file.write("\n")
				file.write("vertexarray custom%d float 1 %s\n" % (i, quote(group.name)))

def export_mesh(file, mesh, mesh_name, vertex_groups=None, bones=None, custom={}):
	print("exporting mesh:", mesh_name)

	gather_custom_layers(file, mesh, vertex_groups, bones, custom)

	out = {}
	for face in mesh.tessfaces:
		fm = face.material_index
		if not fm in out:
			out[fm] = []
		out[fm].append(face)

	ft = [None] * len(mesh.tessface_uv_textures)
	fc = [None] * len(mesh.tessface_vertex_colors)

	for fm in out.keys():
		vertex_map = {}
		vertex_list = []
		face_list = []

		for face in out[fm]:
			for i, layer in enumerate(mesh.tessface_uv_textures):
				data = layer.data[face.index]
				uv1 = data.uv1[0], 1.0 - data.uv1[1]
				uv2 = data.uv2[0], 1.0 - data.uv2[1]
				uv3 = data.uv3[0], 1.0 - data.uv3[1]
				uv4 = data.uv4[0], 1.0 - data.uv4[1]
				ft[i] = uv1, uv2, uv3, uv4

			for i, layer in enumerate(mesh.tessface_vertex_colors):
				data = layer.data[face.index]
				color1 = tuple(data.color1)
				color2 = tuple(data.color2)
				color3 = tuple(data.color3)
				color4 = tuple(data.color4)
				fc[i] = color1, color2, color3, color4

			f = []
			for i, v in enumerate(face.vertices):
				vt = tuple([x[i] for x in ft])
				vc = tuple([x[i] for x in fc])
				v = v, vt, vc
				if v not in vertex_map:
					vertex_map[v] = len(vertex_list)
					vertex_list.append(v)
				f.append(vertex_map[v])
			face_list.append(f)

		file.write("\n")
		file.write("mesh %s\n" % quote(mesh_name))
		file.write("material %s\n" % (fm < len(mesh.materials) and quote(mesh.materials[fm].name)))

		for v, vt, vc in vertex_list:
			vp = tuple(mesh.vertices[v].co)
			vn = tuple(mesh.vertices[v].normal)
			vb = bones and make_blend(mesh.vertices[v].groups, vertex_groups, bones)
			vg = not bones and make_group(mesh.vertices[v].groups, vertex_groups)
			file.write("vp %.9g %.9g %.9g\n" % vp)
			file.write("vn %.9g %.9g %.9g\n" % vn)
			for i, layer in enumerate(mesh.tessface_uv_textures):
				file.write("%s %.9g %.9g\n" % (custom[layer.name], vt[i][0], vt[i][1]))
			for i, layer in enumerate(mesh.tessface_vertex_colors):
				file.write("%s %.9g %.9g %.9g 1\n" % (custom[layer.name], vc[i][0], vc[i][1], vc[i][2]))
			if vb:
				file.write("vb %s\n" % " ".join("%.9g" % x for x in vb))
			if vg:
				for i, group in enumerate(vertex_groups):
					file.write("%s %.9g\n" % (custom[group.name], vg[i]))

		for f in face_list:
			if len(f) == 3:
				file.write("fm %d %d %d\n" % (f[2], f[1], f[0]))
			else:
				file.write("fm %d %d %d %d\n" % (f[3], f[2], f[1], f[0]))

def export_object_imp(file, scene, obj, mesh_name, vertex_groups=None, bones=None, custom={}, apply_matrix=False):
	mesh = obj.to_mesh(scene, True, 'PREVIEW')
	if apply_matrix:
		mesh.transform(obj.matrix_world)
	mesh.calc_tessface()
	mesh.calc_normals()
	export_mesh(file, mesh, mesh_name, vertex_groups, bones, custom)
	bpy.data.meshes.remove(mesh)

def export_object(file, scene, obj, bones=None, custom={}, apply_matrix=False):
	# temporarily disable armature modifiers
	amtmods = []
	for mod in obj.modifiers:
		if mod.type == 'ARMATURE':
			amtmods.append((mod, mod.show_viewport))
			mod.show_viewport = False

	if obj.data.shape_keys:
		for shape_key in obj.data.shape_keys.key_blocks:
			shape_key.mute = True
			shape_key.value = 1
		for shape_key in obj.data.shape_keys.key_blocks:
			if shape_key == obj.data.shape_keys.reference_key:
				shape_name = obj.data.name
			else:
				shape_name = obj.data.name + ";" + shape_key.name
			shape_key.mute = False
			export_object_imp(file, scene, obj, shape_name, obj.vertex_groups, bones, custom, apply_matrix)
			shape_key.mute = True
	else:
		export_object_imp(file, scene, obj, obj.data.name, obj.vertex_groups, bones, custom, apply_matrix)

	# restore armature modifiers
	for mod, show_viewport in amtmods:
		mod.show_viewport = show_viewport

def write_pose(file, t, r, s):
	if abs(s.x - 1.0) > 0.001 or abs(s.y - 1.0) > 0.001 or abs(s.z - 1.0) > 0.001:
		file.write("pq %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g\n" %
			(t.x, t.y, t.z, r.x, r.y, r.z, r.w, s.x, s.y, s.z))
	else:
		file.write("pq %.9g %.9g %.9g %.9g %.9g %.9g %.9g\n" %
			(t.x, t.y, t.z, r.x, r.y, r.z, r.w))

def export_armature(file, obj, amt):
	print("exporting armature:", amt.name)

	bone_map = {}
	count = 0

	file.write("\n")
	for bone in amt.bones:
		if not bone in bone_map:
			bone_map[bone.name] = count
			count += 1
		parent = bone_map[bone.parent.name] if bone.parent else -1
		file.write("joint %s %d\n" % (quote(bone.name), parent))

	file.write("\n")
	for bone in amt.bones:
		if bone.parent:
			matrix = bone.parent.matrix_local.inverted() * bone.matrix_local
		else:
			matrix = obj.matrix_world * bone.matrix_local
		t, r, s = matrix.decompose()
		write_pose(file, t, r, s)

	return bone_map

def export_frame(file, obj, amt, bones):
	for amt_bone in amt.bones:
		bone = obj.pose.bones[amt_bone.name]
		if bone.parent:
			matrix = bone.parent.matrix.inverted() * bone.matrix
		else:
			matrix = obj.matrix_world * bone.matrix
		t, r, s = matrix.decompose()
		write_pose(file, t, r, s)

def export_action(file, scene, obj, amt, bones, action):
	startframe = int(action.frame_range[0])
	endframe = int(action.frame_range[1])
	print("exporting action:", action.name, startframe, endframe)
	file.write("\n")
	file.write("animation %s\n" % quote(action.name))
	for time in range(startframe, endframe + 1):
		scene.frame_set(time)
		file.write("\n")
		file.write("frame %d\n" % time)
		export_frame(file, obj, amt, bones)

def export_actions(file, scene, obj, bones):
	if obj.animation_data: old_action = obj.animation_data.action
	old_time = scene.frame_current
	for action in bpy.data.actions:
		obj.animation_data.action = action
		export_action(file, scene, obj, obj.data, bones, action)
	if obj.animation_data: obj.animation_data.action = old_action
	scene.frame_set(old_time)

# ---

def export_object_list(filename, context, list):
	file = open(filename, "w")
	file.write("# Inter-Quake Export\n")

	amt, bones, custom = None, None, {}

	for obj in list:
		if obj.type == 'ARMATURE':
			amt = obj
			break

	if amt:
		bones = export_armature(file, amt, amt.data)

	for obj in list:
		if obj.type == 'MESH' and obj.find_armature() == amt:
			export_object(file, context.scene, obj, bones, custom, apply_matrix=True)

	if amt:
		export_actions(file, context.scene, amt, bones)

	file.close()

class ExportIQE(bpy.types.Operator, ExportHelper):
	bl_idname = "export.iqe"
	bl_label = "Export IQE"

	filename_ext = ".iqe"

	def execute(self, context):
		export_object_list(self.properties.filepath, context, context.selected_objects)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ExportIQE.bl_idname, text="Inter-Quake Export (.iqe)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
	register()
	if len(sys.argv) > 3 and sys.argv[-2] == '--':
		export_object_list(sys.argv[-1], bpy.context, bpy.context.scene.objects)
