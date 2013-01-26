#!/usr/bin/env python

bl_info = {
	"name": "Import Inter-Quake Export (.iqe)",
	"description": "Import Inter-Quake Export.",
	"author": "Tor Andersson",
	"version": (2013, 1, 26),
	"blender": (2, 6, 5),
	"location": "File > Import > Inter-Quake Export",
	"wiki_url": "http://github.com/ccxvii/asstools",
	"category": "Import-Export",
}

import bpy, math, shlex, struct, os, sys, glob

from bpy.props import *
from bpy_extras.io_utils import ImportHelper, unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image
from mathutils import Matrix, Quaternion, Vector

# see blenkernel/intern/armature.c for vec_roll_to_mat3
# see blenkernel/intern/armature.c for mat3_to_vec_roll
# see makesrna/intern/rna_armature.c for rna_EditBone_matrix_get

def vec_roll_to_mat3(vec, roll):
	target = Vector((0,1,0))
	nor = vec.normalized()
	axis = target.cross(nor)
	if axis.dot(axis) > 0.000001:
		axis.normalize()
		theta = target.angle(nor)
		bMatrix = Matrix.Rotation(theta, 3, axis)
	else:
		updown = 1 if target.dot(nor) > 0 else -1
		bMatrix = Matrix.Scale(updown, 3)
	rMatrix = Matrix.Rotation(roll, 3, nor)
	mat = rMatrix * bMatrix
	return mat

def mat3_to_vec_roll(mat):
	vec = mat.col[1]
	vecmat = vec_roll_to_mat3(mat.col[1], 0)
	vecmatinv = vecmat.copy()
	vecmatinv.invert()
	rollmat = vecmatinv * mat
	roll = math.atan2(rollmat[0][2], rollmat[2][2])
	return vec, roll

def reorder(f, ft, fc):
	# funny shit! see bpy_extras.io_utils.unpack_face_list()
	if len(f) == 3:
		if f[2] == 0:
			f = f[1], f[2], f[0]
			ft = ft[1], ft[2], ft[0]
			fc = fc[1], fc[2], fc[0]
	else: # assume quad
		if f[3] == 0 or f[2] == 0:
			f = f[2], f[3], f[0], f[1]
			ft = ft[2], ft[3], ft[0], ft[1]
			fc = fc[2], fc[3], fc[0], fc[1]
	return f, ft, fc

def isdegenerate(f):
	if len(f) == 3:
		a, b, c = f
		return a == b or a == c or b == c
	if len(f) == 4:
		a, b, c, d = f
		return a == b or a == c or a == d or b == c or b == d
	return True

class Mesh:
	def __init__(self, name):
		self.name = name
		self.material = None
		self.positions = []
		self.texcoords = []
		self.normals = []
		self.colors = []
		self.blends = []
		self.faces = []
		self.custom = [[] for x in range(10)]

class Animation:
	def __init__(self, name):
		self.name = name
		self.framerate = 30.0
		self.loop = False
		self.frames = []

class Model:
	def __init__(self, name):
		self.name = name
		self.bones = []
		self.bindpose = []
		self.meshes = []
		self.anims = []
		self.vertexarrays = []
		self.comment = []

def load_model(filename):
	def blend_pairs(t):
		return tuple(zip(t[::2], t[1::2]))
	name = filename.split("/")[-1].split("\\")[-1].split(".")[0]
	file = open(filename)
	line = file.readline()
	if not line.startswith("# Inter-Quake Export"):
		raise Exception("Not an IQE file!")
	model = Model(name)
	mesh = None
	pose = model.bindpose
	anim = None
	comment = False
	for line in file:
		if comment:
			model.comment.append(line)
			continue
		if '"' in line or '#' in line:
			line = shlex.split(line, "#")
		else:
			line = line.split()
		if len(line) == 0:
			pass
		elif line[0] == "joint":
			name = line[1]
			parent = int(line[2])
			model.bones.append((name, parent))
		elif line[0] == "pq":
			pose.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "mesh":
			mesh = Mesh(line[1])
			model.meshes.append(mesh)
		elif line[0] == "material":
			mesh.material = line[1]
		elif line[0] == "vp": mesh.positions.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vt": mesh.texcoords.append(tuple([float(x) for x in line[1:3]]))
		elif line[0] == "vn": mesh.normals.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vc": mesh.colors.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vb": mesh.blends.append(blend_pairs([float(x) for x in line[1:]]))
		elif line[0] == "v0": mesh.custom[0].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v1": mesh.custom[1].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v2": mesh.custom[2].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v3": mesh.custom[3].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v4": mesh.custom[4].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v5": mesh.custom[5].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v6": mesh.custom[6].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v7": mesh.custom[7].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v8": mesh.custom[8].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v9": mesh.custom[9].append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "fm":
			mesh.faces.append(tuple([int(x) for x in line[1:]]))
		elif line[0] == "animation":
			anim = Animation(line[1])
			model.anims.append(anim)
		elif line[0] == "framerate":
			anim.framerate = float(line[1])
		elif line[0] == "loop":
			anim.loop = True
		elif line[0] == "frame":
			pose = []
			anim.frames.append(pose)
		elif line[0] == "vertexarray":
			model.vertexarrays.append(tuple(line[1:]))
		elif line[0] == "comment":
			comment = True
	return model

# We preserve matrices and the bone orientations, by
# duplicating the conversion that blender does internally
# to map between bone head/tail/roll and a matrix.

def calc_pose_mats(iqmodel, iqpose, bone_axis):
	loc_pose_mat = [None] * len(iqmodel.bones)
	abs_pose_mat = [None] * len(iqmodel.bones)
	recalc = False

	# convert pose to local matrix and compute absolute matrix
	for n, iqbone in enumerate(iqmodel.bones):
		pose_pos = iqpose[n].translate
		pose_rot = iqpose[n].rotate
		pose_scale = iqpose[n].scale

		local_pos = Vector(pose_pos)
		local_rot = Quaternion((pose_rot[3], pose_rot[0], pose_rot[1], pose_rot[2]))
		local_scale = Vector(pose_scale)

		mat_pos = Matrix.Translation(local_pos)
		mat_rot = local_rot.to_matrix().to_4x4()
		mat_scale = Matrix.Scale(local_scale.x, 3).to_4x4()
		loc_pose_mat[n] = mat_pos * mat_rot * mat_scale

		if iqbone[1] >= 0:
			abs_pose_mat[n] = abs_pose_mat[iqbone[1]] * loc_pose_mat[n]
		else:
			abs_pose_mat[n] = loc_pose_mat[n]

	# Remove negative scaling from bones.
	# Due to numerical instabilities in blender's matrix <-> head/tail/roll math
	# this isn't always stable when the bones are in the X axis. If the bones
	# end up rotated 90 degrees from what they should be, that's the reason.
	for n, iqbone in enumerate(iqmodel.bones):
		if abs_pose_mat[n].is_negative:
			if not hasattr(iqmodel, 'abs_bind_mat'):
				print("warning: removing negative scale in bone", iqbone[0])
			abs_pose_mat[n] = abs_pose_mat[n] * Matrix.Scale(-1, 4)
			recalc = True

	# flip bone axis (and recompute local matrix if needed)
	if bone_axis == 'X':
		axis_flip = Matrix.Rotation(math.radians(-90), 4, 'Z')
		abs_pose_mat = [m * axis_flip for m in abs_pose_mat]
		recalc = True
	if bone_axis == 'Z':
		axis_flip = Matrix.Rotation(math.radians(-90), 4, 'X')
		abs_pose_mat = [m * axis_flip for m in abs_pose_mat]
		recalc = True

	if recalc:
		inv_pose_mat = [m.inverted() for m in abs_pose_mat]
		for n, iqbone in enumerate(iqmodel.bones):
			if iqbone[1] >= 0:
				loc_pose_mat[n] = inv_pose_mat[iqbone[1]] * abs_pose_mat[n]
			else:
				loc_pose_mat[n] = abs_pose_mat[n]

	return loc_pose_mat, abs_pose_mat

def make_armature(iqmodel, bone_axis):

	if len(iqmodel.bones) == 0: return None
	if len(iqmodel.bindpose) != len(iqmodel.bones): return None

	print("importing armature with %d bones" % len(iqmodel.bones))

	amt = bpy.data.armatures.new(iqmodel.name)
	obj = bpy.data.objects.new(iqmodel.name + ".amt", amt)
	bpy.context.scene.objects.link(obj)
	bpy.context.scene.objects.active = obj

	bpy.ops.object.mode_set(mode='EDIT')

	loc_bind_mat, abs_bind_mat = calc_pose_mats(iqmodel, iqmodel.bindpose, bone_axis)
	iqmodel.abs_bind_mat = abs_bind_mat
	iqmodel.loc_bind_mat = loc_bind_mat
	iqmodel.inv_loc_bind_mat = [m.inverted() for m in loc_bind_mat]

	for n, iqbone in enumerate(iqmodel.bones):
		bone = amt.edit_bones.new(iqbone[0])
		parent = None
		if iqbone[1] >= 0:
			parent = amt.edit_bones[iqbone[1]]
			bone.parent = parent

		# TODO: bone scaling
		pos = abs_bind_mat[n].to_translation()
		axis, roll = mat3_to_vec_roll(abs_bind_mat[n].to_3x3())
		axis *= 0.125 # short bones
		bone.roll = roll
		bone.head = pos
		bone.tail = pos + axis

		# extend parent and connect if we are aligned
		if parent:
			a = (bone.head - parent.head).normalized()
			b = (parent.tail - parent.head).normalized()
			if a.dot(b) > 0.9999:
				parent.tail = bone.head
				bone.use_connect = True

	bpy.ops.object.mode_set(mode='OBJECT')

	return obj

def make_pose(iqmodel, frame, amtobj, bone_axis, tick):
	loc_pose_mat, _ = calc_pose_mats(iqmodel, frame, bone_axis)
	for n, iqbone in enumerate(iqmodel.bones):
		name = iqbone[0]
		pose_bone = amtobj.pose.bones[name]
		pose_bone.matrix_basis = iqmodel.inv_loc_bind_mat[n] * loc_pose_mat[n]
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='location')
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='rotation_quaternion')
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='scale')

def make_anim(iqmodel, anim, amtobj, bone_axis):
	print("importing animation %s with %d frames" % (anim.name, len(anim.frames)))
	action = bpy.data.actions.new(anim.name)
	action.id_root = 'OBJECT'
	action.use_fake_user = True
	amtobj.animation_data.action = action
	for n in range(len(anim.frames)):
		make_pose(iqmodel, anim.frames[n], amtobj, bone_axis, n)
	return action

def make_actions(iqmodel, amtobj, bone_axis):
	bpy.context.scene.frame_start = 0
	amtobj.animation_data_create()
	for anim in iqmodel.anims:
		action = make_anim(iqmodel, anim, amtobj, bone_axis)

def make_material(matname):
	texname = matname.split("+")[-1]
	imgname = texname + ".png"

	if imgname in bpy.data.images:
		img = bpy.data.images[imgname]
	else:
		img = load_image("textures/" + imgname, place_holder=True)

	if texname in bpy.data.textures:
		tex = bpy.data.textures[texname]
	else:
		tex = bpy.data.textures.new(texname, type='IMAGE')
		tex.image = img
		tex.use_alpha = True

	if matname in bpy.data.materials:
		mat = bpy.data.materials[matname]
	else:
		mat = bpy.data.materials.new(matname)
		mat.game_settings.alpha_blend = 'CLIP'
		mat.diffuse_intensity = 1.0
		mat.specular_intensity = 0.0
		mat.use_transparency = True
		mat.use_object_color = True
		mat.use_vertex_color_paint = False
		slot = mat.texture_slots.create(0)
		slot.texture = tex
		slot.texture_coords = 'UV'
		slot.uv_layer = "UVMap"
		slot.use_map_color_diffuse = True
		slot.use_map_alpha = True
		slot.blend_type = 'MULTIPLY'

	return mat, img

# Create mesh object with normals, texcoords, vertex colors,
# and an armature modifier if the model is skinned.

def gather_meshes(model):
	meshes = {}
	for mesh in model.meshes:
		if mesh.name not in meshes:
			meshes[mesh.name] = []
		meshes[mesh.name].append(mesh)
	return meshes

def gather_vt(vertexarrays, mesh):
	vt, vt_names = [], []
	if len(mesh.texcoords) > 0:
		vt.append(mesh.texcoords)
		vt_names.append("UVMap")
	for i in range(10):
		type = "custom%d" % i
		if len(mesh.custom[i]) > 0:
			for va in vertexarrays:
				if va[0] == type and int(va[2]) == 2:
					vt.append(mesh.custom[i])
					vt_names.append(va[3])
	return vt, vt_names

def gather_vc(vertexarrays, mesh):
	vc, vc_names = [], []
	if len(mesh.colors) > 0:
		vc.append(mesh.colors)
		vc_names.append("Col")
	for i in range(10):
		type = "custom%d" % i
		if len(mesh.custom[i]) > 0:
			for va in vertexarrays:
				if va[0] == type and int(va[2]) >= 3:
					vc.append(mesh.custom[i])
					vc_names.append(va[3])
	return vc, vc_names

def make_mesh(model, name, meshes, amtobj):
	print("importing mesh", name, "with", len(meshes), "parts")

	mesh = bpy.data.meshes.new(name)
	obj = bpy.data.objects.new(name, mesh)
	bpy.context.scene.objects.link(obj)
	bpy.context.scene.objects.active = obj

	# Set the mesh to single-sided to spot normal errors
	mesh.show_double_sided = False

	# Flip winding
	for m in meshes:
		m.faces = [x[::-1] for x in m.faces]

	# Positions, normals, blends and vertex groups go to vertices.
	# Material, texture coords and vertex colors go to faces.

	weld = {}
	out_vp, out_vn, out_vb = [], [], []
	out_f, out_f_mat, out_f_img, out_ft, out_fc = [], [], [], [], []

	for m in meshes:
		material, image = make_material(m.material)
		if material.name not in mesh.materials:
			mesh.materials.append(material)
		material_index = mesh.materials.find(material.name)

		out_from_in = []

		for i, p in enumerate(m.positions):
			n = m.normals[i] if len(m.normals) > i else (0,0,1)
			b = m.blends[i] if len(m.blends) > i else None
			# TODO: vertex groups custom data
			key = p, n, b
			if not key in weld:
				weld[key] = len(out_vp)
				out_vp.append(p)
				out_vn.append(n)
				out_vb.append(b)
			out_from_in.append(weld[key])

		vt, vt_names = gather_vt(model.vertexarrays, m)
		vc, vc_names = gather_vc(model.vertexarrays, m)

		print(vc_names)
		print(vc)

		for face in m.faces:
			f = [out_from_in[v] for v in face]
			ft = [[t[v] for t in vt] for v in face]
			fc = [[c[v] for c in vc] for v in face]
			f, ft, fc = reorder(f, ft, fc)
			if isdegenerate(f):
				print("degenerate face", f)
				continue

			out_f.append(f)
			out_ft.append(ft)
			out_fc.append(fc)
			out_f_mat.append(material_index)
			out_f_img.append(image)

	print("\tcollected %d vertices and %d faces" % (len(out_vp), len(out_f)))

	# Create mesh vertex and face data

	mesh.vertices.add(len(out_vp))
	mesh.vertices.foreach_set("co", unpack_list(out_vp))

	mesh.tessfaces.add(len(out_f))
	mesh.tessfaces.foreach_set("vertices_raw", unpack_face_list(out_f))

	for i, face in enumerate(mesh.tessfaces):
		face.use_smooth = True
		face.material_index = out_f_mat[i]

	for k, name in enumerate(vt_names):
		layer = mesh.tessface_uv_textures.new(name)
		for i, face in enumerate(mesh.tessfaces):
			data = layer.data[i]
			ft = out_ft[i]
			data.image = out_f_img[i]
			data.uv1 = (ft[0][k][0], 1-ft[0][k][1])
			data.uv2 = (ft[1][k][0], 1-ft[1][k][1])
			data.uv3 = (ft[2][k][0], 1-ft[2][k][1])
			if len(ft) > 3:
				data.uv4 = (ft[3][k][0], 1-ft[3][k][1])

	for k, name in enumerate(vc_names):
		layer = mesh.tessface_vertex_colors.new(name)
		for i, face in enumerate(mesh.tessfaces):
			data = layer.data[i]
			data.color1 = tuple(out_fc[i][0][k][:3])
			data.color2 = tuple(out_fc[i][1][k][:3])
			data.color3 = tuple(out_fc[i][2][k][:3])
			if len(out_fc[i]) > 3:
				data.color4 = tuple(out_fc[i][3][k][:3])

	# Vertex groups and armature modifier for skinning

	if amtobj:
		for iqbone in iqmodel.bones:
			obj.vertex_groups.new(iqbone[0])

		for vgroup in obj.vertex_groups:
			for i, b in enumerate(out_vb):
				idx, wgt = b
				if idx == vgroup.index:
					vgroup.add([i], idx, 'REPLACE')

		mod = obj.modifiers.new("Armature", 'ARMATURE')
		mod.object = amtobj
		mod.use_vertex_groups = True

	# Update mesh polygons from tessfaces

	mesh.update()

	# Must set normals after mesh.update() or they will be recalculated.
	mesh.vertices.foreach_set("normal", unpack_list(out_vn))

	return obj

def make_model(iqmodel, bone_axis):
	print("importing model", iqmodel.name)

	for obj in bpy.context.scene.objects:
		obj.select = False

	group = bpy.data.groups.new(iqmodel.name)

	amtobj = make_armature(iqmodel, bone_axis)
	if amtobj:
		group.objects.link(amtobj)

	meshes = gather_meshes(iqmodel)
	for name in meshes:
		meshobj = make_mesh(iqmodel, name, meshes[name], amtobj)
		if amtobj:
			meshobj.parent = amtobj
		group.objects.link(meshobj)

	if len(iqmodel.anims) > 0:
		make_actions(iqmodel, amtobj, bone_axis)

	print("all done.")

def import_iqe(filename, bone_axis='Y'):
	iqmodel = load_model(filename)
	make_model(iqmodel, bone_axis)
	bpy.ops.screen.frame_jump()

# Register addon

class ImportIQE(bpy.types.Operator, ImportHelper):
	bl_idname = "import.iqe"
	bl_label = "Import IQE"

	filename_ext = ".iqe"
	filter_glob = StringProperty(default="*.iqe", options={'HIDDEN'})
	filepath = StringProperty(name="File Path", maxlen=1024, default="")

	bone_axis = EnumProperty(name="Bone Axis",
			description="Flip bones to extend along the Y axis",
			items=[
				('Y', "Preserve", ""),
				('X', "Flip from X to Y", ""),
				('Z', "Flip from Z to Y", "")
			],
			default='Y')

	def execute(self, context):
		import_iqe(self.properties.filepath, self.bone_axis)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ImportIQE.bl_idname, text="Inter-Quake Export (.iqe)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(menu_func)

def batch_zap():
	if "Cube" in bpy.data.objects:
		obj = bpy.data.objects['Cube']
		bpy.context.scene.objects.unlink(obj)
		bpy.data.objects.remove(obj)

def batch(input):
	batch_zap()
	output = os.path.splitext(input)[0] + ".blend"
	import_iqe(input)
	print("Saving", output)
	bpy.ops.wm.save_mainfile(filepath=output, check_existing=False)

def batch_many(input_list):
	batch_zap()
	output = "output.blend"
	for input in input_list:
		import_iqe(input)
	print("Saving", output)
	bpy.ops.wm.save_mainfile(filepath=output, check_existing=False)

if __name__ == "__main__":
	register()
	if len(sys.argv) > 4 and sys.argv[-2] == '--':
		if "*" in sys.argv[-1]:
			batch_many(glob.glob(sys.argv[-1]))
		else:
			batch(sys.argv[-1])
	elif len(sys.argv) > 4 and sys.argv[4] == '--':
		batch_many(sys.argv[5:])
