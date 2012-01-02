# Importer for Inter-Quake Model / Export formats

bl_info = {
	"name": "Import Inter-Quake Model (.iqm, .iqe)",
	"author": "Tor Andersson",
	"version": (0, 1),
	"blender": (2, 6, 0),
	"location": "File > Import > Inter-Quake Model",
	"description": "Import Inter-Quake model with vertex colors and armature.",
	"category": "Import-Export",
}

import bpy, math, shlex, struct, os

from bpy.props import *
from bpy_extras.io_utils import ImportHelper
from bpy_extras.image_utils import load_image
from mathutils import Matrix, Quaternion, Vector

def abbr(name):
	BLENDER_MAX_NAME_LEN = 21
	if len(name) > BLENDER_MAX_NAME_LEN:
		name = name[-BLENDER_MAX_NAME_LEN:]
	return name

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
	vec = mat[1]
	vecmat = vec_roll_to_mat3(mat[1], 0)
	vecmatinv = vecmat.copy()
	vecmatinv.invert()
	rollmat = vecmatinv * mat
	roll = math.atan2(rollmat[2][0], rollmat[2][2])
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
			curmesh.blends.append([float(x) for x in line[1:]])
		elif line[0] == "fm":
			a,b,c = int(line[1]), int(line[2]), int(line[3])
			curmesh.faces.append((a,b,c))
		elif line[0] == "fa": raise Exception("fa style faces not implemented yet")
		elif line[0] == "animation":
			curanim = IQAnimation(line[1])
			model.anims.append(curanim)
		elif line[0] == "framerate":
			curanim.framerate = int(line[1])
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
			mesh.blends.append(vb)

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

	# flip bone axis (and recompute local matrix if needed)
	if bone_axis == 'X': axis_flip = Matrix.Rotation(math.radians(-90), 4, 'Z')
	if bone_axis == 'Z': axis_flip = Matrix.Rotation(math.radians(-90), 4, 'X')
	if bone_axis != 'Y':
		abs_pose_mat = [m * axis_flip for m in abs_pose_mat]
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

	amt = bpy.data.armatures.new("Skeleton")
	obj = bpy.data.objects.new(abbr(iqmodel.name), amt)
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
		pose_bone = amtobj.pose.bones[n]
		pose_bone.matrix_basis = iqmodel.inv_loc_bind_mat[n] * loc_pose_mat[n]
		pose_bone.keyframe_insert(data_path='location', frame=tick)
		pose_bone.keyframe_insert(data_path='rotation_quaternion', frame=tick)
		#pose_bone.keyframe_insert(data_path='scale', frame=tick)

def make_anim(iqmodel, anim, amtobj, bone_axis):
	print("importing animation %s with %d frames" % (anim.name, len(anim.frames)))
	bpy.context.scene.render.fps = anim.framerate
	amtobj.animation_data_create()
	action = bpy.data.actions.new(abbr(anim.name))
	amtobj.animation_data.action = action
	for n in range(len(anim.frames)):
		make_pose(iqmodel, anim.frames[n], amtobj, bone_axis, n)

#
# Create simple material by looking at the magic words.
# Use the last word as a texture name by appending ".png".
#

images = {}

def make_material(mesh, iqmaterial, dir):
	matname = "+".join(iqmaterial)
	texname = iqmaterial[-1]
	if not "." in texname: texname += ".png"

	print("importing material", matname)

	twosided = 'twosided' in iqmaterial
	alphatest = 'alphatest' in iqmaterial
	alphagloss = 'alphagloss' in iqmaterial
	unlit = 'unlit' in iqmaterial

	if not texname in images:
		images[texname] = load_image(texname, dir, place_holder=True, recursive=True)
	image = images[texname]

	# if image: image.use_premultiply = True

	tex = bpy.data.textures.new(matname, type = 'IMAGE')
	tex.image = image
	tex.use_alpha = True

	mat = bpy.data.materials.new(matname)
	mat.specular_intensity = 0

	matslot = mat.texture_slots.add()
	matslot.texture = tex
	matslot.texture_coords = 'UV'
	matslot.use_map_color_diffuse = True
	matslot.use_map_alpha = True

	mesh.show_double_sided = twosided

	if unlit:
		mat.use_shadeless = True

	if alphatest:
		mat.use_transparency = True
		mat.alpha = 0.0

	if alphagloss:
		matslot.use_map_specular = True

	# Vertices are linked to material 0 by default,
	# so this should be enough.
	mesh.materials.append(mat)

	# return the image so we can link the uvlayer faces
	return image

#
# Create mesh object with normals, texcoords, vertex colors,
# and an armature modifier if the model is skinned.
#

def make_mesh(iqmodel, iqmesh, amtobj, dir):
	print("importing mesh %s with %d vertices and %d faces" %
		(iqmesh.name, len(iqmesh.positions), len(iqmesh.faces)))

	mesh = bpy.data.meshes.new(abbr(iqmesh.name))
	obj = bpy.data.objects.new(abbr(iqmesh.name), mesh)
	bpy.context.scene.objects.link(obj)
	bpy.context.scene.objects.active = obj

	# Flip winding and UV coords

	iqmesh.faces = [(c,b,a) for (a,b,c) in iqmesh.faces]
	iqmesh.texcoords = [(u,1-v) for (u,v) in iqmesh.texcoords]

	# Vertex positions and faces

	mesh.from_pydata(iqmesh.positions, [], iqmesh.faces)

	for face in mesh.faces:
		face.use_smooth = True

	# Vertex normals.
	# Blender recreates normals for display when entering edit mode,
	# but does seem to preserve the original normals when saving.

	if len(iqmesh.normals) == len(iqmesh.positions):
		for n in range(len(iqmesh.normals)):
			mesh.vertices[n].normal = iqmesh.normals[n]

	# Texture coords

	if len(iqmesh.texcoords) == len(iqmesh.positions):
		uvlayer = mesh.uv_textures.new()
		for n in range(len(mesh.faces)):
			a, b, c = mesh.faces[n].vertices
			data = uvlayer.data[n]
			data.uv1 = iqmesh.texcoords[a]
			data.uv2 = iqmesh.texcoords[b]
			data.uv3 = iqmesh.texcoords[c]

	# Vertex colors

	if len(iqmesh.colors) == len(iqmesh.positions):
		clayer = mesh.vertex_colors.new()
		for n in range(len(mesh.faces)):
			a, b, c = mesh.faces[n].vertices
			data = clayer.data[n]
			data.color1 = iqmesh.colors[a][0:3]
			data.color2 = iqmesh.colors[b][0:3]
			data.color3 = iqmesh.colors[c][0:3]

	# Vertex groups for skinning

	if len(iqmesh.blends) == len(iqmesh.positions) and amtobj:
		for iqbone in iqmodel.bones:
			obj.vertex_groups.new(iqbone.name)
		for vgroup in obj.vertex_groups:
			for n in range(len(iqmesh.blends)):
				blend = iqmesh.blends[n]
				for k in range(0, len(blend), 2):
					bi = blend[k]
					bw = blend[k+1]
					if bi == vgroup.index:
						vgroup.add([n], bw, 'ADD')
		mod = obj.modifiers.new("Skin", 'ARMATURE')
		mod.object = amtobj
		mod.use_bone_envelopes = False
		mod.use_vertex_groups = True

	# Material

	image = make_material(mesh, iqmesh.material, dir)

	# update faces to point to the texture image
	if len(iqmesh.texcoords) == len(iqmesh.positions):
		for data in uvlayer.data:
			data.image = image

	# what does this do? without it we don't get orange outline.
	mesh.update()

	return obj

#
# Import armature and meshes.
# If there is an armature, parent the meshes to it.
# Otherwise create an empty object and group the meshes in that.
#

def make_model(iqmodel, bone_axis, dir):
	print("importing model", iqmodel.name)

	for obj in bpy.context.scene.objects:
		obj.select = False

	amtobj = make_armature(iqmodel, bone_axis)
	if not amtobj:
		grpobj = bpy.data.objects.new(abbr(iqmodel.name), None)
		bpy.context.scene.objects.link(grpobj)

	for iqmesh in iqmodel.meshes:
		meshobj = make_mesh(iqmodel, iqmesh, amtobj, dir)
		meshobj.parent = amtobj if amtobj else grpobj

	for anim in iqmodel.anims:
		make_anim(iqmodel, anim, amtobj, bone_axis)

	print("all done.")

def import_iqm_file(filename, bone_axis='Y'):
	if filename.endswith(".iqm") or filename.endswith(".IQM"):
		iqmodel = load_iqm(filename)
	else:
		iqmodel = load_iqe(filename)
	dir = os.path.dirname(filename)
	make_model(iqmodel, bone_axis, dir)

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
		import_iqm_file(self.properties.filepath, self.bone_axis)
		return {'FINISHED'}

def menu_func(self, context):
	self.layout.operator(ImportIQM.bl_idname, text="Inter-Quake Model (.iqm, .iqe)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(menu_func)

if __name__ == "__main__":
	register()

#import_iqm_file("ju_s3_banana_tree.iqe")
#import_iqm_file("tr_mo_c03.iqe")
#import_iqm_file("tr_mo_kami_fighter.iqe")
#import_iqm_file("tr_mo_kami_fighter.iqm")
#import_iqm_file("tr_mo_kami_fighter_co_idle.iqe", 'Y')
