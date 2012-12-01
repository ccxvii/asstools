# Importer for Inter-Quake Model / Export formats

bl_info = {
	"name": "Import Inter-Quake Model (.iqm, .iqe)",
	"description": "Import Inter-Quake Model.",
	"author": "Tor Andersson",
	"version": (2012, 12, 1),
	"blender": (2, 6, 4),
	"location": "File > Import > Inter-Quake Model",
	"wiki_url": "http://github.com/ccxvii/asstools",
	"category": "Import-Export",
}

import bpy, math, shlex, struct, os, sys

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

#
# Inter-Quake Model structs
#

class IQMesh:
	def __init__(self, name):
		self.name = name
		self.material = None
		self.faces = []
		self.positions = []
		self.normals = []
		self.texcoords = []
		self.colors = []
		self.blends = []

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
		elif line[0] == "vp":
			x,y,z = float(line[1]), float(line[2]), float(line[3])
			curmesh.positions.append((x,y,z))
		elif line[0] == "vt":
			u,v = float(line[1]), float(line[2])
			curmesh.texcoords.append((u,v))
		elif line[0] == "vn":
			x,y,z = float(line[1]), float(line[2]), float(line[3])
			curmesh.normals.append((x,y,z))
		elif line[0] == "vc":
			r,g,b = float(line[1]), float(line[2]), float(line[3])
			curmesh.colors.append((r,g,b))
		elif line[0] == "vb":
			curmesh.blends.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "fm":
			curmesh.faces.append(tuple([int(x) for x in line[1:]]))
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

	valist = load_iqm_vertexarrays(file, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	triangles = load_iqm_structs(file, "<3I", num_triangles, ofs_triangles)
	load_iqm_meshes(model, file, text, num_meshes, ofs_meshes, valist, triangles)

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

def load_iqm_vertexarray(file, format, size, offset, count):
	if format not in IQM_FORMAT:
		raise Exception("unknown vertex array data type: %d" % format)
	return load_iqm_structs(file, "<" + IQM_FORMAT[format] * size, count, offset)

def load_iqm_vertexarrays(file, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	va = load_iqm_structs(file, "<5I", num_vertexarrays, ofs_vertexarrays)
	valist = {}
	for type, flags, format, size, offset in va:
		valist[type] = load_iqm_vertexarray(file, format, size, offset, num_vertexes)
	return valist

def copy_iqm_verts(mesh, valist, first, count):
	for n in range(first, first+count):
		if IQM_POSITION in valist:
			mesh.positions.append(valist[IQM_POSITION][n])
		if IQM_NORMAL in valist:
			mesh.normals.append(valist[IQM_NORMAL][n])
		if IQM_TEXCOORD in valist:
			mesh.texcoords.append(valist[IQM_TEXCOORD][n])
		if IQM_COLOR in valist:
			r, g, b, a = valist[IQM_COLOR][n]
			mesh.colors.append((r/255.0, g/255.0, b/255.0, a/255.0))
		if IQM_BLENDINDEXES in valist and IQM_BLENDWEIGHTS in valist:
			vb = []
			for y in range(4):
				if valist[IQM_BLENDWEIGHTS][n][y] > 0:
					vb.append(valist[IQM_BLENDINDEXES][n][y])
					vb.append(valist[IQM_BLENDWEIGHTS][n][y]/255.0)
			mesh.blends.append(tuple(vb))

def load_iqm_meshes(model, file, text, num_meshes, ofs_meshes, valist, triangles):
	file.seek(ofs_meshes)
	for n in range(num_meshes):
		name, material, vfirst, vcount, tfirst, tcount = struct.unpack("<6I", file.read(6*4))
		mesh = IQMesh(cstr(text, name))
		mesh.material = cstr(text, material).split("+")
		copy_iqm_verts(mesh, valist, vfirst, vcount)
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
		loc_pose_mat[n] = mat_pos * mat_rot * mat_scale

		if iqbone.parent >= 0:
			abs_pose_mat[n] = abs_pose_mat[iqbone.parent] * loc_pose_mat[n]
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
		for n in range(len(iqmodel.bones)):
			iqbone = iqmodel.bones[n]
			if iqbone.parent >= 0:
				loc_pose_mat[n] = inv_pose_mat[iqbone.parent] * abs_pose_mat[n]
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
		pose_bone.matrix_basis = iqmodel.inv_loc_bind_mat[n] * loc_pose_mat[n]
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='location')
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='rotation_quaternion')
		pose_bone.keyframe_insert(group=name, frame=tick, data_path='scale')

def make_anim(iqmodel, anim, amtobj, bone_axis):
	print("importing animation %s with %d frames" % (anim.name, len(anim.frames)))
	action = bpy.data.actions.new(anim.name)
	action.use_fake_user = True
	amtobj.animation_data.action = action
	for n in range(len(anim.frames)):
		make_pose(iqmodel, anim.frames[n], amtobj, bone_axis, n)
	return action

def make_actions(iqmodel, amtobj, bone_axis, use_nla_tracks):
	bpy.context.scene.frame_start = 0
	amtobj.animation_data_create()
	if use_nla_tracks:
		track = amtobj.animation_data.nla_tracks.new()
		track.name = "All"
		n = 0
	for anim in iqmodel.anims:
		action = make_anim(iqmodel, anim, amtobj, bone_axis)
		if use_nla_tracks:
			track.strips.new(action.name, n, action)
			n = track.strips[-1].frame_end + 1
	if use_nla_tracks:
		amtobj.animation_data.action = None
		bpy.context.scene.frame_end = n - 1

#
# Create simple material by looking at the magic words.
# Use the last word as a texture name by appending ".png".
#

images = {}

def make_material(iqmaterial, dir):
	print("importing material", iqmaterial)

	matname = "+".join(iqmaterial)
	texname = iqmaterial[-1]

	# reuse materials if possible
	if matname in bpy.data.materials:
		return bpy.data.materials[matname], images[texname]

	twosided = 'twosided' in iqmaterial
	alphatest = 'alphatest' in iqmaterial
	unlit = 'unlit' in iqmaterial

	if not texname in images:
		print("load image", texname)
		images[texname] = load_image("textures/" + texname + ".png", dir, place_holder=True, recursive=True)
		images[texname].use_premultiply = True
	image = images[texname]

	if texname in bpy.data.textures:
		tex = bpy.data.textures[texname]
	else:
		tex = bpy.data.textures.new(texname, type = 'IMAGE')
		tex.image = image
		tex.use_alpha = True

	mat = bpy.data.materials.new(matname)
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

def make_mesh_data(iqmodel, name, meshes, amtobj, dir):
	print("importing mesh", name, "with", len(meshes), "parts")

	mesh = bpy.data.meshes.new(name)
	obj = bpy.data.objects.new(name, mesh)
	bpy.context.scene.objects.link(obj)
	bpy.context.scene.objects.active = obj

	# Set the mesh to single-sided to spot normal errors
	mesh.show_double_sided = False

	has_normals = len(iqmodel.meshes[0].normals) > 0
	has_texcoords = len(iqmodel.meshes[0].texcoords) > 0
	has_colors = len(iqmodel.meshes[0].colors) > 0
	has_blends = len(iqmodel.meshes[0].blends) > 0

	# Flip winding and UV coords.

	for iqmesh in meshes:
		iqmesh.faces = [x[::-1] for x in iqmesh.faces]
		iqmesh.texcoords = [(u,1-v) for (u,v) in iqmesh.texcoords]

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
	new_vb = []

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
				vp = iqmesh.positions[iqvert]
				vn = iqmesh.normals[iqvert] if has_normals else (1,0,0)
				vb = iqmesh.blends[iqvert] if has_blends else (0,1)
				vertex = (vp, vn, vb)
				if not vertex in vertex_map:
					vertex_map[vertex] = len(new_vp)
					new_vp.append(vp)
					new_vn.append(vn)
					new_vb.append(vb)
				f.append(vertex_map[vertex])
				ft.append(iqmesh.texcoords[iqvert] if has_texcoords else None)
				fc.append(iqmesh.colors[iqvert] if has_colors else None)
			f, ft, fc = reorder(f, ft, fc)
			new_f.append(f)
			new_ft.append(ft)
			new_fc.append(fc)
			new_fm_m.append(material_index)
			new_fm_i.append(image)

	print("\tcollected %d vertices and %d faces" % (len(new_vp), len(new_f)))

	# Create mesh vertex and face data

	mesh.vertices.add(len(new_vp))
	mesh.vertices.foreach_set("co", unpack_list(new_vp))

	mesh.tessfaces.add(len(new_f))
	mesh.tessfaces.foreach_set("vertices_raw", unpack_face_list(new_f))

	# Set up UV and Color layers

	uvlayer = mesh.tessface_uv_textures.new() if has_texcoords else None
	clayer = mesh.tessface_vertex_colors.new() if has_colors else None

	for i, face in enumerate(mesh.tessfaces):
		face.use_smooth = True
		face.material_index = new_fm_m[i]
		if uvlayer:
			uvlayer.data[i].uv1 = new_ft[i][0]
			uvlayer.data[i].uv2 = new_ft[i][1]
			uvlayer.data[i].uv3 = new_ft[i][2]
			uvlayer.data[i].image = new_fm_i[i]
		if clayer:
			clayer.data[i].color1 = new_fc[0]
			clayer.data[i].color2 = new_fc[1]
			clayer.data[i].color3 = new_fc[2]

	# Vertex groups and armature modifier for skinning

	if has_blends and amtobj:
		for iqbone in iqmodel.bones:
			obj.vertex_groups.new(iqbone.name)

		for vgroup in obj.vertex_groups:
			for v, blend in enumerate(new_vb):
				for k in range(0, len(blend), 2):
					bi = blend[k]
					bw = blend[k+1]
					if bi == vgroup.index:
						vgroup.add([v], bw, 'ADD')

		mod = obj.modifiers.new("Armature", 'ARMATURE')
		mod.object = amtobj
		mod.use_vertex_groups = True

	# Update mesh polygons from tessfaces

	mesh.update()

	return obj

#
# Import armature and meshes.
# If there is an armature, parent the meshes to it.
# Otherwise create an empty object and group the meshes in that.
#

def make_model(iqmodel, bone_axis, dir, use_nla_tracks = False):
	print("importing model", iqmodel.name)

	for obj in bpy.context.scene.objects:
		obj.select = False

	group = bpy.data.groups.new(iqmodel.name)

	amtobj = make_armature(iqmodel, bone_axis)
	if amtobj:
		group.objects.link(amtobj)

	meshes = gather_meshes(iqmodel)
	for name in meshes:
		meshobj = make_mesh_data(iqmodel, name, meshes[name], amtobj, dir)
		if amtobj:
			meshobj.parent = amtobj
		group.objects.link(meshobj)

	if len(iqmodel.anims) > 0:
		make_actions(iqmodel, amtobj, bone_axis, use_nla_tracks)

	print("all done.")

def import_iqm(filename, bone_axis='Y', use_nla_tracks=False):
	if filename.endswith(".iqm") or filename.endswith(".IQM"):
		iqmodel = load_iqm(filename)
	else:
		iqmodel = load_iqe(filename)
	dir = os.path.dirname(filename)
	make_model(iqmodel, bone_axis, dir, use_nla_tracks)
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

	use_nla_tracks = BoolProperty(name="Create NLA track",
			description="Create NLA track containing all actions",
			default=False)

	def execute(self, context):
		import_iqm(self.properties.filepath, self.bone_axis, self.properties.use_nla_tracks)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ImportIQM.bl_idname, text="Inter-Quake Model (.iqm, .iqe)")

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
		batch(sys.argv[-1])
	elif len(sys.argv) > 4 and sys.argv[4] == '--':
		batch_many(sys.argv[5:])
