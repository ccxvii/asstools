#!/usr/bin/env python
#
# Load and write a subset of the IQE format.
#	only 'pq' poses
#	only 'fm' faces with positive indices
#	no smoothing groups
#	no custom vertex array types
#	no comment sections

import sys, shlex, fnmatch

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

	def save(self, file):
		print >>file
		print >>file, "mesh", self.name
		print >>file, "material", '+'.join(self.material)
		for i in xrange(len(self.positions)):
			xyz = self.positions[i]
			print >>file, "vp %.9g %.9g %.9g" % xyz
			if len(self.texcoords) == len(self.positions):
				xy = self.texcoords[i]
				print >>file, "vt %.9g %.9g" % xy
			if len(self.normals) == len(self.positions):
				xyz = self.normals[i]
				print >>file, "vn %.9g %.9g %.9g" % xyz
			if len(self.colors) == len(self.positions):
				xyzw = self.colors[i]
				print >>file, "vc %.9g %.9g %.9g %.9g" % xyzw
			if len(self.blends) == len(self.positions):
				blend = self.blends[i]
				if len(blend) > 0:
					blend = reduce(lambda x,y: x+y, blend) # flatten pairs
				print >>file, "vb", " ".join(["%.9g" % x for x in blend])
		for face in self.faces:
			print >>file, "fm %d %d %d" % (face[0], face[1], face[2])

class Animation:
	def __init__(self, name):
		self.name = name
		self.framerate = 30.0
		self.loop = False
		self.frames = []

	def save(self, file):
		print >>file
		print >>file, "animation", self.name
		print >>file, "framerate", self.framerate
		if self.loop: print >>file, "loop"
		framenumber = 0
		for frame in self.frames:
			print >>file
			print >>file, "frame", framenumber
			for pose in frame:
				print >>file, "pq", " ".join(["%.9g" % x for x in pose])
			framenumber = framenumber + 1

class Model:
	def __init__(self):
		self.bones = []
		self.bindpose = []
		self.meshes = []
		self.anims = []

	def save(self, file):
		print >>file, "# Inter-Quake Export"
		if len(self.bones) > 0:
			print >>file
			for bone in self.bones:
				print >>file, "joint", bone[0], bone[1]
			print >>file
			for pose in self.bindpose:
				print >>file, "pq", " ".join(["%.9g" % x for x in pose])
		for mesh in self.meshes:
			mesh.save(file)
		for anim in self.anims:
			anim.save(file)

def blend_pairs(t):
	return tuple(zip(t[::2], t[1::2]))

def load_model(file):
	model = Model()
	mesh = None
	pose = model.bindpose
	anim = None
	for line in file.xreadlines():
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
			mesh.material = line[1].split('+')
		elif line[0] == "vp":
			mesh.positions.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vt":
			mesh.texcoords.append(tuple([float(x) for x in line[1:3]]))
		elif line[0] == "vn":
			mesh.normals.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vc":
			mesh.colors.append(tuple([float(x) for x in line[1:5]]))
		elif line[0] == "vb":
			mesh.blends.append(blend_pairs([float(x) for x in line[1:]]))
		elif line[0] == "fm":
			mesh.faces.append(tuple([int(x) for x in line[1:4]]))
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
	return model


# Annotate materials with flags from data in .material files.

def basename(str):
	str = str.split('\\')[-1]
	str = str.split('/')[-1]
	str = str.split('.')[0]
	str = str.lower().replace(' ', '_')
	return str

def make_material(mat, texture):
	list = []
	if 'twosided' in mat: list += ['twosided']
	#if 'alphatest' in mat: list += ['alphatest']
	if 'alphablend' in mat: list += ['alphablend']
	#if 'alphagloss' in mat: list += ['alphagloss']
	if 'unlit' in mat: list += ['unlit']
	if 'clipu' in mat: list += ['clipu=%g' % mat['clipu']]
	if 'clipv' in mat: list += ['clipv=%g' % mat['clipv']]
	#if 'clipw' in mat: list += ['clipw=%g' % mat['clipw']]
	#if 'cliph' in mat: list += ['cliph=%g' % mat['cliph']]
	#if 'diffuse.file' in mat: list += [mat['diffuse.file']]
	#elif 'specular.file' in mat: list += [mat['specular.file']]
	#else: list += [texture]
	list += [texture]
	return list

def load_material(file):
	lib = {}
	mat = None
	tex = None
	for line in file.xreadlines():
		line = line.strip()
		if line.startswith("material "):
			name = line.split(' ', 1)[1]
			name = name.lower().replace(' ', '_').replace('#', '_')
			mat = {}
			lib[name] = mat
		elif line.startswith("texture 1"):
			tex = "diffuse"
		elif line.startswith("texture 2"):
			tex = "specular"
		elif line.startswith("texture "):
			tex = "texture" + line.split(' ')[1]
		elif '=' in line:
			key, val = line.split('=', 1)
			if key == 'twoSided' and val == 'true': mat['twosided'] = True
			if key == 'bTwoSided' and val == 'true': mat['twosided'] = True
			if key == 'bAlphaTest' and val == 'true': mat['alphatest'] = True
			if key == 'bAlphaBlend' and val == 'true': mat['alphablend'] = True
			if key == 'iShaderType' and val == '5': mat['alphagloss'] = True
			if key == 'bUnlighted' and val == 'true': mat['unlit'] = True
			if key == 'bitmap1FileName' and val: mat[tex+".file1"] = basename(val)
			if key == 'bitmap2FileName' and val: mat[tex+".file2"] = basename(val)
			if key == 'bitmap3FileName' and val: mat[tex+".file3"] = basename(val)
			if key == 'bitmap4FileName' and val: mat[tex+".file4"] = basename(val)
			if key == 'bitmap5FileName' and val: mat[tex+".file5"] = basename(val)
			if key == 'bitmap6FileName' and val: mat[tex+".file6"] = basename(val)
			if key == 'bitmap7FileName' and val: mat[tex+".file7"] = basename(val)
			if key == 'bitmap8FileName' and val: mat[tex+".file8"] = basename(val)
			if key == 'bitmap.filename' and val: mat[tex+".file"] = basename(val)
			if key == 'bitmap.clipu' and float(val) != 0: mat['clipu'] = float(val)
			if key == 'bitmap.clipv' and float(val) != 0: mat['clipv'] = float(val)
			if key == 'bitmap.clipw' and float(val) != 1: mat['clipw'] = float(val)
			if key == 'bitmap.cliph' and float(val) != 1: mat['cliph'] = float(val)
	#print >>sys.stderr, lib
	return lib

def annotate_model(model, annots):
	for mesh in model.meshes:
		name = mesh.material[0]
		texture = mesh.material[-1]
		if name in annots:
			mesh.material = make_material(annots[name], texture)
		else:
			name = name.replace("_1", "")
			if name in annots:
				mesh.material = make_material(annots[name], texture)

# Create backfacing copies of twosided meshes.

def backface_mesh(mesh):
	print >>sys.stderr, "backface mesh:", mesh.name
	mirror = Mesh(mesh.name + ",backface")
	mirror.material = mesh.material
	mirror.positions = mesh.positions
	mirror.texcoords = mesh.texcoords
	mirror.colors = mesh.colors
	mirror.blends = mesh.blends
	mirror.normals = []
	for x,y,z in mesh.normals:
		mirror.normals.append((-x,-y,-z))
	mirror.faces = []
	for a,b,c in mesh.faces:
		mirror.faces.append((c,b,a))
	return mirror

def backface_model(model):
	extra = []
	for mesh in model.meshes:
		if 'twosided' in mesh.material:
			mesh.material.remove('twosided')
			extra.append(backface_mesh(mesh))
	model.meshes += extra

# Apply global scale to all mesh coords

def scale_model(model, s):
	for mesh in model.meshes:
		mesh.positions = [(x*s,y*s,z*s) for x,y,z in mesh.positions]

# Translate model coords

def translate_model(model, tx, ty, tz):
	for mesh in model.meshes:
		mesh.positions = [(tx+x,ty+y,tz+z) for x,y,z in mesh.positions]

# Flip X to Y (for weapon models to realign with blender bones)

def x_to_y(v):
	x, y, z = v
	return -y, x, z

def model_x_to_y(model):
	for mesh in model.meshes:
		mesh.positions = [x_to_y(v) for v in mesh.positions]
		mesh.normals = [x_to_y(v) for v in mesh.normals]

# Fix UV coords that have a clip region set. Ugh.
# We can offset the origin, but then the repeat/wrapping fails.
# We can offset the origin, and wrap the U/V coords, but then it wraps
# the wrong way.
# We can remap the uv space, but then we have to extract the cropped region
# of the texture as a separate texture.

def clipuv_mesh(mesh, uofs, vofs, w, h):
	print >>sys.stderr, "clipuv", mesh.name, uofs, vofs, w, h
	newtc = []
	for u,v in mesh.texcoords:
		#if u > w: u -= w
		#if v > h: v -= h
		u += uofs;
		v += vofs;
		#u = u / w
		#v = v / h
		newtc.append((u, v))
	mesh.texcoords = newtc

def clipuv_model(model):
	for mesh in model.meshes:
		u = v = 0
		w = h = 1
		ua = va = wa = ha = None
		for a in mesh.material:
			if a.startswith('clipu='): u = float(a.split('=')[1]); ua = a
			if a.startswith('clipv='): v = float(a.split('=')[1]); va = a
			if a.startswith('clipw='): w = float(a.split('=')[1]); wa = a
			if a.startswith('cliph='): h = float(a.split('=')[1]); ha = a
		if u != 0 or v != 0 or w != 1 or h != 1:
			clipuv_mesh(mesh, u, v, w, h)

# Merge meshes with the same material.

def append_mesh(output, mesh):
	offset = len(output.positions)
	output.positions += mesh.positions
	output.texcoords += mesh.texcoords
	output.normals += mesh.normals
	output.colors += mesh.colors
	output.blends += mesh.blends
	for a,b,c in mesh.faces:
		output.faces.append((a+offset, b+offset, c+offset))

def merge_meshes(model):
	map = {}
	for mesh in model.meshes:
		key = '+'.join(mesh.material)
		if key in map:
			map[key] += [mesh]
		else:
			map[key] = [mesh]
	output = []
	for key in map:
		if len(map[key]) > 1:
			name = "+".join([x.name for x in map[key]])
			print >>sys.stderr, "merging meshes:", name
			merged = Mesh(name)
			merged.material = map[key][0].material
			for mesh in map[key]:
				append_mesh(merged, mesh)
		else:
			merged = map[key][0]
		output.append(merged)
	model.meshes = output

# Delete or keep named meshes

def delete_meshes(model, meshnames):
	bucket = {}
	for mesh in model.meshes:
		for glob in meshnames:
			if fnmatch.fnmatch(mesh.name, glob):
				bucket[mesh] = 1
	for mesh in bucket:
		print >>sys.stderr, "deleting mesh", mesh.name
		model.meshes.remove(mesh)

def select_meshes(model, meshnames):
	bucket = {}
	for mesh in model.meshes:
		for glob in meshnames:
			if fnmatch.fnmatch(mesh.name, glob):
				bucket[mesh] = 1
	model.meshes = bucket.keys()

# Copy bind pose from one file to another, matching by bone names.

def make_bone_map(target, source):
	remap = {}
	for i in range(len(target.bones)):
		tname = target.bones[i][0]
		for k in range(len(source.bones)):
			sname = source.bones[k][0]
			if sname == tname:
				remap[i] = k
	return remap

def copy_bind_pose(target, source):
	remap = make_bone_map(target, source)
	for i in range(len(target.bones)):
		if i in remap:
			k = remap[i]
			target.bindpose[i] = source.bindpose[k]

# Discard bones not in list of bones to keep.

def select_bones(model, keeplist):
	new_bones = []
	new_names = []
	new_parents = []
	new_bindpose = []
	N = 0
	for name, parent in model.bones:
		# drop dups as well
		if name in keeplist and not name in new_names:
			new_parent = -1
			if parent > 0:
				parent_name = model.bones[parent][0]
				if parent_name in new_names:
					new_parent = new_names.index(parent_name)
			new_names += [name]
			new_parents += [new_parent]
			new_bones += [(name, new_parent)]
			new_bindpose += [model.bindpose[N]]
		N = N + 1
	# TODO: remap vertices and animations...
	model.meshes = []
	model.anims = []
	model.bones = new_bones
	model.bindpose = new_bindpose

# Split meshes into separate models (all meshes with same name in one model)

def split_and_save_meshes(model):
	mesh_list = {}
	for m in model.meshes:
		if not m.name in mesh_list:
			mesh_list[m.name] = []
		mesh_list[m.name] += [ m ]
	for name in mesh_list:
		part = Model()
		part.name = name
		part.bones = model.bones
		part.bindpose = model.bindpose
		part.meshes = mesh_list[name]
		print "saving mesh:", name
		part.save(open(name + ".iqe", "w"))

# Kill selected channels in an animation

def kill_channels(model, kill_loc, kill_rot, kill_scl):
	for anim in model.anims:
		for frame in anim.frames:
			for i in range(len(frame)):
				name = model.bones[i][0]
				p = frame[i]
				a = anim.frames[0][i]
				if kill_loc(name): p = a[0:3] + p[3:7] + p[7:10]
				if kill_rot(name): p = p[0:3] + a[3:7] + p[7:10]
				if kill_scl(name): p = p[0:3] + p[3:7] + a[7:10]
				frame[i] = p
				#if frame == anim.frames[0]: print >>sys.stderr, kill_loc(name), kill_rot(name), kill_scl(name), name

if __name__ == "__main__":
	for filename in sys.argv[1:]:
		load_model(open(filename)).save(sys.stdout)

