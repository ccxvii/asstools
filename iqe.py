#!/usr/bin/env python
#
# Load and write a subset of the IQE format.
#	only 'pq' poses
#	only 'fm' faces with positive indices
#	no smoothing groups
#	no custom vertex array types
#	no comment sections

import math, sys

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
		print >>file, "material", "+".join(self.material)
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
		line = line.split()
		if len(line) == 0 or line[0] == "#":
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

def load_material(file):
	annots = {}
	for line in file.xreadlines():
		if 'twosided' in line:
			name = line.split(';')[0]
			name = name.lower().replace(' ', '_').replace('#', '_')
			flags = []
			if 'twosided=true' in line: flags.append('twosided')
			if 'alphatest=true' in line: flags.append('alphatest')
			if 'shader=5' in line: flags.append('alphaspec')
			annots[name] = flags
	return annots

def annotate_model(model, annots):
	for mesh in model.meshes:
		name = mesh.material[0]
		if name in annots:
			mesh.material[0:1] = annots[name]

# Create backfacing copies of twosided meshes.

def backface_mesh(mesh):
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
		key = "+".join(mesh.material)
		if key in map:
			map[key] += [mesh]
		else:
			map[key] = [mesh]
	output = []
	for key in map:
		if len(map[key]) > 1:
			material = key.split('+')
			name = "+".join([x.name for x in map[key]])
			merged = Mesh(name)
			merged.material = material
			for mesh in map[key]:
				append_mesh(merged, mesh)
		else:
			merged = map[key][0]
		output.append(merged)
	model.meshes = output

# Default behaviour: process with all passes

if __name__ == "__main__":
	for filename in sys.argv[1:]:
		m = load_model(open(filename))
		a = load_material(open(filename.replace(".iqe", ".material")))
		annotate_model(m, a)
		backface_model(m)
		merge_meshes(m)
		m.save(sys.stdout)

