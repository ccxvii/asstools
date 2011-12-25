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
		print >>file, "material", self.material
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
			mesh.material = line[1]
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

if __name__ == "__main__":
	m = load_model(sys.stdin)
	m.save(sys.stdout)

