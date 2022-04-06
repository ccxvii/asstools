# Inter-Quake Import

bl_info = {
	"name": "Import Inter-Quake Model (.iqm, .iqe)",
	"description": "Import Inter-Quake Model.",
	"author": "Tor Andersson",
	"version": (2012, 12, 2),
	"blender": (2, 80, 0),
	"location": "File > Import > Inter-Quake Model",
	"wiki_url": "http://github.com/ccxvii/asstools",
	"category": "Import-Export",
}

import bpy, math, shlex, struct, os, sys, glob

from bpy.props import *
from bpy_extras.io_utils import ImportHelper, unpack_list
from bpy_extras.image_utils import load_image
from mathutils import Matrix, Quaternion, Vector

# see blenkernel/intern/armature.c for vec_roll_to_mat3
# see blenkernel/intern/armature.c for mat3_to_vec_roll
# see makesrna/intern/rna_armature.c for rna_EditBone_matrix_get

# Compatiblity shims
if bpy.app.version >= (2, 80, 0):
	def matmul(x, y): return x.__matmul__(y)
	def make_group(name): return bpy.data.collections.new(name)
	def link_object(ob): bpy.context.scene.collection.objects.link(ob)
	def select_ob(ob, state=True): ob.select_set(state=state)
else:
	def matmul(x, y): return x * y
	def make_group(name): return bpy.data.groups.new(name)
	def link_object(ob): bpy.context.scene.objects.link(ob)
	def select_ob(ob, state=True): ob.select = state

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
	mat = matmul(rMatrix, bMatrix)
	return mat

def mat3_to_vec_roll(mat):
	vec = mat.col[1]
	vecmat = vec_roll_to_mat3(mat.col[1], 0)
	vecmatinv = vecmat.copy()
	vecmatinv.invert()
	rollmat = matmul(vecmatinv, mat)
	roll = math.atan2(rollmat[0][2], rollmat[2][2])
	return vec, roll

#
# Inter-Quake Model structs
#

class IQMesh:
	def __init__(self, name):
		self.name = name
		self.material = ["unknown"]
		self.faces = []
		self.vp = []
		self.vn = []
		self.vt = []
		self.vc = []
		self.vbi = []
		self.vbw = []
		self.v0 = []
		self.v1 = []
		self.v2 = []
		self.v3 = []
		self.v4 = []
		self.v5 = []
		self.v6 = []
		self.v7 = []
		self.v8 = []
		self.v9 = []

class IQBone:
	def __init__(self, name, parent):
		self.name = name
		self.parent = parent

class IQPose:
	def __init__(self, data):
		self.translate = data[0:3]
		self.rotate = data[3:7]
		if len(data) > 7:
			self.scale = data[7:10]
		else:
			self.scale = (1,1,1)

class IQAnimation:
	def __init__(self, name):
		self.name = name
		self.framerate = 30
		self.loop = False
		self.frames = []

class IQModel:
	def __init__(self, name):
		self.name = name
		self.bones = []
		self.bindpose = []
		self.meshes = []
		self.anims = []
		self.custom_name = {}
		self.custom_size = {}

#
# IQE parser
#

def load_iqe(filename):
	name = filename.split("/")[-1].split("\\")[-1].split(".")[0]
	model = IQModel(name)
	file = open(filename)
	line = file.readline()
	if not line.startswith("# Inter-Quake Export"):
		raise Exception("Not an IQE file!")
	curpose = model.bindpose
	curmesh = None
	curanim = None
	for line in file.readlines():
		if "#" in line or "\"" in line:
			line = shlex.split(line, "#")
		else:
			line = line.split()
		if len(line) == 0:
			pass
		elif line[0] == "vertexarray":
			if line[1].startswith("custom"):
				N = int(line[1][6:])
				model.custom_name[N] = line[4] if len(line) > 4 else line[1]
				model.custom_size[N] = int(line[3])
		elif line[0] == "joint":
			model.bones.append(IQBone(line[1], int(line[2])))
		elif line[0] == "pq":
			curpose.append(IQPose([float(x) for x in line[1:]]))
		elif line[0] == "pm": raise Exception("pm style poses not implemented yet")
		elif line[0] == "pa": raise Exception("pa style poses not implemented yet")
		elif line[0] == "mesh":
			curmesh = IQMesh(line[1])
			model.meshes.append(curmesh)
		elif line[0] == "material":
			curmesh.material = line[1].split("+")
		elif line[0] == "vp": curmesh.vp.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vn": curmesh.vn.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vt": curmesh.vt.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vc": curmesh.vc.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v0": curmesh.v0.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v1": curmesh.v1.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v2": curmesh.v2.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v3": curmesh.v3.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v4": curmesh.v4.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v5": curmesh.v5.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v6": curmesh.v6.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v7": curmesh.v7.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v8": curmesh.v8.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "v9": curmesh.v9.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vb":
			vbi = []
			vbw = []
			i = 1
			while i + 1 < len(line):
				vbi.append(int(line[i]))
				vbw.append(float(line[i+1]))
				i = i + 2
			curmesh.vbi.append(tuple(vbi))
			curmesh.vbw.append(tuple(vbw))
		elif line[0] == "fm":
			f = [int(x) for x in line[1:]]
			if len(f) > 4:
				print("triangulating n-gon with %d sides %s" % (len(f), f))
				i = 1
				for j in range(2,len(f)):
					curmesh.faces.append((f[0], f[i], f[j]))
					i = j
			else:
				curmesh.faces.append(tuple(f))
		elif line[0] == "fa": raise Exception("fa style faces not implemented yet")
		elif line[0] == "animation":
			curanim = IQAnimation(line[1])
			model.anims.append(curanim)
		elif line[0] == "framerate":
			curanim.framerate = float(line[1])
		elif line[0] == "loop":
			curanim.loop = True
		elif line[0] == "frame":
			curpose = []
			curanim.frames.append(curpose)
	return model

#
# IQM Parser
#

IQM_POSITION = 0
IQM_TEXCOORD = 1
IQM_NORMAL = 2
IQM_BLENDINDEXES = 4
IQM_BLENDWEIGHTS = 5
IQM_COLOR = 6
IQM_CUSTOM = 0x10

IQM_BYTE = 0
IQM_UBYTE = 1
IQM_SHORT = 2
IQM_USHORT = 3
IQM_INT = 4
IQM_UINT = 5
IQM_HALF = 6
IQM_FLOAT = 7
IQM_DOUBLE = 8

IQM_FORMAT = {
	IQM_BYTE: "b",
	IQM_UBYTE: "B",
	IQM_SHORT: "h",
	IQM_USHORT: "H",
	IQM_INT: "i",
	IQM_UINT: "I",
	IQM_FLOAT: "f",
	IQM_DOUBLE: "d"
}

def cstr(text, ofs):
	len = 0
	while text[ofs+len] != 0:
		len += 1
	return str(text[ofs:ofs+len], encoding='utf-8')

def load_iqm_structs(file, fmt, count, offset):
	size = struct.calcsize(fmt)
	file.seek(offset)
	return [struct.unpack(fmt, file.read(size)) for n in range(count)]

def load_iqm(filename):
	name = filename.split("/")[-1].split("\\")[-1].split(".")[0]
	model = IQModel(name)
	file = open(filename, "rb")

	hdr = struct.unpack("<16s27I", file.read(124));
	( magic, version, filesize, flags,
		num_text, ofs_text,
		num_meshes, ofs_meshes,
		num_vertexarrays, num_vertexes, ofs_vertexarrays,
		num_triangles, ofs_triangles, ofs_adjacency,
		num_joints, ofs_joints,
		num_poses, ofs_poses,
		num_anims, ofs_anims,
		num_frames, num_framechannels, ofs_frames, ofs_bounds,
		num_comment, ofs_comment,
		num_extensions, ofs_extensions ) = hdr

	if magic != b"INTERQUAKEMODEL\0":
		raise Exception("Not an IQM file: '%s'", magic)
	if version != 2:
		raise Exception("Not an IQMv2 file.")

	file.seek(ofs_text)
	text = file.read(num_text);

	load_iqm_joints(model, file, text, num_joints, ofs_joints)

	vadata = load_iqm_vertexarrays(model, file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	triangles = load_iqm_structs(file, "<3I", num_triangles, ofs_triangles)
	load_iqm_meshes(model, file, text, num_meshes, ofs_meshes, vadata, triangles)

	poses = load_iqm_structs(file, "<iI20f", num_poses, ofs_poses)
	frames = load_iqm_structs(file, "<" + "H" * num_framechannels, num_frames, ofs_frames)
	load_iqm_anims(model, file, text, num_anims, ofs_anims, poses, frames)

	return model

def load_iqm_joints(model, file, text, num_joints, ofs_joints):
	file.seek(ofs_joints)
	for n in range(num_joints):
		data = struct.unpack("<Ii10f", file.read(12*4))
		name = cstr(text, data[0])
		parent = data[1]
		pose = data[2:12]
		model.bones.append(IQBone(name, parent))
		model.bindpose.append(IQPose(data[2:12]))

def load_iqm_vertexarray(file, type, format, size, offset, count):
	if format not in IQM_FORMAT:
		raise Exception("unknown vertex array data type: %d" % format)
	data = load_iqm_structs(file, "<" + IQM_FORMAT[format] * size, count, offset)
	if type == IQM_BLENDINDEXES:
		return data
	if format == IQM_BYTE: return [ tuple([x/127.0 for x in v]) for v in data ]
	if format == IQM_UBYTE: return [ tuple([x/255.0 for x in v]) for v in data ]
	if format == IQM_SHORT: return [ tuple([x/32767.0 for x in v]) for v in data ]
	if format == IQM_USHORT: return [ tuple([x/65535.0 for x in v]) for v in data ]
	if format == IQM_INT: return [ tuple([x/2147483647.0 for x in v]) for v in data ]
	if format == IQM_UINT: return [ tuple([x/4294967295.0 for x in v]) for v in data ]
	return data

def load_iqm_vertexarrays(model, file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	va = load_iqm_structs(file, "<5I", num_vertexarrays, ofs_vertexarrays)
	model.custom_name = []
	model.custom_size = []
	vadata = {}
	for type, flags, format, size, offset in va:
		if type >= IQM_CUSTOM:
			name = cstr(text, type - IQM_CUSTOM)
			type = len(model.custom_name) + IQM_CUSTOM
			model.custom_name.append(name)
			model.custom_size.append(size)
		vadata[type] = load_iqm_vertexarray(file, type, format, size, offset, num_vertexes)
	return vadata

def copy_iqm_verts(mesh, vadata, first, count):
	for n in range(first, first+count):
		if IQM_POSITION in vadata: mesh.vp.append(vadata[IQM_POSITION][n])
		if IQM_NORMAL in vadata: mesh.vn.append(vadata[IQM_NORMAL][n])
		if IQM_TEXCOORD in vadata: mesh.vt.append(vadata[IQM_TEXCOORD][n])
		if IQM_COLOR in vadata: mesh.vc.append(vadata[IQM_COLOR][n])
		if IQM_BLENDINDEXES in vadata and IQM_BLENDWEIGHTS in vadata:
			vbi = []
			vbw = []
			for y in range(4):
				if vadata[IQM_BLENDWEIGHTS][n][y] > 0:
					vbi.append(vadata[IQM_BLENDINDEXES][n][y])
					vbw.append(vadata[IQM_BLENDWEIGHTS][n][y])
			mesh.vbi.append(tuple(vbi))
			mesh.vbw.append(tuple(vbw))
		if IQM_CUSTOM+0 in vadata: mesh.v0.append(vadata[IQM_CUSTOM+0][n])
		if IQM_CUSTOM+1 in vadata: mesh.v1.append(vadata[IQM_CUSTOM+1][n])
		if IQM_CUSTOM+2 in vadata: mesh.v2.append(vadata[IQM_CUSTOM+2][n])
		if IQM_CUSTOM+3 in vadata: mesh.v3.append(vadata[IQM_CUSTOM+3][n])
		if IQM_CUSTOM+4 in vadata: mesh.v4.append(vadata[IQM_CUSTOM+4][n])
		if IQM_CUSTOM+5 in vadata: mesh.v5.append(vadata[IQM_CUSTOM+5][n])
		if IQM_CUSTOM+6 in vadata: mesh.v6.append(vadata[IQM_CUSTOM+6][n])
		if IQM_CUSTOM+7 in vadata: mesh.v7.append(vadata[IQM_CUSTOM+7][n])
		if IQM_CUSTOM+8 in vadata: mesh.v8.append(vadata[IQM_CUSTOM+8][n])
		if IQM_CUSTOM+9 in vadata: mesh.v9.append(vadata[IQM_CUSTOM+9][n])

def load_iqm_meshes(model, file, text, num_meshes, ofs_meshes, vadata, triangles):
	file.seek(ofs_meshes)
	for n in range(num_meshes):
		name, material, vfirst, vcount, tfirst, tcount = struct.unpack("<6I", file.read(6*4))
		mesh = IQMesh(cstr(text, name))
		mesh.material = cstr(text, material).split("+")
		copy_iqm_verts(mesh, vadata, vfirst, vcount)
		mesh.faces = [(a-vfirst, b-vfirst, c-vfirst) for a,b,c in triangles[tfirst:tfirst+tcount]]
		model.meshes.append(mesh)

def copy_iqm_frame(poselist, frame):
	masktest = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200]
	out = []
	p = 0
	for pose in poselist:
		mask = pose[1]
		choffset = pose[2:2+10]
		chscale = pose[2+10:2+10+10]
		data = [x for x in choffset] # make a copy
		for n in range(10):
			if mask & masktest[n]:
				data[n] += chscale[n] * frame[p]
				p += 1
		out.append(IQPose(data))
	return out

def load_iqm_anims(model, file, text, num_anims, ofs_anims, poses, frames):
	file.seek(ofs_anims)
	for n in range(num_anims):
		name, first, count, framerate, loop = struct.unpack("<3IfI", file.read(5*4))
		anim = IQAnimation(cstr(text, name))
		anim.framerate = framerate
		anim.loop = loop
		anim.frames = [copy_iqm_frame(poses, frame) for frame in frames[first:first+count]]
		model.anims.append(anim)

#
# Create armature from joints and the bind pose.
#
# We preserve matrices and the bone orientations, by
# duplicating the conversion that blender does internally
# to map between bone head/tail/roll and a matrix.
#
# Blender assumes all bones extend in the Y-axis,
# but that's not true for all assets. Depending on
# the bone_axis setting we can rotate the bones from
# extending in the X-axis or Z-axis to the Y-axis,
# or leave them untouched.
#

# Calculate armature space matrices for all bones in a pose

def calc_pose_mats(iqmodel, iqpose, bone_axis):
	loc_pose_mat = [None] * len(iqmodel.bones)
	abs_pose_mat = [None] * len(iqmodel.bones)
	recalc = False

	# convert pose to local matrix and compute absolute matrix
	for n in range(len(iqmodel.bones)):
		iqbone = iqmodel.bones[n]

		pose_pos = iqpose[n].translate
		pose_rot = iqpose[n].rotate
		pose_scale = iqpose[n].scale

		local_pos = Vector(pose_pos)
		local_rot = Quaternion((pose_rot[3], pose_rot[0], pose_rot[1], pose_rot[2]))
		local_scale = Vector(pose_scale)

		mat_pos = Matrix.Translation(local_pos)
		mat_rot = local_rot.to_matrix().to_4x4()
		mat_scale = Matrix.Scale(local_scale.x, 3).to_4x4()
		loc_pose_mat[n] = matmul(matmul(mat_pos, mat_rot), mat_scale)

		if iqbone.parent >= 0:
			abs_pose_mat[n] = matmul(abs_pose_mat[iqbone.parent], loc_pose_mat[n])
		else:
			abs_pose_mat[n] = loc_pose_mat[n]

	# Remove negative scaling from bones.
	# Due to numerical instabilities in blender's matrix <-> head/tail/roll math
	# this isn't always stable when the bones are in the X axis. If the bones
	# end up rotated 90 degrees from what they should be, that's the reason.
	for n in range(len(iqmodel.bones)):
		if abs_pose_mat[n].is_negative:
			if not hasattr(iqmodel, 'abs_bind_mat'):
				print("warning: removing negative scale in bone", iqmodel.bones[n].name)
			abs_pose_mat[n] = matmul(abs_pose_mat[n], Matrix.Scale(-1, 4))
			recalc = True

	# flip bone axis (and recompute local matrix if needed)
	if bone_axis == 'X':
		axis_flip = Matrix.Rotation(math.radians(-90), 4, 'Z')
		abs_pose_mat = [matmul(m, axis_flip) for m in abs_pose_mat]
		recalc = True
	if bone_axis == 'Z':
		axis_flip = Matrix.Rotation(math.radians(-90), 4, 'X')
		abs_pose_mat = [matmul(m, axis_flip) for m in abs_pose_mat]
		recalc = True

	if recalc:
		inv_pose_mat = [m.inverted() for m in abs_pose_mat]
		for n in range(len(iqmodel.bones)):
			iqbone = iqmodel.bones[n]
			if iqbone.parent >= 0:
				loc_pose_mat[n] = matmul(inv_pose_mat[iqbone.parent], abs_pose_mat[n])
			else:
				loc_pose_mat[n] = abs_pose_mat[n]

	return loc_pose_mat, abs_pose_mat

def make_armature(iqmodel, bone_axis):

	if len(iqmodel.bones) == 0: return None
	if len(iqmodel.bindpose) != len(iqmodel.bones): return None

	print("importing armature with %d bones" % len(iqmodel.bones))

	# Need to be in object mode before we can enter edit mode; this throws if
	# we're already in object mode
	try:
		bpy.ops.object.mode_set(mode="OBJECT")
	except RuntimeError:
		pass

	bpy.ops.object.add(type="ARMATURE", enter_editmode=True)
	obj, amt = bpy.context.object, bpy.context.object.data
	amt.name = iqmodel.name
	obj.name = iqmodel.name + ".amt"

	loc_bind_mat, abs_bind_mat = calc_pose_mats(iqmodel, iqmodel.bindpose, bone_axis)
	iqmodel.abs_bind_mat = abs_bind_mat
	iqmodel.loc_bind_mat = loc_bind_mat
	iqmodel.inv_loc_bind_mat = [m.inverted() for m in loc_bind_mat]

	for n in range(len(iqmodel.bones)):
		iqbone = iqmodel.bones[n]

		bone = amt.edit_bones.new(iqbone.name)
		parent = None
		if iqbone.parent >= 0:
			parent = amt.edit_bones[iqbone.parent]
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

#
# Strike a pose.
#

def make_pose(iqmodel, frame, amtobj, bone_axis, tick):
	loc_pose_mat, _ = calc_pose_mats(iqmodel, frame, bone_axis)
	for n in range(len(iqmodel.bones)):
		name = iqmodel.bones[n].name
		pose_bone = amtobj.pose.bones[name]
		pose_bone.matrix_basis = matmul(iqmodel.inv_loc_bind_mat[n], loc_pose_mat[n])
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

#
# Create simple material by looking at the magic words.
# Use the last word as a texture name by appending ".png".
#

images = {}

def make_material(iqmaterial, dir):
	print("importing material", iqmaterial)

	matname = ";".join(iqmaterial)
	texname = iqmaterial[-1]

	# reuse materials if possible
	if matname in bpy.data.materials:
		return bpy.data.materials[matname], images.get(texname)

	twosided = 'twosided' in iqmaterial
	alphatest = 'alphatest' in iqmaterial
	unlit = 'unlit' in iqmaterial

	if not texname in images:
		print("load image", texname)
		images[texname] = load_image("textures/" + texname + ".png", dir, place_holder=True, recursive=True)
	image = images[texname]

	if texname in bpy.data.textures:
		tex = bpy.data.textures[texname]
	else:
		tex = bpy.data.textures.new(texname, type = 'IMAGE')
		tex.image = image
		tex.use_alpha = True

	mat = bpy.data.materials.new(matname)
	if bpy.app.version < (2, 80, 0):
		mat.diffuse_intensity = 1
		mat.specular_intensity = 0
		mat.alpha = 0.0

		texslot = mat.texture_slots.add()
		texslot.texture = tex
		texslot.texture_coords = 'UV'
		texslot.uv_layer = "UVMap"
		texslot.use_map_color_diffuse = True
		texslot.use_map_alpha = True

		if unlit: mat.use_shadeless = True
		mat.use_transparency = True

		# blender game engine
		mat.game_settings.use_backface_culling = not twosided
		mat.game_settings.alpha_blend = 'CLIP'
		if alphatest and unlit: mat.game_settings.alpha_blend = 'ADD'

	else:
		mat.use_nodes = True
		prinnode = mat.node_tree.nodes['Principled BSDF']
		texnode = mat.node_tree.nodes.new('ShaderNodeTexImage')
		texnode.location = (-280, 280)
		texnode.image = image
		mat.node_tree.links.new(texnode.outputs[0], prinnode.inputs['Base Color'])
		prinnode.inputs['Roughness'].default_value = 1

		mat.blend_method = 'CLIP'

	# return the material (and image so we can link the uvlayer faces)
	return mat, image

#
# Create mesh object with normals, texcoords, vertex colors,
# and an armature modifier if the model is skinned.
#

def gather_meshes(iqmodel):
	meshes = {}
	for mesh in iqmodel.meshes:
		if mesh.name not in meshes:
			meshes[mesh.name] = [ mesh ]
		else:
			meshes[mesh.name] += [ mesh ]
	return meshes

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

def make_mesh_data(iqmodel, name, meshes, amtobj, dir):
	print("importing mesh", name, "with", len(meshes), "parts")

	mesh = bpy.data.meshes.new(name)
	obj = bpy.data.objects.new(name, mesh)
	link_object(obj)

	# Set the mesh to single-sided to spot normal errors
	mesh.use_mirror_topology = False

	has_vn = len(iqmodel.meshes[0].vn) > 0
	has_vt = len(iqmodel.meshes[0].vt) > 0
	has_vc = len(iqmodel.meshes[0].vc) > 0
	has_vb = len(iqmodel.meshes[0].vbi) > 0 and len(iqmodel.meshes[0].vbw) == len(iqmodel.meshes[0].vbi)
	has_v0 = len(iqmodel.meshes[0].v0) > 0
	has_v1 = len(iqmodel.meshes[0].v1) > 0
	has_v2 = len(iqmodel.meshes[0].v2) > 0
	has_v3 = len(iqmodel.meshes[0].v3) > 0
	has_v4 = len(iqmodel.meshes[0].v4) > 0
	has_v5 = len(iqmodel.meshes[0].v5) > 0
	has_v6 = len(iqmodel.meshes[0].v6) > 0
	has_v7 = len(iqmodel.meshes[0].v7) > 0
	has_v8 = len(iqmodel.meshes[0].v8) > 0
	has_v9 = len(iqmodel.meshes[0].v9) > 0

	# Flip winding and UV coords.

	for iqmesh in meshes:
		iqmesh.faces = [x[::-1] for x in iqmesh.faces]
		iqmesh.vt = [(u,1-v) for (u,v) in iqmesh.vt]

	# Blender has texcoords and colors on faces rather than vertices.
	# Create material slots for all materials used.
	# Create new vertices from unique vp/vn/vb sets (vertex data).
	# Create new faces which index these new vertices, and has associated face data.

	vertex_map = {}

	new_f = []
	new_ft = []
	new_fc = []
	new_fm_m = []
	new_fm_i = []

	new_vp = []
	new_vn = []
	new_vbi = []
	new_vbw = []
	new_v0 = []
	new_v1 = []
	new_v2 = []
	new_v3 = []
	new_v4 = []
	new_v5 = []
	new_v6 = []
	new_v7 = []
	new_v8 = []
	new_v9 = []

	for iqmesh in meshes:
		material, image = make_material(iqmesh.material, dir)
		if material.name not in mesh.materials:
			mesh.materials.append(material)
		material_index = mesh.materials.find(material.name)

		for iqface in iqmesh.faces:
			f = []
			ft = []
			fc = []
			for iqvert in iqface:
				vp = iqmesh.vp[iqvert]
				vn = iqmesh.vn[iqvert] if has_vn else None
				vbi = iqmesh.vbi[iqvert] if has_vb else None
				vbw = iqmesh.vbw[iqvert] if has_vb else None
				v0 = iqmesh.v0[iqvert] if has_v0 else None
				v1 = iqmesh.v1[iqvert] if has_v1 else None
				v2 = iqmesh.v2[iqvert] if has_v2 else None
				v3 = iqmesh.v3[iqvert] if has_v3 else None
				v4 = iqmesh.v4[iqvert] if has_v4 else None
				v5 = iqmesh.v5[iqvert] if has_v5 else None
				v6 = iqmesh.v6[iqvert] if has_v6 else None
				v7 = iqmesh.v7[iqvert] if has_v7 else None
				v8 = iqmesh.v8[iqvert] if has_v8 else None
				v9 = iqmesh.v9[iqvert] if has_v9 else None
				vertex = (vp, vn, vbi, vbw, v0, v1, v2, v3, v4, v5, v6, v7, v8, v9)
				if not vertex in vertex_map:
					vertex_map[vertex] = len(new_vp)
					new_vp.append(vp)
					new_vn.append(vn)
					new_vbi.append(vbi)
					new_vbw.append(vbw)
					new_v0.append(v0)
					new_v1.append(v1)
					new_v2.append(v2)
					new_v3.append(v3)
					new_v4.append(v4)
					new_v5.append(v5)
					new_v6.append(v6)
					new_v7.append(v7)
					new_v8.append(v8)
					new_v9.append(v9)
				f.append(vertex_map[vertex])
				ft.append(iqmesh.vt[iqvert] if has_vt else None)
				fc.append(iqmesh.vc[iqvert] if has_vc else None)
			f, ft, fc = reorder(f, ft, fc)  # XXX: do we need this?
			if isdegenerate(f):
				print("degenerate face", iqface, f)
				continue
			# XXX: what about duplicate faces?
			new_f.append(f)
			new_ft.append(ft)
			new_fc.append(fc)
			new_fm_m.append(material_index)
			new_fm_i.append(image)

	print("\tcollected %d vertices and %d faces" % (len(new_vp), len(new_f)))

	# Create mesh vertex and face data

	mesh.from_pydata(new_vp, [], new_f)
	mesh.validate()

	# Set up UV and Color layers

	if has_vt:
		if getattr(mesh.uv_layers, 'new', None) is not None:
			uvtexture = None
			uvlayer = mesh.uv_layers.new()
		else:
			uvtexture = mesh.uv_textures.new()
			uvlayer = mesh.uv_layers[0]
	clayer = mesh.vertex_colors.new() if has_vc else None

	# Define function for switching to RGB/RGBA as appropriate

	if has_vc:
		num_colors = len(new_fc[0][0])
		num_blender_colors = len(clayer.data[0].color)
		if num_colors == 3 and num_blender_colors == 4:
			def color(rgb): return rgb + [1]
		elif num_colors == 4 and num_blender_colors == 3:
			def color(rgba): return rgba[0:3]
		elif num_colors == num_blender_colors:
			def color(c): return c

	for poly_i, poly in enumerate(mesh.polygons):
		poly.use_smooth = True
		poly.material_index = new_fm_m[poly_i]
		if uvlayer:
			for i, loop_i in enumerate(poly.loop_indices):
				uvlayer.data[loop_i].uv = new_ft[poly_i][i]
		if clayer:
			for i, loop_i in enumerate(poly.loop_indices):
				clayer.data[loop_i].color = color(new_fc[poly_i][i])

	if has_vt and uvtexture:
		for poly_i, poly in enumerate(mesh.polygons):
			uvtexture.data[poly_i].image = new_fm_i[poly_i]

	# Vertex groups and armature modifier for skinning

	if has_vb and amtobj:
		for iqbone in iqmodel.bones:
			obj.vertex_groups.new(name=iqbone.name)

		for vgroup in obj.vertex_groups:
			for v, vbi in enumerate(new_vbi):
				for i, bi in enumerate(vbi):
					bw = new_vbw[v][i]
					if bi == vgroup.index:
						vgroup.add([v], bw, 'REPLACE')

		mod = obj.modifiers.new("Armature", 'ARMATURE')
		mod.object = amtobj
		mod.use_vertex_groups = True

	# Vertex groups for custom attributes

	def make_custom_vgroup(obj, name, size, vdata):
		print("importing custom attribute as vertex group", name)
		if size == 1:
			xg = obj.vertex_groups.new(name=name)
			for i, v in enumerate(vdata):
				xg.add([i], v[0], 'REPLACE')
		if size == 2:
			xg = obj.vertex_groups.new(name=name + ".x")
			yg = obj.vertex_groups.new(name=name + ".y")
			for i, v in enumerate(vdata):
				xg.add([i], v[0], 'REPLACE')
				yg.add([i], v[1], 'REPLACE')
		if size == 3:
			xg = obj.vertex_groups.new(name=name + ".x")
			yg = obj.vertex_groups.new(name=name + ".y")
			zg = obj.vertex_groups.new(name=name + ".z")
			for i, v in enumerate(vdata):
				xg.add([i], v[0], 'REPLACE')
				yg.add([i], v[1], 'REPLACE')
				zg.add([i], v[2], 'REPLACE')
		if size == 4:
			xg = obj.vertex_groups.new(name=name + ".x")
			yg = obj.vertex_groups.new(name=name + ".y")
			zg = obj.vertex_groups.new(name=name + ".z")
			wg = obj.vertex_groups.new(name=name + ".z")
			for i, v in enumerate(vdata):
				xg.add([i], v[0], 'REPLACE')
				yg.add([i], v[1], 'REPLACE')
				zg.add([i], v[2], 'REPLACE')
				wg.add([i], v[3], 'REPLACE')

	if has_v0: make_custom_vgroup(obj, iqmodel.custom_name[0], iqmodel.custom_size[0], new_v0)
	if has_v1: make_custom_vgroup(obj, iqmodel.custom_name[1], iqmodel.custom_size[1], new_v1)
	if has_v2: make_custom_vgroup(obj, iqmodel.custom_name[2], iqmodel.custom_size[2], new_v2)
	if has_v3: make_custom_vgroup(obj, iqmodel.custom_name[3], iqmodel.custom_size[3], new_v3)
	if has_v4: make_custom_vgroup(obj, iqmodel.custom_name[4], iqmodel.custom_size[4], new_v4)
	if has_v5: make_custom_vgroup(obj, iqmodel.custom_name[5], iqmodel.custom_size[5], new_v5)
	if has_v6: make_custom_vgroup(obj, iqmodel.custom_name[6], iqmodel.custom_size[6], new_v6)
	if has_v7: make_custom_vgroup(obj, iqmodel.custom_name[7], iqmodel.custom_size[7], new_v7)
	if has_v8: make_custom_vgroup(obj, iqmodel.custom_name[8], iqmodel.custom_size[8], new_v8)
	if has_v9: make_custom_vgroup(obj, iqmodel.custom_name[9], iqmodel.custom_size[9], new_v9)

	# Update mesh polygons from tessfaces

	mesh.update()

	# Must set normals after mesh.update() or they will be recalculated.
	mesh.vertices.foreach_set("normal", unpack_list(new_vn))

	return obj

#
# Import armature and meshes.
# If there is an armature, parent the meshes to it.
# Otherwise create an empty object and group the meshes in that.
#

def make_model(iqmodel, bone_axis, dir):
	print("importing model", iqmodel.name)

	for obj in bpy.context.scene.objects:
		select_ob(obj, state=False)

	group = make_group(iqmodel.name)

	amtobj = make_armature(iqmodel, bone_axis)
	meshes = gather_meshes(iqmodel)

	if amtobj:
		rootobj = amtobj
	elif meshes:
		bpy.ops.object.empty_add()
		rootobj = bpy.context.object
		rootobj.name = iqmodel.name

	group.objects.link(rootobj)
	select_ob(rootobj)

	for name in meshes:
		meshobj = make_mesh_data(iqmodel, name, meshes[name], amtobj, dir)
		meshobj.parent = rootobj
		group.objects.link(meshobj)
		select_ob(meshobj)

	if len(iqmodel.anims) > 0:
		make_actions(iqmodel, amtobj, bone_axis)

	print("all done.")

def import_iqm(filename, bone_axis='Y'):
	if filename.endswith(".iqm") or filename.endswith(".IQM"):
		iqmodel = load_iqm(filename)
	else:
		iqmodel = load_iqe(filename)
	dir = os.path.dirname(filename)
	make_model(iqmodel, bone_axis, dir)
	bpy.ops.screen.frame_jump()

#
# Register addon
#

class ImportIQM(bpy.types.Operator, ImportHelper):
	bl_idname = "import.iqm"
	bl_label = "Import IQM or IQE"

	filename_ext = ".iqe, .iqm"
	filter_glob = StringProperty(default="*.iq[em]", options={'HIDDEN'})
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
		import_iqm(self.properties.filepath, self.bone_axis)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ImportIQM.bl_idname, text="Inter-Quake Model (.iqm, .iqe)")

def register():
    if bpy.app.version >= (2, 80, 0):
        bpy.utils.register_class(ImportIQM)
        bpy.types.TOPBAR_MT_file_import.append(menu_func)
    else:
        bpy.utils.register_module(__name__)
        bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
    if bpy.app.version >= (2, 80, 0):
        bpy.types.TOPBAR_MT_file_import.remove(menu_func)
        bpy.utils.unregister_class(ImportIQM)
    else:
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
	import_iqm(input)
	print("Saving", output)
	bpy.ops.wm.save_mainfile(filepath=output, check_existing=False)

def batch_many(input_list):
	batch_zap()
	output = "output.blend"
	for input in input_list:
		import_iqm(input)
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
