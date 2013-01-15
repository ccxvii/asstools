#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <assert.h>
#include <math.h>

#ifdef __APPLE__
#include <OpenGL/OpenGL.h>
#include <GLUT/glut.h>
#else
#include <GL/gl.h>
#include <GL/freeglut.h>
#endif

#ifndef GL_GENERATE_MIPMAP
#define GL_GENERATE_MIPMAP 0x8191
#endif

#ifndef GL_MULTISAMPLE
#define GL_MULTISAMPLE 0x809D
#endif

#ifndef GL_SAMPLE_ALPHA_TO_COVERAGE
#define GL_SAMPLE_ALPHA_TO_COVERAGE 0x809E
#endif

#define MIN(a,b) ((a) < (b) ? (a) : (b))
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define CLAMP(x,a,b) MIN(MAX(x,a),b)

/*
 * Some vector and matrix math.
 */

typedef float vec3[3];
typedef float vec4[4];
typedef float mat4[16];

struct pose {
	vec3 position;
	vec4 rotation;
	vec3 scale;
};

#define A(row,col) a[(col<<2)+row]
#define B(row,col) b[(col<<2)+row]
#define M(row,col) m[(col<<2)+row]

void mat_copy(mat4 p, const mat4 m)
{
	memcpy(p, m, sizeof(mat4));
}

void mat_mul(mat4 m, const mat4 a, const mat4 b)
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

void mat_invert(mat4 out, const mat4 m)
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


void mat_from_pose(mat4 m, const vec3 t, const vec4 q, const vec3 s)
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

#undef A
#undef B
#undef M

void vec_scale(vec3 p, const vec3 v, float s)
{
	p[0] = v[0] * s;
	p[1] = v[1] * s;
	p[2] = v[2] * s;
}

void vec_add(vec3 p, const vec3 a, const vec3 b)
{
	p[0] = a[0] + b[0];
	p[1] = a[1] + b[1];
	p[2] = a[2] + b[2];
}

void mat_vec_mul(vec3 p, const mat4 m, const vec3 v)
{
	assert(p != v);
	p[0] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
	p[1] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
	p[2] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14];
}

void mat_vec_mul_n(vec3 p, const mat4 m, const vec3 v)
{
	assert(p != v);
	p[0] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2];
	p[1] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2];
	p[2] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2];
}

static void calc_mul_matrix(mat4 *skin_matrix, mat4 *abs_pose_matrix, mat4 *inv_bind_matrix, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_mul(skin_matrix[i], abs_pose_matrix[i], inv_bind_matrix[i]);
}

static void calc_inv_matrix(mat4 *inv_bind_matrix, mat4 *abs_bind_matrix, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_invert(inv_bind_matrix[i], abs_bind_matrix[i]);
}

static void calc_abs_matrix(mat4 *abs_pose_matrix, mat4 *pose_matrix, int *parent, int count)
{
	int i;
	for (i = 0; i < count; i++)
		if (parent[i] >= 0)
			mat_mul(abs_pose_matrix[i], abs_pose_matrix[parent[i]], pose_matrix[i]);
		else
			mat_copy(abs_pose_matrix[i], pose_matrix[i]);
}

static void calc_matrix_from_pose(mat4 *pose_matrix, struct pose *pose, int count)
{
	int i;
	for (i = 0; i < count; i++)
		mat_from_pose(pose_matrix[i], pose[i].position, pose[i].rotation, pose[i].scale);
}

/*
 * Use Sean Barrett's excellent stb_image to load textures.
 */

#define STBI_NO_HDR
#include "stb_image.c"

char basedir[2000];

unsigned char checker_data[256*256];
unsigned int checker_texture = 0;

void initchecker(void)
{
	int x, y, i = 0;
	for (y = 0; y < 256; y++) {
		for (x = 0; x < 256; x++) {
			int k = ((x>>5) & 1) ^ ((y>>5) & 1);
			checker_data[i++] = k ? 255 : 192;
		}
	}
	glGenTextures(1, &checker_texture);
	glBindTexture(GL_TEXTURE_2D, checker_texture);
	glTexParameteri(GL_TEXTURE_2D, GL_GENERATE_MIPMAP, GL_TRUE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexImage2D(GL_TEXTURE_2D, 0, 1, 256, 256, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, checker_data);
}

void lowerstring(char *s)
{
	while (*s) { *s = tolower(*s); s++; }
}

unsigned int loadtexture(char *filename)
{
	unsigned int texture;
	unsigned char *image;
	int w, h, n, intfmt = 0, fmt = 0;

	image = stbi_load(filename, &w, &h, &n, 0);
	if (!image) {
		lowerstring(filename);
		image = stbi_load(filename, &w, &h, &n, 0);
		if (!image) {
			fprintf(stderr, "cannot load texture '%s'\n", filename);
			return 0;
		}
	}

	if (n == 1) { intfmt = fmt = GL_LUMINANCE; }
	if (n == 2) { intfmt = fmt = GL_LUMINANCE_ALPHA; }
	if (n == 3) { intfmt = fmt = GL_RGB; }
	if (n == 4) { intfmt = fmt = GL_RGBA; }

	glGenTextures(1, &texture);
	glBindTexture(GL_TEXTURE_2D, texture);
	glTexParameteri(GL_TEXTURE_2D, GL_GENERATE_MIPMAP, GL_TRUE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexImage2D(GL_TEXTURE_2D, 0, intfmt, w, h, 0, fmt, GL_UNSIGNED_BYTE, image);
	//glGenerateMipmap(GL_TEXTURE_2D);

	free(image);

	return texture;
}

unsigned int loadmaterial(char *material)
{
	int texture;
	char filename[2000], *s;
	s = strrchr(material, '+');
	if (s) material = s + 1;
	s = strrchr(material, '/');
	if (!s) s = strrchr(material, '\\');
	if (!s) s = material; else s++;
	strcpy(filename, basedir);
	strcat(filename, s);
	strcat(filename, ".png");
	texture = loadtexture(filename);
	if (texture)
		return texture;
	strcpy(filename, basedir);
	strcat(filename, "textures/");
	strcat(filename, s);
	strcat(filename, ".png");
	texture = loadtexture(filename);
	if (texture)
		return texture;
	return 0;
}

/*
 * IQE loading and drawing
 */

#define IQE_MAGIC "# Inter-Quake Export"
#define MAXMESH 4096
#define MAXBONE 256

struct floatarray {
	int len, cap;
	float *data;
};

struct intarray {
	int len, cap;
	unsigned int *data;
};

struct mesh {
	unsigned int texture;
	int first, count;
};

struct anim {
	char *name;
	int len, cap;
	struct frame *data;
	struct anim *next, *prev;
};

struct frame {
	struct pose pose[MAXBONE];
};

static struct floatarray position = { 0, 0, NULL };
static struct floatarray normal = { 0, 0, NULL };
static struct floatarray texcoord = { 0, 0, NULL };
static struct intarray blendindex = { 0, 0, NULL };
static struct floatarray blendweight = { 0, 0, NULL };
static struct intarray element = { 0, 0, NULL };

static float *aposition = NULL;
static float *anormal = NULL;

static struct mesh mesh[MAXMESH];
static int mesh_count = 0;

static int bone_count = 0;
static int bone_parent[MAXBONE];
static char *bone_name[MAXBONE];
static struct pose bindpose[MAXBONE];

static struct anim *anim = NULL;

static mat4 loc_bind_matrix[MAXBONE];
static mat4 abs_bind_matrix[MAXBONE];
static mat4 inv_bind_matrix[MAXBONE];
static mat4 loc_pose_matrix[MAXBONE];
static mat4 abs_pose_matrix[MAXBONE];
static mat4 skin_matrix[MAXBONE];

static float bboxmin[3], bboxmax[3];

static inline void pushfloat(struct floatarray *a, float v)
{
	if (a->len + 1 >= a->cap) {
		a->cap = 600 + a->cap * 2;
		a->data = realloc(a->data, a->cap * sizeof(*a->data));
	}
	a->data[a->len++] = v;
}

static inline void pushint(struct intarray *a, int v)
{
	if (a->len + 1 >= a->cap) {
		a->cap = 600 + a->cap * 2;
		a->data = realloc(a->data, a->cap * sizeof(*a->data));
	}
	a->data[a->len++] = v;
}

static inline struct pose *newframe(struct anim *a)
{
	if (a->len + 1 >= a->cap) {
		a->cap = 128 + a->cap * 2;
		a->data = realloc(a->data, a->cap * sizeof(*a->data));
	}
	return a->data[a->len++].pose;
}

static void addposition(float x, float y, float z)
{
	pushfloat(&position, x);
	pushfloat(&position, y);
	pushfloat(&position, z);
}

static void addtexcoord(float u, float v)
{
	pushfloat(&texcoord, u);
	pushfloat(&texcoord, v);
}

static void addnormal(float x, float y, float z)
{
	pushfloat(&normal, x);
	pushfloat(&normal, y);
	pushfloat(&normal, z);
}

static void addblend(int a, int b, int c, int d, float x, float y, float z, float w)
{
	float total = x + y + z + w;
	pushint(&blendindex, a);
	pushint(&blendindex, b);
	pushint(&blendindex, c);
	pushint(&blendindex, d);
	pushfloat(&blendweight, x / total);
	pushfloat(&blendweight, y / total);
	pushfloat(&blendweight, z / total);
	pushfloat(&blendweight, w / total);
}

static void addtriangle(int a, int b, int c)
{
	// flip triangle winding
	pushint(&element, c);
	pushint(&element, b);
	pushint(&element, a);
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

static void loadmodel(char *filename)
{
	FILE *fp;
	char line[256];
	int material = 0;
	int first = 0;
	int fm = 0;
	char *s, *sp;
	int i, k;

	struct pose *pose = bindpose;
	int pose_count = 0;

	fprintf(stderr, "loading iqe model '%s'\n", filename);

	bboxmin[0] = bboxmin[1] = bboxmin[2] = 1e10;
	bboxmax[0] = bboxmax[1] = bboxmax[2] = -1e10;

	position.len = 0;
	texcoord.len = 0;
	normal.len = 0;
	element.len = 0;

	fp = fopen(filename, "r");
	if (!fp) {
		fprintf(stderr, "error: cannot load model '%s'\n", filename);
		exit(1);
	}

	if (!fgets(line, sizeof line, fp)) {
		fprintf(stderr, "cannot load %s: read error\n", filename);
		exit(1);
	}

	if (memcmp(line, IQE_MAGIC, strlen(IQE_MAGIC))) {
		fprintf(stderr, "cannot load %s: bad iqe magic\n", filename);
		exit(1);
	}

	while (1) {
		if (!fgets(line, sizeof line, fp))
			break;
		sp = line;

		s = parseword(&sp);
		if (!s) {
			continue;
		} else if (!strcmp(s, "vp")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			float z = parsefloat(&sp, 0);
			bboxmin[0] = MIN(bboxmin[0], x); bboxmax[0] = MAX(bboxmax[0], x);
			bboxmin[1] = MIN(bboxmin[1], y); bboxmax[1] = MAX(bboxmax[1], y);
			bboxmin[2] = MIN(bboxmin[2], z); bboxmax[2] = MAX(bboxmax[2], z);
			addposition(x, y, z);
		} else if (!strcmp(s, "vt")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			addtexcoord(x, y);
		} else if (!strcmp(s, "vn")) {
			float x = parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			float z = parsefloat(&sp, 0);
			addnormal(x, y, z);
		} else if (!strcmp(s, "vb")) {
			int a = parseint(&sp, 0);
			float x = parsefloat(&sp, 1);
			int b = parseint(&sp, 0);
			float y = parsefloat(&sp, 0);
			int c = parseint(&sp, 0);
			float z = parsefloat(&sp, 0);
			int d = parseint(&sp, 0);
			float w = parsefloat(&sp, 0);
			addblend(a, b, c, d, x, y, z, w);
		} else if (!strcmp(s, "fm")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, -1);
			while (z > -1) {
				addtriangle(x+fm, y+fm, z+fm);
				y = z;
				z = parseint(&sp, -1);
			}
		} else if (!strcmp(s, "fa")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, -1);
			while (z > -1) {
				addtriangle(x, y, z);
				y = z;
				z = parseint(&sp, -1);
			}
		} else if (!strcmp(s, "joint")) {
			if (bone_count < MAXBONE) {
				bone_name[bone_count] = strdup(parsestring(&sp));
				bone_parent[bone_count] = parseint(&sp, -1);
				bone_count++;
			}
		} else if (!strcmp(s, "pq")) {
			if (pose_count < MAXBONE) {
				pose[pose_count].position[0] = parsefloat(&sp, 0);
				pose[pose_count].position[1] = parsefloat(&sp, 0);
				pose[pose_count].position[2] = parsefloat(&sp, 0);
				pose[pose_count].rotation[0] = parsefloat(&sp, 0);
				pose[pose_count].rotation[1] = parsefloat(&sp, 0);
				pose[pose_count].rotation[2] = parsefloat(&sp, 0);
				pose[pose_count].rotation[3] = parsefloat(&sp, 1);
				pose[pose_count].scale[0] = parsefloat(&sp, 1);
				pose[pose_count].scale[1] = parsefloat(&sp, 1);
				pose[pose_count].scale[2] = parsefloat(&sp, 1);
				pose_count++;
			}
		} else if (!strcmp(s, "animation")) {
			struct anim *head = anim;
			anim = malloc(sizeof(*anim));
			anim->name = strdup(parsestring(&sp));
			anim->len = anim->cap = 0;
			anim->data = NULL;
			if (head) head->prev = anim;
			anim->next = head;
			anim->prev = NULL;
		} else if (!strcmp(s, "frame")) {
			pose = newframe(anim);
			pose_count = 0;
		} else if (!strcmp(s, "mesh")) {
			if (element.len > first) {
				mesh[mesh_count].first = first;
				mesh[mesh_count].count = element.len - first;
				mesh[mesh_count].texture = material;
				mesh_count++;
			}
			first = element.len;
			fm = position.len / 3;
		} else if (!strcmp(s, "material")) {
			s = parsestring(&sp);
			material = loadmaterial(s);
		}
	}

	if (element.len > first) {
		mesh[mesh_count].first = first;
		mesh[mesh_count].count = element.len - first;
		mesh[mesh_count].texture = material;
		mesh_count++;
	}

	if (bone_count > 0) {
		calc_matrix_from_pose(loc_bind_matrix, bindpose, bone_count);
		calc_abs_matrix(abs_bind_matrix, loc_bind_matrix, bone_parent, bone_count);
		calc_inv_matrix(inv_bind_matrix, abs_bind_matrix, bone_count);
	}

	if (bone_count > 0) {
		for (i = 0; i < bone_count; i++) {
			float x = abs_bind_matrix[i][12];
			float y = abs_bind_matrix[i][13];
			float z = abs_bind_matrix[i][14];
			bboxmin[0] = MIN(bboxmin[0], x); bboxmax[0] = MAX(bboxmax[0], x);
			bboxmin[1] = MIN(bboxmin[1], y); bboxmax[1] = MAX(bboxmax[1], y);
			bboxmin[2] = MIN(bboxmin[2], z); bboxmax[2] = MAX(bboxmax[2], z);
		}
		for (k = 0; anim && k < anim->len; k++) {
			pose = anim->data[k].pose;
			calc_matrix_from_pose(loc_pose_matrix, pose, bone_count);
			calc_abs_matrix(abs_pose_matrix, loc_pose_matrix, bone_parent, bone_count);
			for (i = 0; i < bone_count; i++) {
				float x = abs_pose_matrix[i][12];
				float y = abs_pose_matrix[i][13];
				float z = abs_pose_matrix[i][14];
				bboxmin[0] = MIN(bboxmin[0], x); bboxmax[0] = MAX(bboxmax[0], x);
				bboxmin[1] = MIN(bboxmin[1], y); bboxmax[1] = MAX(bboxmax[1], y);
				bboxmin[2] = MIN(bboxmin[2], z); bboxmax[2] = MAX(bboxmax[2], z);
			}
		}
		memcpy(abs_pose_matrix, abs_bind_matrix, sizeof abs_pose_matrix);
	}

	if (mesh_count == 0 && bone_count == 0) {
		bboxmin[0] = bboxmin[1] = bboxmin[2] = -2;
		bboxmax[0] = bboxmax[1] = bboxmax[2] = 2;
	}

	fprintf(stderr, "\t%d meshes; %d vertices; %d triangles; %d bones\n",
			mesh_count, position.len/3, element.len/3, bone_count);
}

void animatemodel(struct anim *anim, int frame)
{
	struct pose *pose;
	frame = CLAMP(frame, 0, anim->len-1);

	pose = anim->data[frame].pose;
	calc_matrix_from_pose(loc_pose_matrix, pose, bone_count);
	calc_abs_matrix(abs_pose_matrix, loc_pose_matrix, bone_parent, bone_count);
	calc_mul_matrix(skin_matrix, abs_pose_matrix, inv_bind_matrix, bone_count);

	if (!aposition) aposition = malloc(sizeof(float) * position.len);
	if (!anormal) anormal = malloc(sizeof(float) * normal.len);

	unsigned int *bi = blendindex.data;
	float *bw = blendweight.data;
	float *sp = position.data;
	float *sn = normal.data;
	float *dp = aposition;
	float *dn = anormal;
	int n = position.len / 3;

	while (n--) {
		int i;
		dp[0] = dp[1] = dp[2] = 0;
		dn[0] = dn[1] = dn[2] = 0;
		for (i = 0; i < 4; i++) {
			vec3 tp, tn;
			mat_vec_mul(tp, skin_matrix[bi[i]], sp);
			mat_vec_mul_n(tn, skin_matrix[bi[i]], sn);
			vec_scale(tp, tp, bw[i]);
			vec_scale(tn, tn, bw[i]);
			vec_add(dp, dp, tp);
			vec_add(dn, dn, tn);
		}
		bi += 4; bw += 4;
		sp += 3; sn += 3;
		dp += 3; dn += 3;
	}
}

static int haschildren(int *parent, int count, int x)
{
	int i;
	for (i = x; i < count; i++)
		if (parent[i] == x)
			return 1;
	return 0;
}

void drawskeleton(void)
{
	vec3 x = { 0, 0.1, 0 };
	int i;
	glBegin(GL_LINES);
	for (i = 0; i < bone_count; i++) {
		float *a = abs_pose_matrix[i];
		if (bone_parent[i] >= 0) {
			float *b = abs_pose_matrix[bone_parent[i]];
			glColor4f(1, 1, 1, 1);
			glVertex3f(a[12], a[13], a[14]);
			glVertex3f(b[12], b[13], b[14]);
		} else {
			glColor4f(1, 1, 1, 1);
			glVertex3f(a[12], a[13], a[14]);
			glColor4f(0, 0, 0, 1);
			glVertex3f(0, 0, 0);
		}
		if (!haschildren(bone_parent, bone_count, i)) {
			vec3 b;
			mat_vec_mul(b, abs_pose_matrix[i], x);
			glColor4f(1, 1, 1, 1);
			glVertex3f(a[12], a[13], a[14]);
			glColor4f(0, 0, 0, 1);
			glVertex3f(b[0], b[1], b[2]);
		}
	}
	glEnd();
}

void drawmodel(void)
{
	int i;

	glEnableClientState(GL_VERTEX_ARRAY);
	if (texcoord.len) glEnableClientState(GL_TEXTURE_COORD_ARRAY);
	if (normal.len) glEnableClientState(GL_NORMAL_ARRAY);

	glVertexPointer(3, GL_FLOAT, 0, aposition ? aposition : position.data);
	glNormalPointer(GL_FLOAT, 0, anormal ? anormal : normal.data);
	glTexCoordPointer(2, GL_FLOAT, 0, texcoord.data);

	for (i = 0; i < mesh_count; i++) {
		if (mesh[i].texture > 0) {
			glColor4f(1, 1, 1, 1);
			glBindTexture(GL_TEXTURE_2D, mesh[i].texture);
		} else {
			glColor4f(0.9, 0.7, 0.7, 1);
			glBindTexture(GL_TEXTURE_2D, checker_texture);
		}
		glDrawElements(GL_TRIANGLES, mesh[i].count, GL_UNSIGNED_INT, element.data + mesh[i].first);
	}

	glDisableClientState(GL_VERTEX_ARRAY);
	glDisableClientState(GL_TEXTURE_COORD_ARRAY);
	glDisableClientState(GL_NORMAL_ARRAY);
}

float measuremodel(float center[3])
{
	float dx, dy, dz;

	center[0] = (bboxmin[0] + bboxmax[0]) / 2;
	center[1] = (bboxmin[1] + bboxmax[1]) / 2;
	center[2] = (bboxmin[2] + bboxmax[2]) / 2;

	dx = MAX(center[0] - bboxmin[0], bboxmax[0] - center[0]);
	dy = MAX(center[1] - bboxmin[1], bboxmax[1] - center[1]);
	dz = MAX(center[2] - bboxmin[2], bboxmax[2] - center[2]);

	return sqrt(dx*dx + dy*dy + dz*dz);
}

/*
 * Boring UI and GLUT hooks.
 */

#define DIABLO 36.8698976	// 4:3 isometric view
#define ISOMETRIC 35.264	// true isometric view
#define DIMETRIC 30		// 2:1 'isometric' as seen in pixel art

int showhelp = 0;
int doplane = 0;
int doalpha = 0;
int dowire = 0;
int dotexture = 1;
int dobackface = 0;
int dotwosided = 0;
int doperspective = 1;
int doskeleton = 0;
int doplay = 0;

unsigned int curframe = 0;
struct anim *curanim = NULL;
float curtime = 0;
int lasttime = 0;

int screenw = 800, screenh = 600;
int mousex, mousey, mouseleft = 0, mousemiddle = 0, mouseright = 0;

int gridsize = 3;
float mindist = 1;
float maxdist = 10;

float light_position[4] = { -1, -2, 2, 0 };

struct {
	float distance;
	float yaw;
	float pitch;
	float center[3];
} camera = { 3, 45, -DIMETRIC, { 0, 1, 0 } };

void perspective(float fov, float aspect, float znear, float zfar)
{
	fov = fov * 3.14159 / 360.0;
	fov = tan(fov) * znear;
	glFrustum(-fov * aspect, fov * aspect, -fov, fov, znear, zfar);
}

void orthogonal(float fov, float aspect, float znear, float zfar)
{
	glOrtho(-fov * aspect, fov * aspect, -fov, fov, znear, zfar);
}

void drawstring(float x, float y, char *s)
{
	glRasterPos2f(x+0.375, y+0.375);
	while (*s)
		//glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, *s++);
		glutBitmapCharacter(GLUT_BITMAP_8_BY_13, *s++);
}

void mouse(int button, int state, int x, int y)
{
	if (button == GLUT_LEFT_BUTTON) mouseleft = state == GLUT_DOWN;
	if (button == GLUT_MIDDLE_BUTTON) mousemiddle = state == GLUT_DOWN;
	if (button == GLUT_RIGHT_BUTTON) mouseright = state == GLUT_DOWN;
	mousex = x;
	mousey = y;
}

void motion(int x, int y)
{
	int dx = x - mousex;
	int dy = y - mousey;
	if (mouseleft) {
		camera.yaw -= dx * 0.3;
		camera.pitch -= dy * 0.2;
		if (camera.pitch < -85) camera.pitch = -85;
		if (camera.pitch > 85) camera.pitch = 85;
		if (camera.yaw < 0) camera.yaw += 360;
		if (camera.yaw > 360) camera.yaw -= 360;
	}
	if (mousemiddle || mouseright) {
		camera.distance += dy * 0.01 * camera.distance;
		if (camera.distance < mindist) camera.distance = mindist;
		if (camera.distance > maxdist) camera.distance = maxdist;
	}
	mousex = x;
	mousey = y;
	glutPostRedisplay();
}

void togglefullscreen(void)
{
	static int oldw = 100, oldh = 100;
	static int oldx = 0, oldy = 0;
	static int isfullscreen = 0;
	if (!isfullscreen) {
		oldw = screenw;
		oldh = screenh;
		oldx = glutGet(GLUT_WINDOW_X);
		oldy = glutGet(GLUT_WINDOW_Y);
		glutFullScreen();
	} else {
		glutPositionWindow(oldx, oldy);
		glutReshapeWindow(oldw, oldh);
	}
	isfullscreen = !isfullscreen;
}

void keyboard(unsigned char key, int x, int y)
{
	switch (key) {
	case 27: case 'q': exit(1); break;
	case 'h': case '?': showhelp = !showhelp; break;
	case 'f': togglefullscreen(); break;
	case 'i': doperspective = 0; camera.yaw = 45; camera.pitch = -DIMETRIC; break;
	case 'I': doperspective = 0; camera.yaw = 45; camera.pitch = -ISOMETRIC; break;
	case 'D': doperspective = 0; camera.yaw = 45; camera.pitch = -DIABLO; break;
	case 'p': doperspective = !doperspective; break;
	case 'g': doplane = !doplane; break;
	case 't': dotexture = !dotexture; break;
	case 'A': doalpha--; break;
	case 'a': doalpha++; break;
	case 'w': dowire = !dowire; break;
	case 'b': dobackface = !dobackface; break;
	case 'l': dotwosided = !dotwosided; break;
	case 'k': doskeleton = !doskeleton; break;
	case ' ': doplay = !doplay; break;
	case '0': curframe = 0; if (curanim) animatemodel(curanim, curframe); break;
	case ',': if (curanim) { curframe--; curframe %= curanim->len; animatemodel(curanim, curframe); } break;
	case '.': if (curanim) { curframe++; curframe %= curanim->len; animatemodel(curanim, curframe); } break;
	case '<':
		if (curanim && curanim->prev) {
			curanim = curanim->prev;
			curframe = 0;
			animatemodel(curanim, curframe);
		}
		break;
	case '>':
		if (curanim && curanim->next) {
			curanim = curanim->next;
			curframe = 0;
			animatemodel(curanim, curframe);
		}
		break;
	}

	if (doplay) {
		if (!curanim)
			curanim = anim;
		lasttime = glutGet(GLUT_ELAPSED_TIME);
	}

	glutPostRedisplay();
}

void special(int key, int x, int y)
{
	switch (key) {
	case GLUT_KEY_F4: exit(1); break;
	case GLUT_KEY_F1: showhelp = !showhelp; break;
	}
	glutPostRedisplay();
}

void reshape(int w, int h)
{
	screenw = w;
	screenh = h;
	glViewport(0, 0, w, h);
}

void display(void)
{
	char buf[256];
	int i;

	int thistime = glutGet(GLUT_ELAPSED_TIME);
	int timediff = thistime - lasttime;
	lasttime = thistime;

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	if (doperspective)
		perspective(50, (float)screenw/screenh, mindist/5, maxdist*5);
	else
		orthogonal(camera.distance/2, (float)screenw/screenh, mindist/5, maxdist*5);

	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	glRotatef(-90, 1, 0, 0); // Z-up

	glEnable(GL_DEPTH_TEST);
	glEnable(GL_COLOR_MATERIAL);
	glEnable(GL_LIGHTING);

	glEnable(GL_LIGHT0);
	glLightfv(GL_LIGHT0, GL_POSITION, light_position);

	glTranslatef(0, camera.distance, 0);
	glRotatef(-camera.pitch, 1, 0, 0);
	glRotatef(-camera.yaw, 0, 0, 1);
	glTranslatef(-camera.center[0], -camera.center[1], -camera.center[2]);

	if (doplay && curanim) {
		glutPostRedisplay();
		curtime = curtime + (timediff / 1000.0) * 30.0;
		curframe = ((int)curtime) % curanim->len;
		animatemodel(curanim, curframe);
	}

	if (dotexture)
		glEnable(GL_TEXTURE_2D);
	else
		glDisable(GL_TEXTURE_2D);

	if (dowire)
		glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
	else
		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);

	if (dobackface)
		glDisable(GL_CULL_FACE);
	else
		glEnable(GL_CULL_FACE);

	glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, dotwosided);

	doalpha = CLAMP(doalpha, 0, 4);
	switch (doalpha) {
	// No alpha transparency.
	case 0:
		drawmodel();
		break;

	// Alpha test only. Always correct, but aliased and ugly.
	case 1:
		glAlphaFunc(GL_GREATER, 0.2);
		glEnable(GL_ALPHA_TEST);
		drawmodel();
		glDisable(GL_ALPHA_TEST);
		break;

	// Quick-and-dirty hack: render with both test and blend.
	// Background may leak through depending on drawing order.
	case 2:
		glAlphaFunc(GL_GREATER, 0.2);
		glEnable(GL_ALPHA_TEST);
		glEnable(GL_BLEND);
		drawmodel();
		glDisable(GL_BLEND);
		glDisable(GL_ALPHA_TEST);
		break;

	// For best looking alpha blending, render twice.
	// Solid parts first to fill the depth buffer.
	// Transparent parts after, with z-write disabled.
	// Background is safe, but internal blend order may be wrong.
	case 3:
		glEnable(GL_ALPHA_TEST);
		glAlphaFunc(GL_EQUAL, 1);
		drawmodel();

		glAlphaFunc(GL_LESS, 1);
		glEnable(GL_BLEND);
		glDepthMask(GL_FALSE);
		drawmodel();
		glDepthMask(GL_TRUE);
		glDisable(GL_BLEND);
		glDisable(GL_ALPHA_TEST);
		break;

	// If we have a multisample buffer, we can get 'perfect' transparency
	// by using alpha-as-coverage. This does have a few limitations, depending
	// on the number of samples available you'll get banding or dithering artefacts.
	case 4:
		glEnable(GL_SAMPLE_ALPHA_TO_COVERAGE);
		drawmodel();
		glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE);
		break;
	}

	glDisable(GL_CULL_FACE);
	glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
	glDisable(GL_TEXTURE_2D);

	glDisable(GL_LIGHTING);
	glDisable(GL_COLOR_MATERIAL);

	if (doplane) {
		glBegin(GL_LINES);
		glColor4f(0.4, 0.4, 0.4, 1);
		for (i = -gridsize; i <= gridsize; i ++) {
			glVertex3f(i, -gridsize, 0); glVertex3f(i, gridsize, 0);
			glVertex3f(-gridsize, i, 0); glVertex3f(gridsize, i, 0);
		}
		glEnd();
	}

	glDisable(GL_DEPTH_TEST);

	if (doskeleton) {
		drawskeleton();
	}

	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glOrtho(0, screenw, screenh, 0, -1, 1);

	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	glColor4f(1, 1, 1, 1);
	sprintf(buf, "%d meshes; %d vertices; %d faces; %d bones", mesh_count, position.len/3, element.len/3, bone_count);
	drawstring(8, 18+0, buf);
	if (curanim) {
		sprintf(buf, "%s (%03d / %03d)", curanim->name, curframe + 1, curanim->len);
		drawstring(8, 18+16, buf);
	}

	if (showhelp) {
		#define Y(n) 18+40+n*16
		glColor4f(1, 1, 0.5, 1);
		drawstring(8, Y(0), "a - change transparency mode");
		drawstring(8, Y(1), "t - toggle textures");
		drawstring(8, Y(2), "w - toggle wireframe");
		drawstring(8, Y(3), "b - toggle backface culling");
		drawstring(8, Y(4), "l - toggle two-sided lighting");
		drawstring(8, Y(5), "k - toggle skeleton");
		drawstring(8, Y(6), "g - toggle ground plane");
		drawstring(8, Y(7), "p - toggle orthogonal/perspective camera");
		drawstring(8, Y(8), "D - set up isometric camera (4:3)");
		drawstring(8, Y(9), "i - set up dimetric camera (2:1)");
		drawstring(8, Y(10), "I - set up isometric camera (true)");
	}

	glutSwapBuffers();

	i = glGetError();
	if (i) fprintf(stderr, "opengl error: %d\n", i);
}

int main(int argc, char **argv)
{
	float clearcolor[4] = { 0.22, 0.22, 0.22, 1.0 };
	float zoom = 1;

	glutInitWindowPosition(50, 50+24);
	glutInitWindowSize(screenw, screenh);
	glutInit(&argc, argv);
	glutInitDisplayMode(GLUT_RGB | GLUT_DOUBLE | GLUT_DEPTH | GLUT_MULTISAMPLE);

	glutCreateWindow("IQE Viewer");
	screenw = glutGet(GLUT_WINDOW_WIDTH);
	screenh = glutGet(GLUT_WINDOW_HEIGHT);

#ifdef __APPLE__
	int one = 1;
	void *ctx = CGLGetCurrentContext();
	CGLSetParameter(ctx, kCGLCPSwapInterval, &one);
#endif

	initchecker();

	if (argc > 1) {
		strcpy(basedir, argv[1]);
		char *p = strrchr(basedir, '/');
		if (!p) p = strrchr(basedir, '\\');
		if (!p) strcpy(basedir, ""); else p[1] = 0;

		glutSetWindowTitle(argv[1]);

		loadmodel(argv[1]);

		float radius = measuremodel(camera.center);
		camera.distance = radius * 2 * zoom;
		gridsize = (int)radius + 1;
		mindist = radius * 0.1;
		maxdist = radius * 10;

		if (mesh_count == 0 && bone_count > 0)
			doskeleton = 1;
	}

	glEnable(GL_MULTISAMPLE);
	glEnable(GL_NORMALIZE);
	glDepthFunc(GL_LEQUAL);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	glClearColor(clearcolor[0], clearcolor[1], clearcolor[2], clearcolor[3]);

	glutReshapeFunc(reshape);
	glutDisplayFunc(display);
	glutMouseFunc(mouse);
	glutMotionFunc(motion);
	glutKeyboardFunc(keyboard);
	glutSpecialFunc(special);
	glutMainLoop();

	return 0;
}

