#!/usr/bin/python

import sys, os

def load_material(filename):
	mtllib = {}
	curmtl = None
	for line in open(filename).readlines():
		line = line.split()
		if len(line) == 0 or line[0] == '#':
			pass
		elif line[0] == 'newmtl':
			curmtl = line[1]
			mtllib[curmtl] = {}
			mtllib[curmtl]['map_Kd'] = 'unknown.png'
		elif line[0] == 'map_Ka':
			mtllib[curmtl]['map_Ka'] = line[1].lower()
		elif line[0] == 'map_Ks':
			mtllib[curmtl]['map_Ks'] = line[1].lower()
		elif line[0] == 'map_Kd':
			mtllib[curmtl]['map_Kd'] = line[1].lower()
		elif line[0] == 'map_Ke':
			mtllib[curmtl]['map_Ke'] = line[1].lower()
		elif len(line) > 1 and curmtl:
			mtllib[curmtl][line[0]] = " ".join(line[1:])
	return mtllib

def remap_materials(mtllib):
	set = {}
	map = {}
	lib = {}
	for mtl in mtllib:
		tex = mtllib[mtl]['map_Kd']
		name = os.path.splitext(tex)[0].split('/')[-1].replace('-','_')
		if name in set:
			map[set[name]] = name + ",0"
			lib[name + ",0"] = mtllib[mtl]
			i = 1
			while '%s,%d' % (name, i) in set:
				i = i + 1
			name = '%s,%d' % (name, i)
		set[name] = mtl
		map[mtl] = name
		lib[name] = mtllib[mtl]
	return map, lib

def load_model(filename):
	mtlmap = {}
	mtllib = {}
	vertex = []
	texcoord = []
	normal = []
	group = {}

	curmtl = None
	curdir = os.path.dirname(filename)
	if curdir == '': curdir = '.'
	face = []

	for line in open(filename).readlines():
		line = line.split()
		if len(line) == 0 or line[0] == '#':
			pass
		elif line[0] == 'vt':
			u = float(line[1])
			v = float(line[2])
			texcoord.append((u,v))
		elif line[0] == 'vn':
			x = float(line[1])
			y = float(line[2])
			z = float(line[3])
			normal.append((x,y,z))
		elif line[0] == 'v':
			x = float(line[1])
			y = float(line[2])
			z = float(line[3])
			vertex.append((x,y,z))
		elif line[0] == 'f':
			f = []
			for ix in line[1:]:
				ix = ix.split('/')
				vx = int(ix[0])
				tx = int(ix[1]) if ix[1] else 1
				nx = int(ix[2]) if ix[2] else 1
				f.append((vx,tx,nx))
			face.append((curmtl, f))
		elif line[0] == 'mtllib':
			mtllib = load_material(curdir + '/' + line[1])
			mtlmap, mtllib = remap_materials(mtllib)
		elif line[0] == 'usemtl':
			curmtl = mtlmap[line[1]]
		elif line[0] == 'g':
			g = line[1]
			if not g in group:
				group[g] = []
			face = group[g]

	# only keep used materials
	newlib = {}
	for g in group:
		face = group[g]
		for f in face:
			mtl = f[0]
			if mtl not in newlib:
				newlib[mtl] = mtllib[mtl]
	mtllib = newlib

	print 'loaded', filename, len(vertex), len(texcoord), len(normal), len(group)

	return (mtllib, vertex, texcoord, normal, group)

def save_material(filename, mtllib):
	file = open(filename, "w")
	print >>file, "# Wavefront Material Library"
	print >>file, "# Created by objcrush"
	for name in sorted(mtllib):
		print >>file
		print >>file, 'newmtl %s' % name
		mtl = mtllib[name]
		for key in mtl:
			print >>file, key, mtl[key]
	file.close()

def save_model(filename, model):
	mtllib, vertex, texcoord, normal, group = model

	print 'saving', filename, len(vertex), len(texcoord), len(normal), len(group)

	mtlfile = os.path.splitext(filename)[0] + ".mtl"
	save_material(mtlfile, mtllib)

	file = open(filename, "w")
	print >>file, "# Wavefront Model"
	print >>file, "# Created by objcrush"
	print >>file
	print >>file, "mtllib", os.path.basename(mtlfile)

	print >>file
	for x, y, z in vertex:
		print >>file, 'v', x, y, z
	print >>file
	for u, v in texcoord:
		print >>file, 'vt', u, v
	print >>file
	for x, y, z in normal:
		print >>file, 'vn', x, y, z

	for g in sorted(group):
		print >>file
		print >>file, 'g', g
		face = group[g]

		# sort faces by material
		out = {}
		for f in face:
			mtl = f[0]
			if mtl not in out:
				out[mtl] = []
			line = 'f'
			for vx, tx, nx in f[1]:
				line += " %d/%d/%d" % (vx, tx, nx)
			out[mtl].append(line)

		keys = out.keys()
		keys.sort()
		for mtl in keys:
			print >>file, 'usemtl', mtl
			for line in out[mtl]:
				print >>file, line

def crush_model(model):
	mtllib, vertex, texcoord, normal, group = model

	newgroup = {}
	newpos = []
	newtex = []
	newnormal = []

	posmap = {}
	texmap = {}
	normalmap = {}

	for g in group:
		face = group[g]
		newface = []
		for mtl, f in face:
			newf = []
			for vx, tx, nx in f:
				x, y, z = vertex[vx-1]
				if not (x,y,z) in posmap:
					posmap[(x,y,z)] = len(newpos) + 1
					newpos.append((x,y,z))
				vx = posmap[(x,y,z)]

				u, v = texcoord[tx-1]	# 1-based index
				if not (u,v) in texmap:
					texmap[(u,v)] = len(newtex) + 1
					newtex.append((u,v))
				tx = texmap[(u,v)]

				x, y, z = normal[nx-1]
				if not (x,y,z) in normalmap:
					normalmap[(x,y,z)] = len(newnormal) + 1
					newnormal.append((x,y,z))
				nx = normalmap[(x,y,z)]

				newf.append((vx,tx,nx))
			newface.append((mtl, newf))
		newgroup[g] = newface

	print "crushed %d -> %d positions" % (len(vertex), len(newpos))
	print "crushed %d -> %d texcoords" % (len(texcoord), len(newtex))
	print "crushed %d -> %d normals" % (len(normal), len(newnormal))

	return (mtllib, newpos, newtex, newnormal, newgroup)

for arg in sys.argv[1:]:
	model = load_model(arg)
	model = crush_model(model)
	save_model("./crushed_" + os.path.basename(arg), model)
	#save_model(arg, model)
