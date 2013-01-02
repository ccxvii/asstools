#!/usr/bin/env python3

import sys, math, struct

iqm_va_type = {
	0: "position",
	1: "texcoord",
	2: "normal",
	3: "tangent",
	4: "blendindexes",
	5: "blendweights",
	6: "color",
	7: "reserved7",
	8: "reserved8", 9: "reserved9", 10: "reserved10", 11: "reserved11",
	12: "reserved12", 13: "reserved13", 14: "reserved14", 15: "reserved15",
}

iqm_va_format = {
	0: 'byte',
	1: 'ubyte',
	2: 'short',
	3: 'ushort',
	4: 'int',
	5: 'uint',
	6: 'half',
	7: 'float',
	8: 'double',
}

def cstr(text, ofs):
	len = 0
	while text[ofs+len] != 0:
		len += 1
	return text[ofs:ofs+len].decode("utf-8", "ignore")

def optscale(scale):
	x, y, z = scale
	if abs(x - 1) > 0.0001: return x, y, z
	if abs(y - 1) > 0.0001: return x, y, z
	if abs(z - 1) > 0.0001: return x, y, z
	return ()

def fmtv(v): return " ".join(["%.9g" % x for x in v])
def fmtb(v): return " ".join(["%.9g" % (x/255.0) for x in v])
def fmtp(v): return " ".join(["%.9g" % x for x in v])

def quote(s):
	return "\"%s\"" % s

def dump_joints(out, file, text, num_joints, ofs_joints):
	file.seek(ofs_joints)
	jointlist = []
	for x in range(num_joints):
		joint = struct.unpack("<Ii10f", file.read(12*4))
		jointlist += (joint,)
	out.write("\n")
	for joint in jointlist:
		name = cstr(text, joint[0])
		parent = joint[1]
		out.write("joint %s %s\n" % (quote(name), parent))
	out.write("\n")
	for joint in jointlist:
		pos = joint[2:5]
		rot = joint[5:9]
		scale = joint[9:12]
		out.write("pq %s\n" % fmtp(pos + rot + optscale(scale)))

def load_poses(file, num_poses, ofs_poses):
	file.seek(ofs_poses)
	poselist = []
	for x in range(num_poses):
		pose = struct.unpack("<iI20f", file.read(22*4))
		poselist.append(pose)
	return poselist

def load_frames(file, num_frames, num_framechannels, ofs_frames):
	file.seek(ofs_frames)
	F = "<"+"H"*num_framechannels; S=2*num_framechannels
	framelist = []
	for x in range(num_frames):
		frame = struct.unpack(F, file.read(S))
		framelist.append(frame)
	return framelist

def dump_frame(out, poselist, frame):
	masktest = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200]
	p = 0
	for pose in poselist:
		mask = pose[1]
		choffset = pose[2:2+10]
		chscale = pose[2+10:2+10+10]
		data = [x for x in choffset]
		for x in range(10):
			if mask & masktest[x]:
				data[x] += chscale[x] * frame[p]
				p += 1
			pos = data[0:3]
			rot = [x for x in data[3:7]]
			scale = [x for x in optscale(data[7:10])]
		out.write("pq %s\n" % fmtp(pos + rot + scale))

def dump_anims(out, file, text, num_anims, ofs_anims, poses, frames):
	file.seek(ofs_anims)
	for x in range(num_anims):
		anim = struct.unpack("<3IfI", file.read(5*4))
		name = cstr(text, anim[0])
		first = anim[1]
		count = anim[2]
		out.write("\n")
		out.write("animation %s\n" % quote(name))
		out.write("framerate %g\n" % anim[3])
		if anim[4]: out.write("loop\n")
		for y in range(first, first+count):
			out.write("\nframe %d\n" % (y - first))
			dump_frame(out, poses, frames[y])

def load_array(file, format, size, offset, count):
	if format != 1 and format != 7:
		sys.stdout.write("can only handle ubyte and float arrays\n")
		sys.exit(1)
	if format == 1: A="<"+"B"*size; S=1*size
	if format == 7: A="<"+"f"*size; S=4*size
	file.seek(offset)
	list = []
	for x in range(count):
		comp = struct.unpack(A, file.read(S))
		list.append(comp)
	return list

def load_verts(out, file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	file.seek(ofs_vertexarrays)
	out.write("\n")
	custom = 16
	valist = []
	for x in range(num_vertexarrays):
		va = struct.unpack("<5I", file.read(5*4))
		valist += (va,)
	verts = [None] * (16+10)
	vafmt = [None] * (16+10)
	for type, flags, format, size, offset in valist:
		if type < 16:
			type_name = iqm_va_type[type]
		else:
			type_name = cstr(text, type - 16)
			type = custom
			custom = custom + 1
		vafmt[type] = format
		verts[type] = load_array(file, format, size, offset, num_vertexes)
		if type != 4 and format == 7: verts[type]
		if type >= 16: out.write("vertexarray %s %s %d %s\n" % (iqm_va_type[type], iqm_va_format[format], size, quote(type_name)))
		else: out.write("vertexarray %s %s %d\n" % (iqm_va_type[type], iqm_va_format[format], size))
	return vafmt, verts

def load_tris(file, num_triangles, ofs_triangles, ofs_adjacency):
	file.seek(ofs_triangles)
	tris = []
	for x in range(num_triangles):
		tri = struct.unpack("<3I", file.read(3*4))
		tris.append(tri)
	return tris

def dump_verts(out, vafmt, verts, first, count):
	for x in range(first, first+count):
		if verts[0]: out.write("vp %s\n" % fmtv(verts[0][x]))
		if verts[2]: out.write("vn %s\n" % fmtv(verts[2][x]))
		if verts[3]: out.write("vx %s\n" % fmtv(verts[3][x]))
		if verts[1]: out.write("vt %s\n" % fmtv(verts[1][x]))
		if verts[6]: out.write("vc %s\n" % fmtb(verts[6][x]))
		if verts[4] and verts[5]:
			buf = "vb"
			for y in range(4):
				if verts[5][x][y] > 0:
					buf += " %d" % verts[4][x][y]
					buf += " %.9g" % (verts[5][x][y]/255.0)
			out.write(buf + "\n")
		for i in range(16, 16+10):
			if verts[i] and vafmt[i] == 1: out.write("v%d %s\n" % (i-16, fmtb(verts[i][x])))
			if verts[i] and vafmt[i] == 7: out.write("v%d %s\n" % (i-16, fmtv(verts[i][x])))

def dump_tris(out, tris, first, count, fv):
	for x in range(first, first+count):
		tri = tris[x]
		out.write("fm %d %d %d\n" % (tri[0]-fv, tri[1]-fv, tri[2]-fv))

def dump_meshes(out, file, text, num_meshes, ofs_meshes, vafmt, verts, tris):
	file.seek(ofs_meshes)
	for x in range(num_meshes):
		mesh = struct.unpack("<6I", file.read(6*4))
		name = cstr(text, mesh[0])
		material = cstr(text, mesh[1])
		v1, vnum, t1, tnum = mesh[2:]
		out.write("\n")
		out.write("mesh %s\n" % quote(name))
		out.write("material %s\n" % quote(material))
		dump_verts(out, vafmt, verts, v1, vnum)
		dump_tris(out, tris, t1, tnum, v1)

def dump_comment(out, file, num_comment, ofs_comment):
	file.seek(ofs_comment)
	comment = file.read(num_comment)
	comment = cstr(comment, 0)
	out.write("\ncomment\n")
	out.write(comment)

def dump_iqm(out, file):
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
		sys.stderr.write("Not an IQM file (%s)\n" % repr(magic))
		sys.exit(1)

	if version != 2:
		sys.stderr.write("Not an IQMv2 file.\n")
		sys.exit(1)

	out.write("# Inter-Quake Export\n")

	file.seek(ofs_text)
	text = file.read(num_text)

	if ofs_joints:
		dump_joints(out, file, text, num_joints, ofs_joints)
	if ofs_vertexarrays:
		vafmt, verts = load_verts(out, file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	if ofs_triangles:
		tris = load_tris(file, num_triangles, ofs_triangles, ofs_adjacency)
	if ofs_meshes:
		dump_meshes(out, file, text, num_meshes, ofs_meshes, vafmt, verts, tris)
	poses = load_poses(file, num_poses, ofs_poses)
	frames = load_frames(file, num_frames, num_framechannels, ofs_frames)
	# bounds are auto-computed, no need to load
	dump_anims(out, file, text, num_anims, ofs_anims, poses, frames)

	if ofs_comment:
		dump_comment(out, file, num_comment, ofs_comment)

for arg in sys.argv[1:]:
	file = open(arg, "rb")
	dump_iqm(sys.stdout, file)

