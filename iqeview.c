#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
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

static struct floatarray position = { 0, 0, NULL };
static struct floatarray normal = { 0, 0, NULL };
static struct floatarray texcoord = { 0, 0, NULL };
static struct intarray element = { 0, 0, NULL };

static struct mesh meshbuf[MAXMESH];
static int mesh_count = 0;

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
	int fm = 0;
	struct mesh *mesh = NULL;
	char *s, *sp;

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
			float z = -parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
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
			float z = -parsefloat(&sp, 0);
			float y = parsefloat(&sp, 0);
			addnormal(x, y, z);
		} else if (!strcmp(s, "fm")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, 0);
			addtriangle(x+fm, y+fm, z+fm);
		} else if (!strcmp(s, "fa")) {
			int x = parseint(&sp, 0);
			int y = parseint(&sp, 0);
			int z = parseint(&sp, 0);
			addtriangle(x, y, z);
		} else if (!strcmp(s, "mesh")) {
			if (mesh) {
				mesh->count = element.len - mesh->first;
				if (mesh->count == 0)
					mesh_count--;
			}
			mesh = &meshbuf[mesh_count++];
			mesh->texture = material;
			mesh->first = element.len;
			mesh->count = 0;
			fm = position.len / 3;
		} else if (!strcmp(s, "material")) {
			s = parsestring(&sp);
			material = loadmaterial(s);
			if (mesh) {
				mesh->texture = material;
			}
		}
	}

	if (mesh) {
		glBindTexture(GL_TEXTURE_2D, mesh->texture);
		mesh->count = element.len - mesh->first;
		if (mesh->count == 0)
			mesh_count--;
	}

	if (mesh_count == 0) {
		mesh = meshbuf;
		mesh->texture = 0;
		mesh->first = 0;
		mesh->count = element.len;
		mesh_count = 1;
	}

	fprintf(stderr, "\t%d meshes; %d vertices; %d triangles\n",
			mesh_count, position.len/3, element.len/3);
}

void drawmodel(void)
{
	int i;

	glEnableClientState(GL_VERTEX_ARRAY);
	glEnableClientState(GL_TEXTURE_COORD_ARRAY);
	glEnableClientState(GL_NORMAL_ARRAY);

	glVertexPointer(3, GL_FLOAT, 0, position.data);
	glNormalPointer(GL_FLOAT, 0, normal.data);
	glTexCoordPointer(2, GL_FLOAT, 0, texcoord.data);

	for (i = 0; i < mesh_count; i++) {
		if (meshbuf[i].texture > 0) {
			glColor4f(1, 1, 1, 1);
			glBindTexture(GL_TEXTURE_2D, meshbuf[i].texture);
		} else {
			glColor4f(0.9, 0.7, 0.7, 1);
			glBindTexture(GL_TEXTURE_2D, checker_texture);
		}
		glDrawElements(GL_TRIANGLES, meshbuf[i].count, GL_UNSIGNED_INT, element.data + meshbuf[i].first);
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

#include "getopt.c"

#define ISOMETRIC 35.264	// true isometric view
#define DIMETRIC 30		// 2:1 'isometric' as seen in pixel art

int showhelp = 0;
int doplane = 0;
int doalpha = 0;
int dowire = 0;
int dotexture = 1;
int dobackface = 1;
int dotwosided = 1;
int doperspective = 1;

int screenw = 800, screenh = 600;
int mousex, mousey, mouseleft = 0, mousemiddle = 0, mouseright = 0;

int gridsize = 3;
float mindist = 1;
float maxdist = 10;

float light_position[4] = { -1, 2, 2, 0 };

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
	case 'p': doperspective = !doperspective; break;
	case 'g': doplane = !doplane; break;
	case 't': dotexture = !dotexture; break;
	case 'A': doalpha--; break;
	case 'a': doalpha++; break;
	case 'w': dowire = !dowire; break;
	case 'b': dobackface = !dobackface; break;
	case 'l': dotwosided = !dotwosided; break;
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

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	if (doperspective)
		perspective(50, (float)screenw/screenh, mindist/5, maxdist*5);
	else
		orthogonal(camera.distance/2, (float)screenw/screenh, mindist/5, maxdist*5);

	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	glEnable(GL_DEPTH_TEST);
	glEnable(GL_COLOR_MATERIAL);
	glEnable(GL_LIGHTING);

	glEnable(GL_LIGHT0);
	glLightfv(GL_LIGHT0, GL_POSITION, light_position);

	glTranslatef(0, 0, -camera.distance);
	glRotatef(-camera.pitch, 1, 0, 0);
	glRotatef(-camera.yaw, 0, 1, 0);
	glTranslatef(-camera.center[0], -camera.center[1], -camera.center[2]);

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
			glVertex3f(i, 0, -gridsize); glVertex3f(i, 0, gridsize);
			glVertex3f(-gridsize, 0, i); glVertex3f(gridsize, 0, i);
		}
		glEnd();
	}

	glDisable(GL_DEPTH_TEST);

	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glOrtho(0, screenw, screenh, 0, -1, 1);

	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	glColor4f(1, 1, 1, 1);
	sprintf(buf, "%d meshes; %d vertices; %d faces ", mesh_count, position.len/3, element.len/3);
	drawstring(8, 18+0, buf);

	if (showhelp) {
		#define Y(n) 18+40+n*16
		glColor4f(1, 1, 0.5, 1);
		drawstring(8, Y(0), "a - change transparency mode");
		drawstring(8, Y(1), "t - toggle textures");
		drawstring(8, Y(2), "w - toggle wireframe");
		drawstring(8, Y(3), "b - toggle backface culling");
		drawstring(8, Y(4), "l - toggle two-sided lighting");
		drawstring(8, Y(5), "g - toggle ground plane");
		drawstring(8, Y(6), "p - toggle orthogonal/perspective camera");
		drawstring(8, Y(7), "i - set up dimetric camera (2:1)");
		drawstring(8, Y(8), "I - set up isometric camera");
	}

	glutSwapBuffers();

	i = glGetError();
	if (i) fprintf(stderr, "opengl error: %d\n", i);
}

void usage(void)
{
	fprintf(stderr, "usage: assview [-geometry WxH] [options] asset.dae\n");
	fprintf(stderr, "\t-i\tdimetric (2:1) camera\n");
	fprintf(stderr, "\t-I\ttrue isometric camera\n");
	fprintf(stderr, "\t-a\talpha transparency mode; use more times for higher quality.\n");
	fprintf(stderr, "\t-b\tdon't render backfaces\n");
	fprintf(stderr, "\t-g\trender ground plane\n");
	fprintf(stderr, "\t-l\tone-sided lighting\n");
	fprintf(stderr, "\t-t\tdon't render textures\n");
	fprintf(stderr, "\t-w\trender wireframe\n");
	fprintf(stderr, "\t-c r,g,b\tbackground color\n");
	fprintf(stderr, "\t-r n\trotate camera n degrees (yaw)\n");
	fprintf(stderr, "\t-p n\tpitch camera n degrees\n");
	fprintf(stderr, "\t-z n\tzoom camera n times\n");
	fprintf(stderr, "\t-f n\trender animation at frame n\n");
	exit(1);
}

int main(int argc, char **argv)
{
	float clearcolor[4] = { 0.22, 0.22, 0.22, 1.0 };
	float zoom = 1;
	int c;

	glutInitWindowPosition(50, 50+24);
	glutInitWindowSize(screenw, screenh);
	glutInit(&argc, argv);
	glutInitDisplayMode(GLUT_RGB | GLUT_DOUBLE | GLUT_DEPTH | GLUT_MULTISAMPLE);

	while ((c = getopt(argc, argv, "iIgtawblc:r:p:z:f:")) != -1) {
		switch (c) {
		case 'i': doperspective = 0; camera.yaw = 45; camera.pitch = -DIMETRIC; break;
		case 'I': doperspective = 0; camera.yaw = 45; camera.pitch = -ISOMETRIC; break;
		case 'g': doplane = 1; break;
		case 't': dotexture = 0; break;
		case 'a': doalpha++; break;
		case 'w': dowire = 1; break;
		case 'b': dobackface = 0; break;
		case 'l': dotwosided = 0; break;
		case 'c': sscanf(optarg, "%g,%g,%g", clearcolor+0, clearcolor+1, clearcolor+2); break;
		case 'r': camera.yaw = atof(optarg); break;
		case 'p': camera.pitch = atof(optarg); break;
		case 'z': zoom = atof(optarg); break;
		default: usage(); break;
		}
	}

	glutCreateWindow("IQE Viewer");
	screenw = glutGet(GLUT_WINDOW_WIDTH);
	screenh = glutGet(GLUT_WINDOW_HEIGHT);

#ifdef __APPLE__
	int one = 1;
	void *ctx = CGLGetCurrentContext();
	CGLSetParameter(ctx, kCGLCPSwapInterval, &one);
#endif

	initchecker();

	if (optind < argc) {
		strcpy(basedir, argv[1]);
		char *p = strrchr(basedir, '/');
		if (!p) p = strrchr(basedir, '\\');
		if (!p) strcpy(basedir, ""); else p[1] = 0;

		glutSetWindowTitle(argv[1]);

		loadmodel(argv[optind]);

		float radius = measuremodel(camera.center);
		camera.distance = radius * 2 * zoom;
		gridsize = (int)radius + 1;
		mindist = radius * 0.1;
		maxdist = radius * 10;
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

