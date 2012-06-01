#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <assert.h>

typedef float vec2[2];
typedef float vec3[3];
typedef float vec4[4];
typedef float mat4[16];

/* column-major 4x4 matrices, as in opengl */

#define A(row,col) a[(col<<2)+row]
#define B(row,col) b[(col<<2)+row]
#define M(row,col) m[(col<<2)+row]

static void mat_copy(mat4 p, const mat4 m)
{
	memcpy(p, m, sizeof(mat4));
}

static void mat_mul44(mat4 m, const mat4 a, const mat4 b)
{
	int i;
	for (i = 0; i < 4; i++) {
		const float ai0=A(i,0), ai1=A(i,1), ai2=A(i,2), ai3=A(i,3);
		M(i,0) = ai0 * B(0,0) + ai1 * B(1,0) + ai2 * B(2,0) + ai3 * B(3,0);
		M(i,1) = ai0 * B(0,1) + ai1 * B(1,1) + ai2 * B(2,1) + ai3 * B(3,1);
		M(i,2) = ai0 * B(0,2) + ai1 * B(1,2) + ai2 * B(2,2) + ai3 * B(3,2);
		M(i,3) = ai0 * B(0,3) + ai1 * B(1,3) + ai2 * B(2,3) + ai3 * B(3,3);
	}
}

static void mat_invert(mat4 out, const mat4 m)
{
	mat4 inv;
	float det;
	int i;

	inv[0] = m[5]*m[10]*m[15] - m[5]*m[11]*m[14] - m[9]*m[6]*m[15] +
		m[9]*m[7]*m[14] + m[13]*m[6]*m[11] - m[13]*m[7]*m[10];
	inv[4] = -m[4]*m[10]*m[15] + m[4]*m[11]*m[14] + m[8]*m[6]*m[15] -
		m[8]*m[7]*m[14] - m[12]*m[6]*m[11] + m[12]*m[7]*m[10];
	inv[8] = m[4]*m[9]*m[15] - m[4]*m[11]*m[13] - m[8]*m[5]*m[15] +
		m[8]*m[7]*m[13] + m[12]*m[5]*m[11] - m[12]*m[7]*m[9];
	inv[12] = -m[4]*m[9]*m[14] + m[4]*m[10]*m[13] + m[8]*m[5]*m[14] -
		m[8]*m[6]*m[13] - m[12]*m[5]*m[10] + m[12]*m[6]*m[9];
	inv[1] = -m[1]*m[10]*m[15] + m[1]*m[11]*m[14] + m[9]*m[2]*m[15] -
		m[9]*m[3]*m[14] - m[13]*m[2]*m[11] + m[13]*m[3]*m[10];
	inv[5] = m[0]*m[10]*m[15] - m[0]*m[11]*m[14] - m[8]*m[2]*m[15] +
		m[8]*m[3]*m[14] + m[12]*m[2]*m[11] - m[12]*m[3]*m[10];
	inv[9] = -m[0]*m[9]*m[15] + m[0]*m[11]*m[13] + m[8]*m[1]*m[15] -
		m[8]*m[3]*m[13] - m[12]*m[1]*m[11] + m[12]*m[3]*m[9];
	inv[13] = m[0]*m[9]*m[14] - m[0]*m[10]*m[13] - m[8]*m[1]*m[14] +
		m[8]*m[2]*m[13] + m[12]*m[1]*m[10] - m[12]*m[2]*m[9];
	inv[2] = m[1]*m[6]*m[15] - m[1]*m[7]*m[14] - m[5]*m[2]*m[15] +
		m[5]*m[3]*m[14] + m[13]*m[2]*m[7] - m[13]*m[3]*m[6];
	inv[6] = -m[0]*m[6]*m[15] + m[0]*m[7]*m[14] + m[4]*m[2]*m[15] -
		m[4]*m[3]*m[14] - m[12]*m[2]*m[7] + m[12]*m[3]*m[6];
	inv[10] = m[0]*m[5]*m[15] - m[0]*m[7]*m[13] - m[4]*m[1]*m[15] +
		m[4]*m[3]*m[13] + m[12]*m[1]*m[7] - m[12]*m[3]*m[5];
	inv[14] = -m[0]*m[5]*m[14] + m[0]*m[6]*m[13] + m[4]*m[1]*m[14] -
		m[4]*m[2]*m[13] - m[12]*m[1]*m[6] + m[12]*m[2]*m[5];
	inv[3] = -m[1]*m[6]*m[11] + m[1]*m[7]*m[10] + m[5]*m[2]*m[11] -
		m[5]*m[3]*m[10] - m[9]*m[2]*m[7] + m[9]*m[3]*m[6];
	inv[7] = m[0]*m[6]*m[11] - m[0]*m[7]*m[10] - m[4]*m[2]*m[11] +
		m[4]*m[3]*m[10] + m[8]*m[2]*m[7] - m[8]*m[3]*m[6];
	inv[11] = -m[0]*m[5]*m[11] + m[0]*m[7]*m[9] + m[4]*m[1]*m[11] -
		m[4]*m[3]*m[9] - m[8]*m[1]*m[7] + m[8]*m[3]*m[5];
	inv[15] = m[0]*m[5]*m[10] - m[0]*m[6]*m[9] - m[4]*m[1]*m[10] +
		m[4]*m[2]*m[9] + m[8]*m[1]*m[6] - m[8]*m[2]*m[5];

	det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
	assert (det != 0);
	det = 1.0 / det;
	for (i = 0; i < 16; i++)
		out[i] = inv[i] * det;
}

/* Transform a point (column vector) by a matrix: p = m * v */
static void mat_vec_mul(vec3 p, const mat4 m, const vec3 v)
{
	assert(p != v);
	p[0] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
	p[1] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
	p[2] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14];
}

static void mat_vec_mul_n(vec3 p, const mat4 m, const vec3 v)
{
	assert(p != v);
	p[0] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2];
	p[1] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2];
	p[2] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2];
}

/* Transform a normal (row vector) by a matrix: [px py pz] = v * m */
static void mat_vec_mul_t(vec3 p, const mat4 m, const vec3 v)
{
	assert(p != v);
	p[0] = v[0] * m[0] + v[1] * m[1] + v[2] * m[2];
	p[1] = v[0] * m[4] + v[1] * m[5] + v[2] * m[6];
	p[2] = v[0] * m[8] + v[1] * m[9] + v[2] * m[10];
}

static void vec_normalize(vec3 v)
{
	float d = sqrtf(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);
	if (d >= 0.00001) {
		d = 1 / d;
		v[0] *= d;
		v[1] *= d;
		v[2] *= d;
	} else {
		v[0] = v[1] = 0;
		v[2] = 1;
	}
}

static void quat_normalize(vec4 q)
{
	float d = sqrtf(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
	if (d >= 0.00001) {
		d = 1 / d;
		q[0] *= d;
		q[1] *= d;
		q[2] *= d;
		q[3] *= d;
	} else {
		q[0] = q[1] = q[2] = 0;
		q[3] = 1;
	}
}

static void mat_from_pose(mat4 m, const vec3 t, const vec4 q, const vec3 s)
{
	float x2 = q[0] + q[0];
	float y2 = q[1] + q[1];
	float z2 = q[2] + q[2];
	{
		float xx2 = q[0] * x2;
		float yy2 = q[1] * y2;
		float zz2 = q[2] * z2;
		M(0,0) = 1 - yy2 - zz2;
		M(1,1) = 1 - xx2 - zz2;
		M(2,2) = 1 - xx2 - yy2;
	}
	{
		float yz2 = q[1] * z2;
		float wx2 = q[3] * x2;
		M(2,1) = yz2 + wx2;
		M(1,2) = yz2 - wx2;
	}
	{
		float xy2 = q[0] * y2;
		float wz2 = q[3] * z2;
		M(1,0) = xy2 + wz2;
		M(0,1) = xy2 - wz2;
	}
	{
		float xz2 = q[0] * z2;
		float wy2 = q[3] * y2;
		M(0,2) = xz2 + wy2;
		M(2,0) = xz2 - wy2;
	}

	m[0] *= s[0]; m[4] *= s[1]; m[8] *= s[2];
	m[1] *= s[0]; m[5] *= s[1]; m[9] *= s[2];
	m[2] *= s[0]; m[6] *= s[1]; m[10] *= s[2];

	M(0,3) = t[0];
	M(1,3) = t[1];
	M(2,3) = t[2];

	M(3,0) = 0;
	M(3,1) = 0;
	M(3,2) = 0;
	M(3,3) = 1;
}

#define MAXBONE 256
#define MAXMESH 256

struct pose {
	vec3 translate;
	vec4 rotate;
	vec3 scale;
};

struct mesh {
	char name[256];
	char material[256];
	int first_tri, count_tri;
	int first_vert, count_vert;
};

struct model {
	int mesh_count, bone_count;
	struct mesh *mesh;

	int vertex_count, triangle_count;
	float *vp, *vn, *vt, *vc, *vbw;
	int *fm, *vbi;

	char bone_name[MAXBONE][256];
	int parent[MAXBONE];
	struct pose bind_pose[MAXBONE];
	mat4 bind_matrix[MAXBONE];
	mat4 abs_bind_matrix[MAXBONE];
	mat4 inv_bind_matrix[MAXBONE];
};

void calc_mul_matrix(mat4 *skin_matrix, mat4 *abs_pose_matrix, mat4 *inv_bind_matrix, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_mul44(skin_matrix[i], abs_pose_matrix[i], inv_bind_matrix[i]);
}

void calc_inv_matrix(mat4 *inv_bind_matrix, mat4 *abs_bind_matrix, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_invert(inv_bind_matrix[i], abs_bind_matrix[i]);
}

void calc_abs_matrix(mat4 *abs_pose_matrix, mat4 *pose_matrix, int *parent, int count)
{
	int i;
	for (i = 0; i < count; i++)
		if (parent[i] >= 0)
			mat_mul44(abs_pose_matrix[i], abs_pose_matrix[parent[i]], pose_matrix[i]);
		else
			mat_copy(abs_pose_matrix[i], pose_matrix[i]);
}

void calc_matrix_from_pose(mat4 *pose_matrix, struct pose *pose, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_from_pose(pose_matrix[i], pose[i].translate, pose[i].rotate, pose[i].scale);
}

#define IQE_MAGIC "# Inter-Quake Export"
#define MAXMESH 256

struct floatarray {
	int len, cap;
	float *data;
};

struct intarray {
	int len, cap;
	int *data;
};

// temp buffers are global so we can reuse them between models
static struct floatarray position = { 0, 0, NULL };
static struct floatarray normal = { 0, 0, NULL };
static struct floatarray texcoord = { 0, 0, NULL };
static struct floatarray color = { 0, 0, NULL };
static struct floatarray blendweight = { 0, 0, NULL };
static struct intarray blendindex = { 0, 0, NULL };
static struct intarray element = { 0, 0, NULL };

static inline void push_float(struct floatarray *a, float v)
{
	if (a->len + 1 >= a->cap) {
		a->cap = 600 + a->cap * 2;
		a->data = realloc(a->data, a->cap * sizeof(*a->data));
	}
	a->data[a->len++] = v;
}

static inline void push_int(struct intarray *a, int v)
{
	assert(v >= 0 && v < 65535);
	if (a->len + 1 >= a->cap) {
		a->cap = 600 + a->cap * 2;
		a->data = realloc(a->data, a->cap * sizeof(*a->data));
	}
	a->data[a->len++] = v;
}

static void add_position(float x, float y, float z)
{
	push_float(&position, x);
	push_float(&position, y);
	push_float(&position, z);
}

static void add_texcoord(float u, float v)
{
	push_float(&texcoord, u);
	push_float(&texcoord, v);
}

static void add_normal(float x, float y, float z)
{
	push_float(&normal, x);
	push_float(&normal, y);
	push_float(&normal, z);
}

static void add_color(float r, float g, float b, float a)
{
	push_float(&color, r);
	push_float(&color, g);
	push_float(&color, b);
	push_float(&color, a);
}

static void add_blend(int idx[4], float wgt[4])
{
	int i;
	for (i = 0; i < 4; i++) {
		push_int(&blendindex, idx[i]);
		push_float(&blendweight, wgt[i]);
	}
}

static void add_triangle(int a, int b, int c)
{
	push_int(&element, a);
	push_int(&element, b);
	push_int(&element, c);
}

static char *parsestring(char **stringp)
{
	char *start, *end, *s = *stringp;
	while (isspace(*s)) s++;
	if (*s == '"') {
		s++;
		start = end = s;
		while (*end && *end != '"') end++;
		if (*end) *end++ = 0;
	} else {
		start = end = s;
		while (*end && !isspace(*end)) end++;
		if (*end) *end++ = 0;
	}
	*stringp = end;
	return start;
}

static char *parseword(char **stringp)
{
	char *start, *end, *s = *stringp;
	while (isspace(*s)) s++;
	start = end = s;
	while (*end && !isspace(*end)) end++;
	if (*end) *end++ = 0;
	*stringp = end;
	return start;
}

static inline float parsefloat(char **stringp, float def)
{
	char *s = parseword(stringp);
	return *s ? atof(s) : def;
}

static inline int parseint(char **stringp, int def)
{
	char *s = parseword(stringp);
	return *s ? atoi(s) : def;
}

struct model *
load_iqe_model_from_memory(char *filename, unsigned char *data, int len)
{
	char *line, *next;
	struct model *model;
	struct mesh meshbuf[MAXMESH], *mesh = NULL;
	char bonename[MAXBONE][256];
	int boneparent[MAXBONE];
	struct pose posebuf[MAXBONE];
	int mesh_count = 0;
	int bone_count = 0;
	int pose_count = 0;
	int fm = 0;
	char *s, *sp;
	int i;

	position.len = 0;
	texcoord.len = 0;
	normal.len = 0;
	color.len = 0;
	blendindex.len = 0;
	blendweight.len = 0;
	element.len = 0;

	position.cap = 0;
	texcoord.cap = 0;
	normal.cap = 0;
	color.cap = 0;
	blendindex.cap = 0;
	blendweight.cap = 0;
	element.cap = 0;

	position.data = 0;
	texcoord.data = 0;
	normal.data = 0;
	color.data = 0;
	blendindex.data = 0;
	blendweight.data = 0;
	element.data = 0;

	if (memcmp(data, IQE_MAGIC, strlen(IQE_MAGIC))) {
		fprintf(stderr, "error: bad iqe magic: '%s'\n", filename);
		return NULL;
	}

	// data is zero-terminated!
	for (line = (char*)data; line; line = next) {
		next = strchr(line, '\n');
		if (next)
			*next++ = 0;

		sp = line;
		s = parseword(&sp);
		if (!s) {
			continue;
		} else if (!strcmp(s, "vp")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			float z = parsefloat(&sp, 0);
			add_position(x, y, z);
		} else if (!strcmp(s, "vt")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			add_texcoord(x, y);
		} else if (!strcmp(s, "vn")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			float z = parsefloat(&sp, 0);
			add_normal(x, y, z);
		} else if (!strcmp(s, "vc")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			float z = parsefloat(&sp, 0);
			float w = parsefloat(&sp, 1);
			add_color(x, y, z, w);
		} else if (!strcmp(s, "vb")) {
			int idx[4] = {0, 0, 0, 0};
			float wgt[4] = {1, 0, 0, 0};
			for (i = 0; i < 4; i++) {
				idx[i] = parseint(&sp, 0);
				wgt[i] = parsefloat(&sp, 0);
			}
			add_blend(idx, wgt);
		} else if (!strcmp(s, "fm")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, 0);
			add_triangle(x+fm, y+fm, z+fm);
		} else if (!strcmp(s, "fa")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, 0);
			add_triangle(x, y, z);
		} else if (!strcmp(s, "mesh")) {
			s = parsestring(&sp);
			if (mesh) {
				mesh->count_tri = element.len - mesh->first_tri;
				mesh->count_vert = position.len - mesh->first_vert;
				if (mesh->count_tri == 0)
					mesh_count--;
			}
			mesh = &meshbuf[mesh_count++];
			strcpy(mesh->name, s);
			strcpy(mesh->material, "unknown");
			mesh->first_tri = element.len;
			mesh->first_vert = position.len;
			mesh->count_tri = 0;
			fm = position.len / 3;
		} else if (!strcmp(s, "material")) {
			s = parsestring(&sp);
			if (mesh) {
				strcpy(mesh->material, s);
			}
		} else if (!strcmp(s, "joint")) {
			if (bone_count < MAXBONE) {
				char *name = parsestring(&sp);
				strcpy(bonename[bone_count], name);
				boneparent[bone_count] = parseint(&sp, -1);
				bone_count++;
			}
		} else if (!strcmp(s, "pq")) {
			if (pose_count < MAXBONE) {
				posebuf[pose_count].translate[0] = parsefloat(&sp, 0);
				posebuf[pose_count].translate[1] = parsefloat(&sp, 0);
				posebuf[pose_count].translate[2] = parsefloat(&sp, 0);
				posebuf[pose_count].rotate[0] = parsefloat(&sp, 0);
				posebuf[pose_count].rotate[1] = parsefloat(&sp, 0);
				posebuf[pose_count].rotate[2] = parsefloat(&sp, 0);
				posebuf[pose_count].rotate[3] = parsefloat(&sp, 1);
				posebuf[pose_count].scale[0] = parsefloat(&sp, 1);
				posebuf[pose_count].scale[1] = parsefloat(&sp, 1);
				posebuf[pose_count].scale[2] = parsefloat(&sp, 1);
				pose_count++;
			}
		}
		// TODO: "pm", "pa"
	}

	if (mesh) {
		mesh->count_tri = element.len - mesh->first_tri;
		mesh->count_vert = position.len - mesh->first_vert;
		if (mesh->count_tri == 0)
			mesh_count--;
	}

	model = malloc(sizeof *model);
	memset(model, 0, sizeof *model);

	model->mesh_count = mesh_count;
	model->mesh = malloc(mesh_count * sizeof(struct mesh));
	memcpy(model->mesh, meshbuf, mesh_count * sizeof(struct mesh));

	model->vertex_count = position.len / 3;
	model->triangle_count = element.len / 3;

	model->vp = position.data;
	model->vn = normal.data;
	model->vt = texcoord.data;
	model->vc = color.data;
	model->vbi = blendindex.data;
	model->vbw = blendweight.data;

	model->fm = element.data;

	if (bone_count > 0 && pose_count >= bone_count) {
		model->bone_count = bone_count;
		memcpy(model->bone_name, bonename, sizeof bonename); // XXX careful of size
		memcpy(model->parent, boneparent, sizeof boneparent);
		memcpy(model->bind_pose, posebuf, sizeof posebuf);
		calc_matrix_from_pose(model->bind_matrix, model->bind_pose, model->bone_count);
		calc_abs_matrix(model->abs_bind_matrix, model->bind_matrix, model->parent, model->bone_count);
		calc_inv_matrix(model->inv_bind_matrix, model->abs_bind_matrix, model->bone_count);
	}

	return model;
}

unsigned char *load_file(char *filename, int *lenp)
{
	unsigned char *data;
	int len;
	FILE *file = fopen(filename, "rb");
	if (!file) {
		return NULL;
	}
	fseek(file, 0, 2);
	len = ftell(file);
	fseek(file, 0, 0);
	data = malloc(len + 1);
	fread(data, 1, len, file);
	fclose(file);
	if (lenp) *lenp = len;
	data[len] = 0; // zero-terminate in case it's a text file that we use as a string
	return data;
}

struct model *
load_iqe_model(char *filename)
{
	int len;
	unsigned char *data = load_file(filename, &len);
	assert(data);
	return load_iqe_model_from_memory(filename, data, len);
}

void
save_iqe_model(struct model *model)
{
	int i, k, x;

	printf("# Inter-Quake Export\n");
	printf("\n");

	for (k = 0; k < model->bone_count; k++)
		printf("joint %s %d\n", model->bone_name[k], model->parent[k]);
	printf("\n");

	for (k = 0; k < model->bone_count; k++)
	{
		struct pose *p = model->bind_pose + k;
		printf("pq %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g\n",
			p->translate[0], p->translate[1], p->translate[2],
			p->rotate[0], p->rotate[1], p->rotate[2], p->rotate[3],
			p->scale[0], p->scale[1], p->scale[2]);
	}
	printf("\n");

	for (k = 0; k < model->mesh_count; k++)
	{
		int v0 = model->mesh[k].first_vert / 3;
		int v1 = v0 + model->mesh[k].count_vert / 3;
		int t0 = model->mesh[k].first_tri / 3;
		int t1 = t0 + model->mesh[k].count_tri / 3;
		printf("mesh %s\n", model->mesh[k].name);
		printf("material %s\n", model->mesh[k].material);
		for (i = v0; i < v1; i++) {
			printf("vp %.9g %.9g %.9g\n", model->vp[i*3+0], model->vp[i*3+1], model->vp[i*3+2]);
			if (model->vt)
				printf("vt %.9g %.9g\n", model->vt[i*2+0], model->vt[i*2+1]);
			if (model->vn)
				printf("vn %.9g %.9g %.9g\n", model->vn[i*3+0], model->vn[i*3+1], model->vn[i*3+2]);
			if (model->vc)
				printf("vc %.9g %.9g %.9g %.9g\n", model->vc[i*4+0], model->vc[i*4+1], model->vc[i*4+2], model->vc[i*4+3]);
			if (model->vbi && model->vbw) {
				printf("vb");
				for (x = 0; x < 4; x++)
					if (model->vbw[i*4+x] > 0)
						printf(" %d %.9g", model->vbi[i*4+x], model->vbw[i*4+x]);
				printf("\n");
			}
		}
		for (i = t0; i < t1; i++) {
			printf("fm %d %d %d\n",
				model->fm[i*3+0] - v0,
				model->fm[i*3+1] - v0,
				model->fm[i*3+2] - v0);
		}
	}
}

void
apply_pose(mat4 *dst_pose_matrix, struct model *dst, struct model *src)
{
	int i, k;
	for (i = 0; i < dst->bone_count; i++) {
		mat_copy(dst_pose_matrix[i], src->abs_bind_matrix[i]);
		for (k = 0; k < src->bone_count; k++) {
			if (!strcmp(dst->bone_name[i], src->bone_name[k])) {
				mat_copy(dst_pose_matrix[i], src->abs_bind_matrix[k]);
				dst->bind_pose[i] = src->bind_pose[k];
				break;
			}
		}
		if (k == src->bone_count)
			fprintf(stderr, "cannot find source pose for bone '%s'\n", dst->bone_name[i]);
	}
}

void
apply_skin(struct model *model, mat4 *skin_matrix)
{
	vec3 p[4];
	vec3 n[4];
	int i, k, x;

	for (i = 0; i < model->vertex_count; i++) {
		float *vp = model->vp + 3 * i;
		float *vn = model->vn + 3 * i;
		float *vbw = model->vbw + 4 * i;
		int *vbi = model->vbi + 4 * i;

		for (x = 0; x < 4; x++) {
			mat_vec_mul(p[x], skin_matrix[vbi[x]], vp);
			mat_vec_mul_n(n[x], skin_matrix[vbi[x]], vn);
		}

		for (x = 0; x < 3; x++) {
			vp[x] = p[0][x] * vbw[0] + p[1][x] * vbw[1] + p[2][x] * vbw[2] + p[3][x] * vbw[3];
			vn[x] = n[0][x] * vbw[0] + n[1][x] * vbw[1] + n[2][x] * vbw[2] + n[3][x] * vbw[3];
		}
	}
}

int
main(int argc, char **argv)
{
	struct model *mesh, *skel;

	mat4 abs_pose_matrix[MAXBONE];
	mat4 skin_matrix[MAXBONE];

	if (argc != 3) {
		fprintf(stderr, "usage: iqe-apply-pose model.iqe skeleton.iqe\n");
		return 1;
	}

	mesh = load_iqe_model(argv[1]);
	skel = load_iqe_model(argv[2]);

	// copy bind pose to bind_pose for saving
	// save new pose matrices in abs_pose_matrix for skinning
	apply_pose(abs_pose_matrix, mesh, skel);

	// compute skinning matrices
	calc_mul_matrix(skin_matrix, abs_pose_matrix, mesh->inv_bind_matrix, mesh->bone_count);

	// apply skinning to vp and vt
	apply_skin(mesh, skin_matrix);

	save_iqe_model(mesh);

	return 0;
}
