#!/usr/bin/env python
#
# Load and write a subset of the IQE format.
#	only 'pq' poses
#	only 'fm' faces with positive indices
#	no smoothing groups
#	no custom vertex array types
#	no comment sections

import sys, shlex, fnmatch, os.path, math

def normalize(x, y, z):
	d = math.sqrt(x*x + y*y + z*z)
	if d >= 0.001:
		return x/d, y/d, z/d
	return 0, 0, 1

def x_to_y(v):
	x, y, z = v
	return -y, x, z

def y_to_z(v):
	x, y, z = v
	return x, -z, y

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

	def save(self, file):
		print >>file
		print >>file, 'mesh %s' % self.name
		print >>file, 'material %s' % ';'.join(self.material)
		for i in xrange(len(self.positions)):
			xyz = self.positions[i]
			print >>file, "vp %.9g %.9g %.9g" % xyz
			if len(self.normals):
				xyz = self.normals[i]
				print >>file, "vn %.9g %.9g %.9g" % xyz
			if len(self.texcoords):
				xy = self.texcoords[i]
				print >>file, "vt %.9g %.9g" % xy
			if len(self.colors):
				xyzw = self.colors[i]
				print >>file, "vc %.9g %.9g %.9g %.9g" % xyzw
			if len(self.blends):
				blend = self.blends[i]
				if len(blend) > 0:
					blend = reduce(lambda x,y: x+y, blend) # flatten pairs
				print >>file, "vb", " ".join(["%.9g" % x for x in blend])
			for k in range(10):
				if len(self.custom[k]):
					print >>file, "v%d" % k, " ".join(["%.9g" % x for x in self.custom[k][i]])
		for face in self.faces:
			if len(face) == 3:
				print >>file, "fm %d %d %d" % (face[0], face[1], face[2])
			else:
				print >>file, "fm %d %d %d %d" % (face[0], face[1], face[2], face[3])

class Animation:
	def __init__(self, name):
		self.name = name
		self.framerate = 30.0
		self.loop = False
		self.frames = []

	def save(self, file):
		print >>file
		print >>file, 'animation %s' % self.name
		if self.framerate != 30: print >>file, "framerate %g" % self.framerate
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
		self.vertexarrays = []
		self.comment = []

	def save(self, file):
		print >>file, "# Inter-Quake Export"
		if len(self.vertexarrays) > 0:
			print >>file
			# vertexarray custom0 float 2 "lightmap"
			for va in self.vertexarrays:
				print >>file, 'vertexarray %s %s %s %s' % va
		if len(self.bones) > 0:
			print >>file
			for bone in self.bones:
				print >>file, 'joint %s %d' % (bone[0], bone[1])
			print >>file
			for pose in self.bindpose:
				print >>file, "pq", " ".join(["%.9g" % x for x in pose])
		for mesh in self.meshes:
			mesh.save(file)
		for anim in self.anims:
			anim.save(file)
		if len(self.comment) > 0:
			print >>file
			print >>file, "comment"
			for line in self.comment:
				print >>file, line,

def load_model(file):
	def blend_pairs(t):
		return tuple(zip(t[::2], t[1::2]))
	model = Model()
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
			mesh.material = line[1].split(';')
		elif line[0] == "vp": mesh.positions.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vt": mesh.texcoords.append(tuple([float(x) for x in line[1:3]]))
		elif line[0] == "vn": mesh.normals.append(tuple([float(x) for x in line[1:4]]))
		elif line[0] == "vc": mesh.colors.append(tuple([float(x) for x in line[1:5]]))
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

# Create backfacing copies of doublesided meshes.

def doublesided_mesh(mesh):
	print >>sys.stderr, "doublesided mesh:", mesh.name
	mirror = Mesh(mesh.name + ".back")
	mirror.material = mesh.material
	mirror.positions = mesh.positions
	mirror.texcoords = mesh.texcoords
	mirror.colors = mesh.colors
	mirror.blends = mesh.blends
	mirror.custom = mesh.custom
	mirror.normals = []
	for x,y,z in mesh.normals:
		mirror.normals.append((-x,-y,-z))
	mirror.faces = []
	for face in mesh.faces:
		if len(face) == 3:
			a, b, c = face
			mirror.faces.append((c,b,a))
		else:
			a, b, c, d = face
			mirror.faces.append((d,c,b,a))
	return mirror

def singlesided_mesh(mesh):
	print >>sys.stderr, "singlesided mesh:", mesh.name
	mirror = Mesh(mesh.name + ".back")
	mirror.material = mesh.material
	mirror.positions = mesh.positions
	mirror.normals = mesh.normals
	mirror.texcoords = mesh.texcoords
	mirror.colors = mesh.colors
	mirror.blends = mesh.blends
	mirror.custom = mesh.custom
	mirror.faces = []
	for face in mesh.faces:
		if len(face) == 3:
			a, b, c = face
			mirror.faces.append((c,b,a))
		else:
			a, b, c, d = face
			mirror.faces.append((d,c,b,a))
	return mirror

def doublesided_model(model):
	extra = []
	for mesh in model.meshes:
		if 'doublesided' in mesh.material:
			mesh.material.remove('doublesided')
			extra.append(doublesided_mesh(mesh))
	model.meshes += extra

def singlesided_model(model):
	extra = []
	for mesh in model.meshes:
		if 'singlesided' in mesh.material:
			mesh.material.remove('singlesided')
			extra.append(singlesided_mesh(mesh))
	model.meshes += extra


# Radial normals.

def normal_thief_grass(mesh):
	mesh.normals = [(0,0,1)] * len(mesh.normals)

def normal_thief_tree(mesh):
	cx, cy, cz = 0, 0, 0
	bboxmin = [1e10, 1e10, 1e10]
	bboxmax = [-1e10, -1e10, -1e10]
	for x,y,z in mesh.positions:
		cx += x
		cy += y
		cz += z
	cx /= len(mesh.positions)
	cy /= len(mesh.positions)
	cz /= len(mesh.positions)
	for i in range(len(mesh.positions)):
		x, y, z = mesh.positions[i]
		mesh.normals[i] = normalize(x-cx, y-cy, z-cz)

def calc_mesh_center(mesh):
	cx, cy, cz = 0, 0, 0
	for x,y,z in mesh.positions:
		cx += x
		cy += y
		cz += z
	cx /= len(mesh.positions)
	cy /= len(mesh.positions)
	cz /= len(mesh.positions)
	return cx, cy, cz

def calc_mesh_base(mesh):
	cx, cy, cz = 0, 0, 1e10
	for x,y,z in mesh.positions:
		cx += x
		cy += y
		cz = min(cz, z)
	cx /= len(mesh.positions)
	cy /= len(mesh.positions)
	return cx, cy, cz

def calc_radial_mesh(mesh, centers):
	print >>sys.stderr, "radial normals:", centers
	cx, cy, cz = 0, 0, 0
	for i, p in enumerate(mesh.positions):
		x, y, z = p
		nearest_pos, nearest_dist = (0, 0, 0), 1e10
		for c in centers:
			dx, dy, dz = x-c[0], y-c[1], z-c[2]
			dist = dx*dx + dy*dy + dz*dz
			if dist < nearest_dist:
				nearest_dist = dist
				cx, cy, cz = c
		mesh.normals[i] = normalize(x-cx, y-cy, z-cz)

def calc_radial_model(model):
	for mesh in model.meshes:
		centers = []
		print >>sys.stderr, "radial mats", mesh.material
		for tag in mesh.material:
			if tag == "radial=center": centers.append(calc_mesh_center(mesh))
			elif tag == "radial=base": centers.append(calc_mesh_base(mesh))
			elif tag.startswith("radial="): centers.append(tuple([float(x) for x in tag[7:].split(",")]))
		if len(centers) > 0:
			calc_radial_mesh(mesh, centers)

# Transform model.

def scale_model(model, s):
	for mesh in model.meshes:
		mesh.positions = [(x*s,y*s,z*s) for x,y,z in mesh.positions]
	for i in range(len(model.bindpose)):
		pose = list(model.bindpose[i])
		pose[0] *= s
		pose[1] *= s
		pose[2] *= s
		model.bindpose[i] = tuple(pose)
	for anim in model.anims:
		for frame in anim.frames:
			for i in range(len(frame)):
				pose = list(frame[i])
				pose[0] *= s
				pose[1] *= s
				pose[2] *= s
				frame[i] = tuple(pose)

def translate_model(model, tx, ty, tz):
	if len(model.bindpose) > 0:
		pose = list(model.bindpose[0])
		pose[0] += tx
		pose[1] += ty
		pose[2] += tz
		model.bindpose[0] = tuple(pose)
	for mesh in model.meshes:
		mesh.positions = [(tx+x,ty+y,tz+z) for x,y,z in mesh.positions]

def zero_root_translation(model):
	pose = list(model.bindpose[0])
	translate_model(model, -pose[0], -pose[1], -pose[2])

def drop_to_ground(model):
	min_z = 1000
	for mesh in model.meshes:
		for x, y, z in mesh.positions:
			if z < min_z:
				min_z = z
	translate_model(model, 0, 0, -min_z)

def model_x_to_y(model):
	# TODO: bones
	for mesh in model.meshes:
		mesh.positions = [x_to_y(v) for v in mesh.positions]
		mesh.normals = [x_to_y(v) for v in mesh.normals]

def model_y_to_z(model):
	# TODO: bones
	for mesh in model.meshes:
		mesh.positions = [y_to_z(v) for v in mesh.positions]
		mesh.normals = [y_to_z(v) for v in mesh.normals]

# Merge meshes with the same material.

def append_mesh(output, mesh):
	offset = len(output.positions)
	output.positions += mesh.positions
	output.texcoords += mesh.texcoords
	output.normals += mesh.normals
	output.colors += mesh.colors
	output.blends += mesh.blends
	for k in range(10):
		output.custom[k] += mesh.custom[k]
	for face in mesh.faces:
		if len(face) == 3:
			a, b, c = face
			output.faces.append((a+offset, b+offset, c+offset))
		else:
			a, b, c, d = face
			output.faces.append((a+offset, b+offset, c+offset, d+offset))

def merge_meshes(model):
	map = {}
	for mesh in model.meshes:
		key = ';'.join(mesh.material)
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

def copy_bone_translation(target, source):
	remap = make_bone_map(target, source)
	for i in range(len(target.bones)):
		if i in remap:
			k = remap[i]
			spose = list(source.bindpose[k])
			tpose = list(target.bindpose[k])
			pose = spose[:3] + tpose[3:]
			target.bindpose[i] = tuple(pose)

def copy_bip01(target, source):
	source.bindpose = source.anims[0].frames[0]
	target.meshes = []
	remap = make_bone_map(target, source)
	for i in range(len(target.bones)):
		n = target.bones[i][0]
		if n == 'bip01' or n == 'bip01_pelvis':
			if i in remap:
				k = remap[i]
				target.bindpose[i] = source.bindpose[k]

def copy_animation(target, source):
	remap = make_bone_map(target, source)
	for srcanim in source.anims:
		dstanim = Animation(srcanim.name)
		dstanim.framerate = srcanim.framerate
		dstanim.loop = srcanim.loop
		for srcframe in srcanim.frames:
			dstframe = []
			for i in range(len(target.bones)):
				if i in remap:
					k = remap[i]
					dstframe.append(srcframe[k])
				else:
					dstframe.append(target.bindpose[i])
			dstanim.frames.append(dstframe)
		target.anims.append(dstanim)

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
		part.vertexarrays = model.vertexarrays
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

# Force scaling to 1 (and warn)

def kill_bind_scaling(model):
	for i in range(len(model.bindpose)):
		model.bindpose[i] = model.bindpose[i][0:7]

def kill_anim_scaling(model):
	for anim in model.anims:
		for frame in anim.frames:
			for i in range(len(frame)):
				frame[i] = frame[i][0:7]
