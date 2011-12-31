# Importer for Inter-Quake Model / Export formats

bl_info = {
	"name": "Import Inter-Quake Model (.iqm, .iqe)",
	"author": "Tor Andersson",
	"version": (0, 1),
	"blender": (2, 6, 0),
	"location": "File > Import > Inter-Quake Model",
	"description": "Import IQM or IQE model with vertex colors and armature.",
	"category": "Import-Export",
}

import bpy, math, shlex, struct

from bpy.props import *
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Quaternion, Vector

# see blenkernel/intern/armature.c for vec_roll_to_mat3
# see blenkernel/intern/armature.c for mat3_to_vec_roll
# see makesrna/intern/rna_armature.c for rna_EditBone_matrix_get

def vec_roll_to_mat3(vec, roll):
	target = Vector((0,1,0))
	nor = vec.normalized()
	axis = target.cross(nor)
	axis.normalize()
	theta = target.angle(nor)
	bMatrix = Matrix.Rotation(theta, 3, axis)
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
# IQE Parser
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

def load_iqe_model(filename):
	name = filename.split("/")[-1].split("\\")[-1].split(".")[0]
	model = IQModel(name)
	mesh = None
	pose = model.bindpose
	anim = None
	file = open(filename)
	line = file.readline()
	if not line.startswith("# Inter-Quake Export"):
		raise Exception("Not an IQE file")
	for line in file.readlines():
		line = shlex.split(line, "#")
		if len(line) == 0:
			pass
		elif line[0] == "joint":
			name = line[1]
			parent = int(line[2])
			model.bones.append((name, parent))
		elif line[0] == "pq":
			pq = [float(x) for x in line[1:]]
			if len(pq) < 10: pq += [1,1,1]
			pose.append(pq)
		elif line[0] == "pm": raise Exception("pm style poses not implemented yet")
		elif line[0] == "pa": raise Exception("pa style poses not implemented yet")
		elif line[0] == "mesh":
			mesh = IQMesh(line[1])
			model.meshes.append(mesh)
		elif line[0] == "material":
			mesh.material = line[1].split("+")
		elif line[0] == "vp":
			mesh.positions.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vt":
			u,v = [float(x) for x in line[1:3]]
			mesh.texcoords.append((u,v))
		elif line[0] == "vn":
			mesh.normals.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vc":
			mesh.colors.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "vb":
			mesh.blends.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "fm":
			a,b,c = [int(x) for x in line[1:]]
			mesh.faces.append((a,b,c))
		elif line[0] == "fa": raise Exception("fa style faces not implemented yet")
		elif line[0] == "animation":
			anim = IQAnimation(line[1])
			model.anims.append(anim)
		elif line[0] == "framerate":
			anim.framerate = int(line[1])
		elif line[0] == "loop":
			anim.loop = True
		elif line[0] == "frame":
			pose = []
			anim.frames.append(pose)
	return model

#
# IQM Parser
#

VA_POSITION = 0
VA_TEXCOORD = 1
VA_NORMAL = 2
VA_BLENDINDEXES = 4
VA_BLENDWEIGHTS = 5
VA_COLOR = 6

def cstr(text, ofs):
	len = 0
	while text[ofs+len] != 0:
		len += 1
	return str(text[ofs:ofs+len], encoding='utf-8')

def load_iqm_joints(file, text, num_joints, ofs_joints):
	file.seek(ofs_joints)
	bones = []
	bindpose = []
	for x in range(num_joints):
		data = struct.unpack("<Ii10f", file.read(12*4))
		name = cstr(text, data[0])
		parent = data[1]
		pose = data[2:12]
		bones.append((name, parent))
		bindpose.append(list(data[2:12]))
	return bones, bindpose

def load_iqm_poses(file, num_poses, ofs_poses):
	file.seek(ofs_poses)
	poselist = []
	for x in range(num_poses):
		pose = struct.unpack("<iI20f", file.read(22*4))
		poselist.append(pose)
	return poselist

def load_iqm_frames(file, num_frames, num_framechannels, ofs_frames):
	file.seek(ofs_frames)
	F = "<"+"H"*num_framechannels; S=2*num_framechannels
	framelist = []
	for x in range(num_frames):
		frame = struct.unpack(F, file.read(S))
		framelist.append(frame)
	return framelist

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
		out.append(data)
	return out

def load_iqm_anims(file, text, num_anims, ofs_anims, poses, frames):
	file.seek(ofs_anims)
	anims = []
	for n in range(num_anims):
		data = struct.unpack("<3IfI", file.read(5*4))
		name = cstr(text, data[0])
		first = data[1]
		count = data[2]
		anim = IQAnimation(name)
		anim.framerate = data[3]
		anim.loop = data[4]
		for y in range(first, first+count):
			anim.frames.append(copy_iqm_frame(poses, frames[y]))
		anims.append(anim)
	return anims

def load_iqm_vertexarray(file, format, size, offset, count):
	if format != 1 and format != 7:
		raise Exception("can only handle ubyte and float arrays")
	if format == 1: A="<"+"B"*size; S=1*size
	if format == 7: A="<"+"f"*size; S=4*size
	file.seek(offset)
	list = []
	for n in range(count):
		comp = struct.unpack(A, file.read(S))
		list.append(comp)
	return list

def load_iqm_vertexarrays(file, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	file.seek(ofs_vertexarrays)
	valist = []
	for n in range(num_vertexarrays):
		va = struct.unpack("<5I", file.read(5*4))
		valist += (va,)
	verts = {}
	for type, flags, format, size, offset in valist:
		verts[type] = load_iqm_vertexarray(file, format, size, offset, num_vertexes)
	return verts

def load_iqm_triangles(file, num_triangles, ofs_triangles, ofs_adjacency):
	file.seek(ofs_triangles)
	tris = []
	for n in range(num_triangles):
		data = struct.unpack("<3I", file.read(3*4))
		tris.append(data)
	return tris

def copy_iqm_verts(mesh, verts, first, count):
	for n in range(first, first+count):
		if VA_POSITION in verts:
			mesh.positions.append(verts[VA_POSITION][n])
		if VA_NORMAL in verts:
			mesh.normals.append(verts[VA_NORMAL][n])
		if VA_TEXCOORD in verts:
			mesh.texcoords.append(verts[VA_TEXCOORD][n])
		if VA_COLOR in verts:
			mesh.colors.append(verts[VA_COLOR][n])
		if VA_BLENDINDEXES in verts and VA_BLENDWEIGHTS in verts:
			vb = []
			for y in range(4):
				if verts[VA_BLENDWEIGHTS][n][y] > 0:
					vb.append(verts[VA_BLENDINDEXES][n][y])
					vb.append(verts[VA_BLENDWEIGHTS][n][y]/255.0)
			mesh.blends.append(vb)

def copy_iqm_faces(mesh, tris, first, count, fv):
	for n in range(first, first+count):
		tri = tris[n]
		mesh.faces.append((tri[0]-fv, tri[1]-fv, tri[2]-fv))

def load_iqm_meshes(file, text, num_meshes, ofs_meshes, verts, tris):
	file.seek(ofs_meshes)
	meshes = []
	for n in range(num_meshes):
		data = struct.unpack("<6I", file.read(6*4))
		name = cstr(text, data[0])
		material = cstr(text, data[1])
		v1, vnum, t1, tnum = data[2:]
		mesh = IQMesh(name)
		mesh.material = material.split("+")
		copy_iqm_verts(mesh, verts, v1, vnum)
		copy_iqm_faces(mesh, tris, t1, tnum, v1)
		meshes.append(mesh)
	return meshes

def load_iqm_model(filename, ):
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

	verts = load_iqm_vertexarrays(file, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	tris = load_iqm_triangles(file, num_triangles, ofs_triangles, ofs_adjacency)
	poses = load_iqm_poses(file, num_poses, ofs_poses)
	frames = load_iqm_frames(file, num_frames, num_framechannels, ofs_frames)

	model.bones, model.bindpose = load_iqm_joints(file, text, num_joints, ofs_joints)
	model.meshes = load_iqm_meshes(file, text, num_meshes, ofs_meshes, verts, tris)
	model.anims = load_iqm_anims(file, text, num_anims, ofs_anims, poses, frames)

	return model

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
	abs_pose_mat = [None] * len(iqmodel.bones)

	for n in range(len(iqmodel.bones)):
		bonename, boneparent = iqmodel.bones[n]
		pose = iqpose[n]

		local_loc = Vector(pose[0:3])
		local_rot = Quaternion([pose[6]] + pose[3:6])
		local_size = Vector(pose[7:10])

		mat_loc = Matrix.Translation(local_loc)
		mat_rot = local_rot.to_matrix().to_4x4()
		mat_size = Matrix.Scale(local_size.x, 3).to_4x4()
		loc_pose_mat = mat_loc * mat_rot * mat_size

		if boneparent >= 0:
			abs_pose_mat[n] = abs_pose_mat[boneparent] * loc_pose_mat
		else:
			abs_pose_mat[n] = loc_pose_mat

	if bone_axis == 'X': axis_flip = Matrix.Rotation(math.radians(-90), 4, 'Z')
	if bone_axis == 'Z': axis_flip = Matrix.Rotation(math.radians(-90), 4, 'X')
	if bone_axis != 'Y':
		for n in range(len(iqmodel.bones)):
			abs_pose_mat[n] = abs_pose_mat[n] * axis_flip

	return abs_pose_mat

def make_armature(iqmodel, bone_axis):

	if len(iqmodel.bones) == 0: return None
	if len(iqmodel.bindpose) != len(iqmodel.bones): return None

	print("importing armature with %d bones" % len(iqmodel.bones))

	amt = bpy.data.armatures.new("Skeleton")
	obj = bpy.data.objects.new(iqmodel.name, amt)
	bpy.context.scene.objects.link(obj)
	bpy.context.scene.objects.active = obj

	bpy.ops.object.mode_set(mode='EDIT')

	abs_bind_mat = calc_pose_mats(iqmodel, iqmodel.bindpose, bone_axis)

	for n in range(len(iqmodel.bones)):
		bonename, boneparent = iqmodel.bones[n]

		bone = amt.edit_bones.new(bonename)
		parent = None
		if boneparent >= 0:
			parent = amt.edit_bones[boneparent]
			bone.parent = parent

		# TODO: bone scaling
		loc = abs_bind_mat[n].to_translation()
		axis, roll = mat3_to_vec_roll(abs_bind_mat[n].to_3x3())
		axis *= 0.125 # short bones
		bone.roll = roll
		bone.head = loc
		bone.tail = loc + axis

		# extend parent and connect if we are aligned
		if parent:
			a = (bone.head - parent.head).normalized()
			b = (parent.tail - parent.head).normalized()
			if a.dot(b) > 0.999:
				parent.tail = bone.head
				bone.use_connect = True

	bpy.ops.object.mode_set(mode='OBJECT')

	return obj

#
# Strike a pose.
#

def make_pose(iqmodel, iqpose, amtobj, bone_axis):
	abs_pose_mat = calc_pose_mats(iqmodel, iqpose, bone_axis)
	#abs_pose_mat = calc_pose_mats(iqmodel, iqmodel.bindpose, bone_axis)
	for n in range(len(iqmodel.bones)):
		pose_bone = amtobj.pose.bones[n]
		rest_bone = amtobj.data.bones[n]

		# hmm, they're not the same in the initial pose!
		print("BONE", n)
		print(abs_pose_mat[n])
		print(rest_bone.matrix_local)
		print(pose_bone.matrix)

		pose_bone.matrix = rest_bone.matrix_local

#
# Create simple material by looking at the magic words.
# Use the last word as a texture name by appending ".png".
#

images = {}

def make_material(mesh, iqmaterial):
	matname = "+".join(iqmaterial)
	texname = iqmaterial[-1] + ".png"

	print("importing material", matname)

	twosided = 'twosided' in iqmaterial
	alphatest = 'alphatest' in iqmaterial
	alphagloss = 'alphagloss' in iqmaterial
	unlit = 'unlit' in iqmaterial

	if not texname in images:
		try:
			images[texname] = bpy.data.images.load(texname)
		except:
			images[texname] = None
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

def make_mesh(iqmodel, iqmesh, amtobj):
	print("importing mesh %s with %d vertices and %d faces" %
		(iqmesh.name, len(iqmesh.positions), len(iqmesh.faces)))

	mesh = bpy.data.meshes.new(iqmesh.name)
	obj = bpy.data.objects.new(iqmesh.name, mesh)
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
		print("has vertex colors")
		clayer = mesh.vertex_colors.new()
		for n in range(len(mesh.faces)):
			a, b, c = mesh.faces[n].vertices
			data = clayer.data[n]
			data.color1 = iqmesh.colors[a][0:3]
			data.color2 = iqmesh.colors[b][0:3]
			data.color3 = iqmesh.colors[c][0:3]

	# Vertex groups for skinning

	if len(iqmesh.blends) == len(iqmesh.positions) and amtobj:
		print("has vertex bone weights")
		for bonename, boneparent in iqmodel.bones:
			obj.vertex_groups.new(bonename)
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

	image = make_material(mesh, iqmesh.material)

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

def make_model(iqmodel, bone_axis):
	print("importing model", iqmodel.name)

	for obj in bpy.context.scene.objects:
		obj.select = False

	amtobj = make_armature(iqmodel, bone_axis)
	if not amtobj:
		grpobj = bpy.data.objects.new(iqmodel.name, None)
		bpy.context.scene.objects.link(grpobj)

	for iqmesh in iqmodel.meshes:
		meshobj = make_mesh(iqmodel, iqmesh, amtobj)
		meshobj.parent = amtobj if amtobj else grpobj

	if len(iqmodel.anims) > 0:
		print("warning: cannot import animations yet:", len(iqmodel.anims))
		# make_pose(iqmodel, iqmodel.anims[0].frames[0], amtobj, bone_axis)

	print("all done.")

def import_iqm_file(filename, bone_axis='Y'):
	if filename.endswith(".iqm") or filename.endswith(".IQM"):
		iqmodel = load_iqm_model(filename)
	else:
		iqmodel = load_iqe_model(filename)
	make_model(iqmodel, bone_axis)

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
				('X', "From X to Y", ""),
				('Z', "From Z to Y", "")
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
