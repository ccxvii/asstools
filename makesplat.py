# Create texture splatting material:
#	blender -P makesplat.py -- splat.png tex0.png tex1.png tex2.png tex3.png
# 	blender -P makesplat.py -- tex0.png tex1.png tex2.png tex3.png

import bpy, os, sys
from bpy_extras.image_utils import load_image

def import_texture(path):
	print("importing texture", path)
	imgname = os.path.basename(path)
	if imgname in bpy.data.images:
		img = bpy.data.images[imgname]
	else:
		img = load_image(path, place_holder=True)
	texname = os.path.splitext(imgname)[0]
	if texname in bpy.data.textures:
		tex = bpy.data.textures[texname]
	else:
		tex = bpy.data.textures.new(texname, type='IMAGE')
		tex.image = img
		tex.use_alpha = True
	return tex

def setup_splat_material(mat, tex0, tex1, tex2, tex3, tex_splat=None, use_vcol=True):

	mat.diffuse_intensity = 1.0
	mat.diffuse_shader = 'LAMBERT'
	mat.specular_intensity = 0.0
	mat.specular_shader = 'BLINN'

	mat.use_nodes = True
	nodes = mat.node_tree.nodes
	links = mat.node_tree.links

	nodes.clear()
	links.clear()

	# Nodes

	n_out = nodes.new('OUTPUT')

	n_mat = nodes.new('MATERIAL')
	n_mat.material = mat

	n_geo_splat = nodes.new('GEOMETRY')
	n_geo_splat.name = n_geo_splat.label = "Splat"
	n_geo_splat.uv_layer = "splat"
	n_geo_splat.color_layer = "splat"

	if tex_splat:
		n_tex_splat = nodes.new('TEXTURE')
		n_tex_splat.texture = tex_splat
		n_tex_splat.name = n_tex_splat.label = 'TexSplat'

	n_sep_rgb = nodes.new('SEPRGB')

	n_geo_tex = nodes.new('GEOMETRY')
	n_geo_tex.uv_layer = 'UVMap'
	n_geo_tex.name = n_geo_tex.label = "TexCoord"

	n_tex_0 = nodes.new('TEXTURE')
	n_tex_1 = nodes.new('TEXTURE')
	n_tex_2 = nodes.new('TEXTURE')
	n_tex_3 = nodes.new('TEXTURE')

	n_tex_0.texture = tex0
	n_tex_1.texture = tex1
	n_tex_2.texture = tex2
	n_tex_3.texture = tex3

	n_tex_0.name = n_tex_0.label = 'Tex0'
	n_tex_1.name = n_tex_1.label = 'Tex1'
	n_tex_2.name = n_tex_2.label = 'Tex2'
	n_tex_3.name = n_tex_3.label = 'Tex3'

	n_mix_0 = nodes.new('MIX_RGB')
	n_mix_1 = nodes.new('MIX_RGB')
	n_mix_2 = nodes.new('MIX_RGB')

	n_tex_0.name = n_mix_0.label = 'Mix0'
	n_mix_1.name = n_mix_1.label = 'Mix1'
	n_mix_2.name = n_mix_2.label = 'Mix2'

	if use_vcol:
		n_vcol = nodes.new('GEOMETRY')
		n_vcol.color_layer = 'Col'
		n_vcol.name = n_vcol.label = 'Color'

		n_mul = nodes.new('MIX_RGB')
		n_mul.blend_type = 'MULTIPLY'
		n_mul.inputs[0].default_value = 1.0

	# Links

	if tex_splat:
		links.new(n_geo_splat.outputs["UV"], n_tex_splat.inputs[0])
		links.new(n_tex_splat.outputs["Color"], n_sep_rgb.inputs[0])
	else:
		links.new(n_geo_splat.outputs["Vertex Color"], n_sep_rgb.inputs[0])

	links.new(n_sep_rgb.outputs[0], n_mix_0.inputs[0])
	links.new(n_sep_rgb.outputs[1], n_mix_1.inputs[0])
	links.new(n_sep_rgb.outputs[2], n_mix_2.inputs[0])

	links.new(n_geo_tex.outputs["UV"], n_tex_0.inputs[0])
	links.new(n_geo_tex.outputs["UV"], n_tex_1.inputs[0])
	links.new(n_geo_tex.outputs["UV"], n_tex_2.inputs[0])
	links.new(n_geo_tex.outputs["UV"], n_tex_3.inputs[0])

	links.new(n_tex_0.outputs["Color"], n_mix_0.inputs[1])
	links.new(n_tex_1.outputs["Color"], n_mix_0.inputs[2])
	links.new(n_tex_2.outputs["Color"], n_mix_1.inputs[2])
	links.new(n_tex_3.outputs["Color"], n_mix_2.inputs[2])
	links.new(n_mix_0.outputs[0], n_mix_1.inputs[1])
	links.new(n_mix_1.outputs[0], n_mix_2.inputs[1])

	if use_vcol:
		links.new(n_mix_2.outputs[0], n_mul.inputs[1])
		links.new(n_vcol.outputs["Vertex Color"], n_mul.inputs[2])
		links.new(n_mul.outputs[0], n_mat.inputs["Color"])
	else:
		links.new(n_mix_2.outputs[0], n_mat.inputs["Color"])

	links.new(n_mat.outputs["Color"], n_out.inputs["Color"])

	# Layout

	n_mix_0.color = 0.9, 0.7, 0.7
	n_mix_1.color = 0.7, 0.9, 0.7
	n_mix_2.color = 0.7, 0.7, 0.9

	n_tex_0.color = 0.9, 0.9, 0.9
	n_tex_1.color = 0.9, 0.7, 0.7
	n_tex_2.color = 0.7, 0.9, 0.7
	n_tex_3.color = 0.7, 0.7, 0.9

	n_mix_0.use_custom_color = True
	n_mix_1.use_custom_color = True
	n_mix_2.use_custom_color = True

	n_tex_0.use_custom_color = True
	n_tex_1.use_custom_color = True
	n_tex_2.use_custom_color = True
	n_tex_3.use_custom_color = True

	n_geo_splat.location = -1, 3
	if tex_splat: n_tex_splat.location = 0, 3
	n_sep_rgb.location = 1, 3

	n_mix_0.location = 2, 2
	n_mix_1.location = 3, 2
	n_mix_2.location = 4, 2
	if use_vcol: n_mul.location = 5, 2

	n_geo_tex.location = -1, 1
	n_tex_0.location = 0, 1
	n_tex_1.location = 1, 1
	n_tex_2.location = 2, 1
	n_tex_3.location = 3, 1
	if use_vcol: n_vcol.location = 4, 1

	n_mat.location = 6, 2
	n_out.location = 7, 2

	for n in nodes:
		n.location = n.location[0] * 250, n.location[1] * 250

def import_splat_material(tex_path_0, tex_path_1, tex_path_2, tex_path_3, splat_path=None, use_vcol=True):
	splat = import_texture(splat_path) if splat_path else None
	tex0 = import_texture(tex_path_0)
	tex1 = import_texture(tex_path_1)
	tex2 = import_texture(tex_path_2)
	tex3 = import_texture(tex_path_3)
	mat = bpy.data.materials.new('SplatMaterial')
	setup_splat_material(mat, tex0, tex1, tex2, tex3, splat, use_vcol)

if __name__ == "__main__":
	if len(sys.argv) > 5 and sys.argv[-5] == '--':
		a, b, c, d = sys.argv[-5:]
		import_splat_material(a, b, c, d)
	elif len(sys.argv) > 6 and sys.argv[-6] == '--':
		splat, a, b, c, d = sys.argv[-5:]
		import_splat_material(a, b, c, d, splat_path=splat)
	else:
		a = "terrain/dirt1.png"
		b = "terrain/dirt2.png"
		c = "terrain/basegrass1.png"
		d = "terrain/rock.png"
		import_splat_material(a,b,c,d, splat_path="splat.png", use_vcol=True)
