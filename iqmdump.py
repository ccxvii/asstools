#!/usr/bin/env python

import sys, math, struct

iqmver = 1
iqm_va_type = {
	0: "POSITION",
	1: "TEXCOORD",
	2: "NORMAL",
	3: "TANGENT",
	4: "BLENDINDEXES",
	5: "BLENDWEIGHTS",
	6: "COLOR",
	8: "reserved", 9: "reserved", 10: "reserved", 11: "reserved",
	12: "reserved", 13: "reserved", 14: "reserved", 15: "reserved",
	16: "CUSTOM0",
	17: "CUSTOM1",
	18: "CUSTOM2",
	19: "CUSTOM3",
	20: "CUSTOM4",
	21: "CUSTOM5",
	22: "CUSTOM6",
	23: "CUSTOM7",
	24: "CUSTOM8",
	25: "CUSTOM9",
}

def cstr(text, ofs):
	t = ""
	while text[ofs] != "\0":
		t += text[ofs]
		ofs += 1
	return t

def restorew(rot):
	x, y, z = rot
	w = -math.sqrt(max(1 - x*x - y*y - z*z, 0))
	return x, y, z, w

def optscale(scale):
	x, y, z = scale
	if abs(x) - 1 > 0.001: return x, y, z
	if abs(y) - 1 > 0.001: return x, y, z
	if abs(z) - 1 > 0.001: return x, y, z
	return ()
	#return x, y, z

def fmtv(v): return " ".join(["%g" % x for x in v])
def fmtb(v): return " ".join(["%g" % (x/255.0) for x in v])
def fmtp(v): return " ".join(["%g" % x for x in v])

def dump_joints(file, text, num_joints, ofs_joints):
	file.seek(ofs_joints)
	jointlist = []
	for x in range(num_joints):
		if iqmver == 1:
			joint = struct.unpack("<Ii9f", file.read(11*4))
		else:
			joint = struct.unpack("<Ii10f", file.read(12*4))
		jointlist += (joint,)
	for joint in jointlist:
		name = cstr(text, joint[0])
		parent = joint[1]
		print "joint", name, parent
	for joint in jointlist:
		if iqmver == 1:
			pos = joint[2:5]
			rot = joint[5:8]
			scale = joint[8:11]
			print "pq", fmtp(pos + restorew(rot) + optscale(scale))
		else:
			pos = joint[2:5]
			rot = joint[5:9]
			scale = joint[9:12]
			print "pq", fmtp(pos + rot + optscale(scale))

def load_poses(file, num_poses, ofs_poses):
	file.seek(ofs_poses)
	poselist = []
	for x in range(num_poses):
		if iqmver == 1:
			pose = struct.unpack("<iI18f", file.read(20*4))
		else:
			pose = struct.unpack("<iI20f", file.read(22*4))
		poselist.append(pose)
	#print "pose list", len(poselist)
	#print poselist
	return poselist

def load_frames(file, num_frames, num_framechannels, ofs_frames):
	file.seek(ofs_frames)
	F = "<"+"H"*num_framechannels; S=2*num_framechannels
	framelist = []
	for x in range(num_frames):
		frame = struct.unpack(F, file.read(S))
		framelist.append(frame)
	return framelist

def dump_frame(poselist, frame):
	masktest = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x100]
	LEN = 9
	if iqmver > 1:
		masktest += [0x200]
		LEN = 10
	p = 0
	for pose in poselist:
		mask = pose[1]
		choffset = pose[2:2+LEN]
		chscale = pose[2+LEN:2+LEN+LEN]
		data = [x for x in choffset]
		for x in range(LEN):
			if mask & masktest[x]:
				data[x] += chscale[x] * frame[p]
				p += 1
		if iqmver == 1:
			pos = data[0:3]
			rot = [x for x in restorew(data[3:6])]
			scale = [x for x in optscale(data[6:9])]
		else:
			pos = data[0:3]
			rot = [x for x in data[3:7]]
			scale = [x for x in optscale(data[7:10])]
		print "pq", fmtp(pos + rot + scale)

def dump_anims(file, text, num_anims, ofs_anims, poses, frames):
	file.seek(ofs_anims)
	for x in range(num_anims):
		anim = struct.unpack("<3IfI", file.read(5*4))
		name = cstr(text, anim[0])
		first = anim[1]
		count = anim[2]
		print
		print "animation", name
		print "framerate", anim[3]
		if anim[4]: print "loop"
		for y in range(first, first+count):
			print
			print "frame"
			dump_frame(poses, frames[y])

def load_array(file, format, size, offset, count):
	if format != 1 and format != 7:
		print >>sys.stderr, "can only handle ubyte and float arrays"
		sys.exit(1)
	if format == 1: A="<"+"B"*size; S=1*size
	if format == 7: A="<"+"f"*size; S=4*size
	file.seek(offset)
	list = []
	for x in range(count):
		comp = struct.unpack(A, file.read(S))
		list.append(comp)
	return list

def load_verts(file, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	file.seek(ofs_vertexarrays)
	valist = []
	for x in range(num_vertexarrays):
		va = struct.unpack("<5I", file.read(5*4))
		valist += (va,)
	verts = [None] * 10
	for type, flags, format, size, offset in valist:
		print >>sys.stderr, "# vertex array: %s" % iqm_va_type[type]
		verts[type] = load_array(file, format, size, offset, num_vertexes)
	return verts

def load_tris(file, num_triangles, ofs_triangles, ofs_adjacency):
	file.seek(ofs_triangles)
	tris = []
	for x in range(num_triangles):
		tri = struct.unpack("<3I", file.read(3*4))
		tris.append(tri)
	return tris

def dump_verts(verts, first, count):
	for x in range(first, first+count):
		if verts[0]: print "vp", fmtv(verts[0][x])
		if verts[1]: print "vt", fmtv(verts[1][x])
		if verts[2]: print "vn", fmtv(verts[2][x])
		# automatically computed by "iqm" tool
		# if verts[3]: print "v3", fmtv(verts[3][x])
		if verts[4] and verts[5]:
			out = "vb"
			for y in range(4):
				out += " %d" % verts[4][x][y]
				out += " %g" % (verts[5][x][y]/255.0)
			print out
		if verts[6]:
			print "vc", fmtb(verts[6][x])
		if verts[7]: print "v7", fmtv(verts[7][x])
		if verts[8]: print "v8", fmtv(verts[8][x])
		if verts[9]: print "v9", fmtv(verts[9][x])

def dump_tris(tris, first, count, fv):
	for x in range(first, first+count):
		tri = tris[x]
		print "fm", tri[0]-fv, tri[1]-fv, tri[2]-fv

def dump_meshes(file, text, num_meshes, ofs_meshes, verts, tris):
	file.seek(ofs_meshes)
	for x in range(num_meshes):
		mesh = struct.unpack("<6I", file.read(6*4))
		name = cstr(text, mesh[0])
		material = cstr(text, mesh[1])
		v1, vnum, t1, tnum = mesh[2:]
		print
		print "mesh", name
		print "material", material
		dump_verts(verts, v1, vnum)
		dump_tris(tris, t1, tnum, v1)

def dump_iqm(file):
	global iqmver

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

	if magic != "INTERQUAKEMODEL\0":
		print >>sys.stderr, "Not an IQM file."
		sys.exit(1)

	iqmver = version

	print "# Inter-Quake Export (v%d)" % version

	print >>sys.stderr, "# %d meshes" % num_meshes
	print >>sys.stderr, "# %d vertex arrays" % num_vertexarrays
	print >>sys.stderr, "# %d vertices" % num_vertexes
	print >>sys.stderr, "# %d triangles (adjacency at %d)" % (num_triangles, ofs_adjacency)
	print >>sys.stderr, "# %d joints" % num_joints
	print >>sys.stderr, "# %d poses" % num_poses
	print >>sys.stderr, "# %d anims" % num_anims
	print >>sys.stderr, "# %d frames (bounds at %d)" % (num_frames, ofs_bounds)
	print >>sys.stderr, "# %d frame channels" % num_framechannels

	file.seek(ofs_text)
	text = file.read(num_text);

	dump_joints(file, text, num_joints, ofs_joints)
	if ofs_vertexarrays:
		verts = load_verts(file, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	if ofs_triangles:
		tris = load_tris(file, num_triangles, ofs_triangles, ofs_adjacency)
	if ofs_meshes:
		dump_meshes(file, text, num_meshes, ofs_meshes, verts, tris)
	poses = load_poses(file, num_poses, ofs_poses)
	frames = load_frames(file, num_frames, num_framechannels, ofs_frames)
	# bounds are auto-computed, no need to load
	dump_anims(file, text, num_anims, ofs_anims, poses, frames)

for arg in sys.argv[1:]:
	file = open(arg, "rb")
	dump_iqm(file)

