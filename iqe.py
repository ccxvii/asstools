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
			if len(self.texcoords):
				xy = self.texcoords[i]
				print >>file, "vt %.9g %.9g" % xy
			if len(self.normals):
				xyz = self.normals[i]
				print >>file, "vn %.9g %.9g %.9g" % xyz
			if len(self.colors):
				xyzw = self.colors[i]
				print >>file, "vc %.9g %.9g %.9g %.9g" % xyzw
			if len(self.blends):
				blend = self.blends[i]
				print >>file, "vb", " ".join(["%.9g" % x for x in blend])
		for face in self.faces:
			print "fm %d %d %d" % (face[0], face[1], face[2])

class Animation:
	def __init__(self, name):
		self.name = name
		self.framerate = 30
		self.loop = False
		self.frames = []

	def save(self, file):
		print >>file
		print >>file, "animation", self.name
		print >>file, "framerate", self.framerate
		if self.loop: print >>file, "loop"
		for frame in self.frames:
			print >>file
			print >>file, "frame"
			for pose in frame:
				print >>file, "pq", " ".join(["%.9g" % x for x in pose])

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

def load_model(file):
	model = Model()
	mesh = None
	pose = model.bindpose
	anim = None
	for line in file.xreadlines():
		line = shlex.split(line, "#")
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
			mesh.blends.append(tuple([float(x) for x in line[1:]]))
		elif line[0] == "fm":
			mesh.faces.append(tuple([int(x) for x in line[1:4]]))
		elif line[0] == "animation":
			anim = Animation(line[1])
			model.anims.append(anim)
		elif line[0] == "framerate":
			anim.framerate = int(line[1])
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

def make_material(mat):
	list = []
	if 'twosided' in mat: list += ['twosided']
	if 'alphatest' in mat: list += ['alphatest']
	if 'alphagloss' in mat: list += ['alphagloss']
	if 'unlit' in mat: list += ['unlit']
	if 'diffuse.file' in mat: list += [mat['diffuse.file']]
	else: list += ["unknown"]
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
			tex = "texture" + line.split(' ')[2]
		elif '=' in line:
			key, val = line.split('=', 1)
			if key == 'bTwoSided' and val == 'true': mat['twosided'] = True
			if key == 'bAlphaTest' and val == 'true': mat['alphatest'] = True
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
	print >>sys.stderr, lib
	return lib

def annotate_model(model, annots):
	for mesh in model.meshes:
		name = mesh.material[0]
		if name in annots:
			mesh.material[0:1] = make_material(annots[name])

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

if __name__ == "__main__":
	for filename in sys.argv[1:]:
		load_model(open(filename)).save(sys.stdout)

