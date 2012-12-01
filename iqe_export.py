# Inter-Quake Export

bl_info = {
	"name": "Export Inter-Quake Model (.iqe)",
	"description": "Export Inter-Quake Model.",
	"author": "Tor Andersson",
	"version": (2012, 12, 1),
	"blender": (2, 6, 4),
	"location": "File > Export > Inter-Quake Model",
	"wiki_url": "http://github.com/ccxvii/asstools",
	"category": "Import-Export",
}

import bpy, math, struct, os, sys

from bpy.props import *
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix, Quaternion, Vector

def make_blend(groups, vertex_groups, bone_map):
	vb = []
	for g in groups:
		n = vertex_groups[g.group].name
		if n in bone_map:
			vb += [ bone_map[n], g.weight ]
	return tuple(vb)

def export_mesh(file, mesh, mesh_name, vertex_groups, bone_map):
	texcoords = mesh.tessface_uv_textures.active
	colors = mesh.tessface_vertex_colors.active

	out = {}
	for face in mesh.tessfaces:
		fm = face.material_index
		if not fm in out:
			out[fm] = []
		out[fm].append(face)

	for fm in out.keys():
		vertex_map = {}
		vertex_list = []
		face_list = []

		for face in out[fm]:
			ft = texcoords and texcoords.data[face.index]
			fc = colors and colors.data[face.index]
			ft = ft and [ft.uv1, ft.uv2, ft.uv3, ft.uv4]
			fc = fc and [fc.color1, fc.color2, fc.color3, fc.color4]
			f = []
			for i, v in enumerate(face.vertices):
				vp = tuple(mesh.vertices[v].co)
				vn = tuple(mesh.vertices[v].normal)
				vt = ft and tuple(ft[i])
				vc = fc and tuple(fc[i])
				vb = bone_map and make_blend(mesh.vertices[v].groups, vertex_groups, bone_map)
				v = vp, vn, vt, vc, vb
				if v not in vertex_map:
					vertex_map[v] = len(vertex_list)
					vertex_list.append(v)
				f.append(vertex_map[v])
			face_list.append(f)

		file.write("\n")
		file.write("mesh \"%s\"\n" % mesh_name)
		file.write("material \"%s\"\n" % mesh.materials[fm].name)
		for vp, vn, vt, vc, vb in vertex_list:
			file.write("vp %.9g %.9g %.9g\n" % vp)
			file.write("vn %.9g %.9g %.9g\n" % vn)
			if vt: file.write("vt %.9g %.9g\n" % (vt[0], 1.0 - vt[1]))
			if vc: file.write("vc %.9g %.9g %.9g\n" % vc)
			if vb: file.write("vb %s\n" % " ".join("%.9g" % x for x in vb))
		for f in face_list:
			if len(f) == 3:
				file.write("fm %d %d %d\n" % (f[2], f[1], f[0]))
			else:
				file.write("fm %d %d %d %d\n" % (f[3], f[2], f[1], f[0]))

def write_pose(file, t, r, s):
	if abs(s.x - 1.0) > 0.001 or abs(s.y - 1.0) > 0.001 or abs(s.z - 1.0) > 0.001:
		file.write("pq %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g\n" %
			(t.x, t.y, t.z, r.x, r.y, r.z, r.w, s.x, s.y, s.z))
	else:
		file.write("pq %.9g %.9g %.9g %.9g %.9g %.9g %.9g\n" %
			(t.x, t.y, t.z, r.x, r.y, r.z, r.w))

def export_armature(file, amtobj):
	amt = amtobj.data

	bone_map = {}
	bone_list = []

	file.write("\n")
	for bone in amt.bones:
		if not bone in bone_map:
			bone_map[bone.name] = len(bone_list)
			bone_list.append(bone)
		parent = bone_map[bone.parent.name] if bone.parent else -1
		file.write("joint \"%s\" %d\n" % (bone.name, parent))

	file.write("\n")
	for bone in amt.bones:
		matrix = bone.matrix_local
		if bone.parent:
			matrix = bone.parent.matrix_local.inverted() * bone.matrix_local
		t, r, s = matrix.decompose()
		write_pose(file, t, r, s)

	return bone_map

def export_iqe(filename):
	file = open(filename, "w")
	file.write("# Inter-Quake Export\n")

	for scene in bpy.data.scenes:
		for obj in scene.objects:
			if obj.type == 'MESH':
				print("exporting object", obj.name)

				# temporarily disable armature modifiers
				amtmods = []
				for mod in obj.modifiers:
					if mod.type == 'ARMATURE':
						amtmods.append((mod, mod.show_viewport))
						mod.show_viewport = False

				amt = obj.find_armature()
				if amt:
					bone_map = amt and export_armature(file, amt)
				else:
					bone_map = None

				mesh = obj.to_mesh(scene, True, 'PREVIEW')
				mesh.calc_tessface()
				export_mesh(file, mesh, obj.name, obj.vertex_groups, bone_map)
				bpy.data.meshes.remove(mesh)

				# restore armature modifiers
				for mod, show_viewport in amtmods:
					mod.show_viewport = show_viewport

#
# Register addon
#

class ExportIQE(bpy.types.Operator, ExportHelper):
	bl_idname = "export.iqe"
	bl_label = "Export IQE"

	filename_ext = ".iqe"

	def execute(self, context):
		export_iqe(self.properties.filepath)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ExportIQE.bl_idname, text="Inter-Quake Model (.iqe)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func)

def batch(output):
	export_iqe(output)

if __name__ == "__main__":
	register()
	if len(sys.argv) > 4 and sys.argv[-2] == '--':
		batch(sys.argv[-1])
