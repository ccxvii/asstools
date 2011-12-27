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

#include <assimp.h>
#include <aiColor4D.h>
#include <aiConfig.h>
#include <aiMatrix3x3.h>
#include <aiMatrix4x4.h>
#include <aiPostProcess.h>
#include <aiScene.h>
#include <aiVector3D.h>

#define MIN(a,b) ((a) < (b) ? (a) : (b))
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define CLAMP(x,a,b) MIN(MAX(x,a),b)

#define ISOMETRIC 35.264	// true isometric view
#define DIMETRIC 30		// 2:1 'isometric' as seen in pixel art

/*
 * Use Sean Barrett's excellent stb_image to load textures.
 */

#define STBI_NO_HDR
#define STBI_NO_WRITE
#include "stb_image.c"

char basedir[2000];

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

unsigned int loadmaterial(struct aiMaterial *material)
{
	char filename[2000];
	struct aiString str;
	if (!aiGetMaterialString(material, AI_MATKEY_TEXTURE_DIFFUSE(0), &str)) {
		char *s = strrchr(str.data, '/');
		if (!s) s = strrchr(str.data, '\\');
		if (!s) s = str.data; else s++;
		strcpy(filename, basedir);
		strcat(filename, s);
		return loadtexture(filename);
	}
	return 0;
}

/*
 * Some extra matrix, vector and quaternion functions.
 *
 * Many of these already exist in some variant in assimp,
 * but not exported to the C interface.
 */

// convert 4x4 to column major format for opengl
void transposematrix(float m[16], struct aiMatrix4x4 *p)
{
	m[0] = p->a1; m[4] = p->a2; m[8] = p->a3; m[12] = p->a4;
	m[1] = p->b1; m[5] = p->b2; m[9] = p->b3; m[13] = p->b4;
	m[2] = p->c1; m[6] = p->c2; m[10] = p->c3; m[14] = p->c4;
	m[3] = p->d1; m[7] = p->d2; m[11] = p->d3; m[15] = p->d4;
}

void extract3x3(struct aiMatrix3x3 *m3, struct aiMatrix4x4 *m4)
{
	m3->a1 = m4->a1; m3->a2 = m4->a2; m3->a3 = m4->a3;
	m3->b1 = m4->b1; m3->b2 = m4->b2; m3->b3 = m4->b3;
	m3->c1 = m4->c1; m3->c2 = m4->c2; m3->c3 = m4->c3;
}

void mixvector(struct aiVector3D *p, struct aiVector3D *a, struct aiVector3D *b, float t)
{
	p->x = a->x + t * (b->x - a->x);
	p->y = a->y + t * (b->y - a->y);
	p->z = a->z + t * (b->z - a->z);
}

float dotquaternions(struct aiQuaternion *a, struct aiQuaternion *b)
{
	return a->x*b->x + a->y*b->y + a->z*b->z + a->w*b->w;
}

void normalizequaternion(struct aiQuaternion *q)
{
	float d = sqrt(dotquaternions(q, q));
	if (d >= 0.00001) {
		d = 1 / d;
		q->x *= d;
		q->y *= d;
		q->z *= d;
		q->w *= d;
	} else {
		q->x = q->y = q->z = 0;
		q->w = 1;
	}
}

void mixquaternion(struct aiQuaternion *q, struct aiQuaternion *a, struct aiQuaternion *b, float t)
{
	if (dotquaternions(a, b) < 0) {
		struct aiQuaternion tmp;
		tmp.x = -a->x; tmp.y = -a->y; tmp.z = -a->z; tmp.w = -a->w;
		a = &tmp;
	}
	q->x = a->x + t * (b->x - a->x);
	q->y = a->y + t * (b->y - a->y);
	q->z = a->z + t * (b->z - a->z);
	q->w = a->w + t * (b->w - a->w);
	normalizequaternion(q);
}

void composematrix(struct aiMatrix4x4 *m,
	struct aiVector3D *t, struct aiQuaternion *q, struct aiVector3D *s)
{
	// quat to rotation matrix
	m->a1 = 1 - 2 * (q->y * q->y + q->z * q->z);
	m->a2 = 2 * (q->x * q->y - q->z * q->w);
	m->a3 = 2 * (q->x * q->z + q->y * q->w);
	m->b1 = 2 * (q->x * q->y + q->z * q->w);
	m->b2 = 1 - 2 * (q->x * q->x + q->z * q->z);
	m->b3 = 2 * (q->y * q->z - q->x * q->w);
	m->c1 = 2 * (q->x * q->z - q->y * q->w);
	m->c2 = 2 * (q->y * q->z + q->x * q->w);
	m->c3 = 1 - 2 * (q->x * q->x + q->y * q->y);

	// scale matrix
	m->a1 *= s->x; m->a2 *= s->x; m->a3 *= s->x;
	m->b1 *= s->y; m->b2 *= s->y; m->b3 *= s->y;
	m->c1 *= s->z; m->c2 *= s->z; m->c3 *= s->z;

	// set translation
	m->a4 = t->x; m->b4 = t->y; m->c4 = t->z;

	m->d1 = 0; m->d2 = 0; m->d3 = 0; m->d4 = 1;
}

/*
 * Init, animate and draw aiScene.
 *
 * We build our own list of the meshes to keep the vertex data
 * in a format suitable for use with OpenGL. We also store the
 * resulting meshes during skeletal animation here.
 */

int vertexcount = 0, facecount = 0; // for statistics only

// opengl (and skinned vertex) buffers for the meshes
int meshcount = 0;
struct mesh {
	struct aiMesh *mesh;
	unsigned int texture;
	int vertexcount, elementcount;
	float *position;
	float *normal;
	float *texcoord;
	int *element;
} *meshlist = NULL;

// find a node by name in the hierarchy (for anims and bones)
struct aiNode *findnode(struct aiNode *node, char *name)
{
	int i;
	if (!strcmp(name, node->mName.data))
		return node;
	for (i = 0; i < node->mNumChildren; i++) {
		struct aiNode *found = findnode(node->mChildren[i], name);
		if (found)
			return found;
	}
	return NULL;
}

// calculate absolute transform for node to do mesh skinning
void transformnode(struct aiMatrix4x4 *result, struct aiNode *node)
{
	if (node->mParent) {
		transformnode(result, node->mParent);
		aiMultiplyMatrix4(result, &node->mTransformation);
	} else {
		*result = node->mTransformation;
	}
}

void transformmesh(struct aiScene *scene, struct mesh *mesh)
{
	struct aiMesh *amesh = mesh->mesh;
	struct aiMatrix4x4 skin4;
	struct aiMatrix3x3 skin3;
	int i, k;

	if (amesh->mNumBones == 0)
		return;

	memset(mesh->position, 0, mesh->vertexcount * 3 * sizeof(float));
	memset(mesh->normal, 0, mesh->vertexcount * 3 * sizeof(float));

	for (k = 0; k < amesh->mNumBones; k++) {
		struct aiBone *bone = amesh->mBones[k];
		struct aiNode *node = findnode(scene->mRootNode, bone->mName.data);

		transformnode(&skin4, node);
		aiMultiplyMatrix4(&skin4, &bone->mOffsetMatrix);
		extract3x3(&skin3, &skin4);

		for (i = 0; i < bone->mNumWeights; i++) {
			int v = bone->mWeights[i].mVertexId;
			float w = bone->mWeights[i].mWeight;

			struct aiVector3D position = amesh->mVertices[v];
			aiTransformVecByMatrix4(&position, &skin4);
			mesh->position[v*3+0] += position.x * w;
			mesh->position[v*3+1] += position.y * w;
			mesh->position[v*3+2] += position.z * w;

			struct aiVector3D normal = amesh->mNormals[v];
			aiTransformVecByMatrix3(&normal, &skin3);
			mesh->normal[v*3+0] += normal.x * w;
			mesh->normal[v*3+1] += normal.y * w;
			mesh->normal[v*3+2] += normal.z * w;
		}
	}
}

void initmesh(struct aiScene *scene, struct mesh *mesh, struct aiMesh *amesh)
{
	int i;

	vertexcount += amesh->mNumVertices;
	facecount += amesh->mNumFaces;

	mesh->mesh = amesh; // stow away pointer for bones

	mesh->texture = loadmaterial(scene->mMaterials[amesh->mMaterialIndex]);

	mesh->vertexcount = amesh->mNumVertices;
	mesh->position = calloc(mesh->vertexcount * 3, sizeof(float));
	mesh->normal = calloc(mesh->vertexcount * 3, sizeof(float));
	mesh->texcoord = calloc(mesh->vertexcount * 2, sizeof(float));

	for (i = 0; i < mesh->vertexcount; i++) {
		mesh->position[i*3+0] = amesh->mVertices[i].x;
		mesh->position[i*3+1] = amesh->mVertices[i].y;
		mesh->position[i*3+2] = amesh->mVertices[i].z;

		if (amesh->mNormals) {
			mesh->normal[i*3+0] = amesh->mNormals[i].x;
			mesh->normal[i*3+1] = amesh->mNormals[i].y;
			mesh->normal[i*3+2] = amesh->mNormals[i].z;
		}

		if (amesh->mTextureCoords[0]) {
			mesh->texcoord[i*2+0] = amesh->mTextureCoords[0][i].x;
			mesh->texcoord[i*2+1] = 1 - amesh->mTextureCoords[0][i].y;
		}
	}

	mesh->elementcount = amesh->mNumFaces * 3;
	mesh->element = calloc(mesh->elementcount, sizeof(int));

	for (i = 0; i < amesh->mNumFaces; i++) {
		struct aiFace *face = amesh->mFaces + i;
		mesh->element[i*3+0] = face->mIndices[0];
		mesh->element[i*3+1] = face->mIndices[1];
		mesh->element[i*3+2] = face->mIndices[2];
	}
}

void initscene(struct aiScene *scene)
{
	int i;
	meshcount = scene->mNumMeshes;
	meshlist = calloc(meshcount, sizeof *meshlist);
	for (i = 0; i < meshcount; i++) {
		initmesh(scene, meshlist + i, scene->mMeshes[i]);
		transformmesh(scene, meshlist + i);
	}
}

void drawmesh(struct mesh *mesh)
{
	if (mesh->texture > 0)
		glColor4f(1, 1, 1, 1);
	else
		glColor4f(0.9, 0.7, 0.7, 1);
	glBindTexture(GL_TEXTURE_2D, mesh->texture);
	glVertexPointer(3, GL_FLOAT, 0, mesh->position);
	glNormalPointer(GL_FLOAT, 0, mesh->normal);
	glTexCoordPointer(2, GL_FLOAT, 0, mesh->texcoord);
	glDrawElements(GL_TRIANGLES, mesh->elementcount, GL_UNSIGNED_INT, mesh->element);
}

void drawnode(struct aiNode *node, struct aiMatrix4x4 world)
{
	float mat[16];
	int i;

	aiMultiplyMatrix4(&world, &node->mTransformation);
	transposematrix(mat, &world);

	for (i = 0; i < node->mNumMeshes; i++) {
		struct mesh *mesh = meshlist + node->mMeshes[i];
		if (mesh->mesh->mNumBones == 0) {
			// non-skinned meshes are in node-local space
			glPushMatrix();
			glMultMatrixf(mat);
			drawmesh(mesh);
			glPopMatrix();
		} else {
			// skinned meshes are already in world space
			drawmesh(mesh);
		}
	}

	for (i = 0; i < node->mNumChildren; i++)
		drawnode(node->mChildren[i], world);
}

void drawscene(struct aiScene *scene)
{
	struct aiMatrix4x4 world;

	glEnableClientState(GL_VERTEX_ARRAY);
	glEnableClientState(GL_TEXTURE_COORD_ARRAY);
	glEnableClientState(GL_NORMAL_ARRAY);

	aiIdentityMatrix4(&world);
	drawnode(scene->mRootNode, world);

	glDisableClientState(GL_VERTEX_ARRAY);
	glDisableClientState(GL_TEXTURE_COORD_ARRAY);
	glDisableClientState(GL_NORMAL_ARRAY);
}

void measuremesh(struct mesh *mesh, struct aiMatrix4x4 transform, float bboxmin[3], float bboxmax[3])
{
	struct aiVector3D p;
	int i;
	for (i = 0; i < mesh->vertexcount; i++) {
		p.x = mesh->position[i*3+0];
		p.y = mesh->position[i*3+1];
		p.z = mesh->position[i*3+2];
		aiTransformVecByMatrix4(&p, &transform);
		bboxmin[0] = MIN(bboxmin[0], p.x);
		bboxmin[1] = MIN(bboxmin[1], p.y);
		bboxmin[2] = MIN(bboxmin[2], p.z);
		bboxmax[0] = MAX(bboxmax[0], p.x);
		bboxmax[1] = MAX(bboxmax[1], p.y);
		bboxmax[2] = MAX(bboxmax[2], p.z);
	}
}

void measurenode(struct aiNode *node, struct aiMatrix4x4 world, float bboxmin[3], float bboxmax[3])
{
	struct aiMatrix4x4 identity;
	int i;

	aiMultiplyMatrix4(&world, &node->mTransformation);
	aiIdentityMatrix4(&identity);

	for (i = 0; i < node->mNumMeshes; i++) {
		struct mesh *mesh = meshlist + node->mMeshes[i];
		if (mesh->mesh->mNumBones == 0) {
			// non-skinned meshes are in node-local space
			measuremesh(mesh, world, bboxmin, bboxmax);
		} else {
			// skinned meshes are already in world space
			measuremesh(mesh, identity, bboxmin, bboxmax);
		}
	}

	for (i = 0; i < node->mNumChildren; i++)
		measurenode(node->mChildren[i], world, bboxmin, bboxmax);
}

float measurescene(struct aiScene *scene, float center[3])
{
	struct aiMatrix4x4 world;
	float bboxmin[3];
	float bboxmax[3];
	float dx, dy, dz;

	bboxmin[0] = 1e10; bboxmax[0] = -1e10;
	bboxmin[1] = 1e10; bboxmax[1] = -1e10;
	bboxmin[2] = 1e10; bboxmax[2] = -1e10;

	aiIdentityMatrix4(&world);
	measurenode(scene->mRootNode, world, bboxmin, bboxmax);

	center[0] = (bboxmin[0] + bboxmax[0]) / 2;
	center[1] = (bboxmin[1] + bboxmax[1]) / 2;
	center[2] = (bboxmin[2] + bboxmax[2]) / 2;

	dx = MAX(center[0] - bboxmin[0], bboxmax[0] - center[0]);
	dy = MAX(center[1] - bboxmin[1], bboxmax[1] - center[1]);
	dz = MAX(center[2] - bboxmin[2], bboxmax[2] - center[2]);

	return sqrt(dx*dx + dy*dy + dz*dz);
}

int animationlength(struct aiAnimation *anim)
{
	int i, len = 0;
	for (i = 0; i < anim->mNumChannels; i++) {
		struct aiNodeAnim *chan = anim->mChannels[i];
		len = MAX(len, chan->mNumPositionKeys);
		len = MAX(len, chan->mNumRotationKeys);
		len = MAX(len, chan->mNumScalingKeys);
	}
	return len;
}

void animatescene(struct aiScene *scene, struct aiAnimation *anim, float tick)
{
	struct aiVectorKey *p0, *p1, *s0, *s1;
	struct aiQuatKey *r0, *r1;
	struct aiVector3D p, s;
	struct aiQuaternion r;
	int i;

	// Assumes even key frame rate and synchronized pos/rot/scale keys.
	// We should look at the key->mTime values instead, but I'm lazy.

	int frame = floor(tick);
	float t = tick - floor(tick);

	for (i = 0; i < anim->mNumChannels; i++) {
		struct aiNodeAnim *chan = anim->mChannels[i];
		struct aiNode *node = findnode(scene->mRootNode, chan->mNodeName.data);
		p0 = chan->mPositionKeys + (frame+0) % chan->mNumPositionKeys;
		p1 = chan->mPositionKeys + (frame+1) % chan->mNumPositionKeys;
		r0 = chan->mRotationKeys + (frame+0) % chan->mNumRotationKeys;
		r1 = chan->mRotationKeys + (frame+1) % chan->mNumRotationKeys;
		s0 = chan->mScalingKeys + (frame+0) % chan->mNumScalingKeys;
		s1 = chan->mScalingKeys + (frame+1) % chan->mNumScalingKeys;
		mixvector(&p, &p0->mValue, &p1->mValue, t);
		mixquaternion(&r, &r0->mValue, &r1->mValue, t);
		mixvector(&s, &s0->mValue, &s1->mValue, t);
		composematrix(&node->mTransformation, &p, &r, &s);
	}

	for (i = 0; i < meshcount; i++)
		transformmesh(scene, meshlist + i);
}

/*
 * Boring UI and GLUT hooks.
 */

struct aiScene *g_scene = NULL;
int lasttime = 0;
struct aiAnimation *curanim = NULL;
int animfps = 30, animlen = 0;
float animtick = 0;
int playing = 1;

unsigned int doplane = 0;
unsigned int dotexture = 1;
unsigned int doalpha = 0;
unsigned int dowire = 0;
unsigned int docull = 0;
unsigned int dotwosided = 1;
unsigned int doperspective = 1;

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

void setanim(int i)
{
	if (!g_scene) return;
	if (g_scene->mNumAnimations == 0) return;
	i = MIN(i, g_scene->mNumAnimations - 1);
	curanim = g_scene->mAnimations[i];
	animlen = animationlength(curanim);
	animfps = 30;
	animtick = 0;
	if (animfps < 1)
		animfps = 30;
}

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
		glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, *s++);
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
	case 'f': togglefullscreen(); break;
	case '0': animtick = 0; animfps = 30; break;
	case 'i': doperspective = 0; camera.yaw = 45; camera.pitch = -DIMETRIC; break;
	case 'I': doperspective = 0; camera.yaw = 45; camera.pitch = -ISOMETRIC; break;
	case 'r': doperspective = !doperspective; break;
	case '1': case '2': case '3': case '4':
	case '5': case '6': case '7': case '8':
	case '9': setanim(key - '1'); break;
	case ' ': playing = !playing; break;
	case '.': animtick = floor(animtick) + 1; break;
	case ',': animtick = floor(animtick) - 1; break;
	case '[': animfps = MAX(5, animfps-5); break;
	case ']': animfps = MIN(60, animfps+5); break;
	case 'p': doplane = !doplane; break;
	case 't': dotexture = !dotexture; break;
	case 'A': doalpha--; break;
	case 'a': doalpha++; break;
	case 'w': dowire = !dowire; break;
	case 'c': docull = !docull; break;
	case 'l': dotwosided = !dotwosided; break;
	}

	if (playing)
		lasttime = glutGet(GLUT_ELAPSED_TIME);

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
	int time, timestep;
	int i;

	time = glutGet(GLUT_ELAPSED_TIME);
	timestep = time - lasttime;
	lasttime = time;

	if (g_scene) {
		if (curanim) {
			if (playing) {
				animtick = animtick + (timestep/1000.0) * animfps;
				glutPostRedisplay();
			}
			while (animtick < 0) animtick += animlen;
			while (animtick >= animlen) animtick -= animlen;
			animatescene(g_scene, curanim, animtick);
		}
	}

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

	if (docull)
		glEnable(GL_CULL_FACE);
	else
		glDisable(GL_CULL_FACE);

	glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, dotwosided);

	doalpha = CLAMP(doalpha, 0, 4);
	switch (doalpha) {
	// No alpha transparency.
	case 0:
		if (g_scene) drawscene(g_scene);
		break;

	// Alpha test only. Always correct, but aliased and ugly.
	case 1:
		glAlphaFunc(GL_GREATER, 0.2);
		glEnable(GL_ALPHA_TEST);
		if (g_scene) drawscene(g_scene);
		glDisable(GL_ALPHA_TEST);
		break;

	// Quick-and-dirty hack: render with both test and blend.
	// Background may leak through depending on drawing order.
	case 2:
		glAlphaFunc(GL_GREATER, 0.2);
		glEnable(GL_ALPHA_TEST);
		glEnable(GL_BLEND);
		if (g_scene) drawscene(g_scene);
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
		if (g_scene) drawscene(g_scene);

		glAlphaFunc(GL_LESS, 1);
		glEnable(GL_BLEND);
		glDepthMask(GL_FALSE);
		if (g_scene) drawscene(g_scene);
		glDepthMask(GL_TRUE);
		glDisable(GL_BLEND);
		glDisable(GL_ALPHA_TEST);
		break;

	// If we have a multisample buffer, we can get 'perfect' transparency
	// by using alpha-as-coverage. This does have a few limitations, depending
	// on the number of samples available you'll get banding or dithering artefacts.
	case 4:
		glEnable(GL_SAMPLE_ALPHA_TO_COVERAGE);
		if (g_scene) drawscene(g_scene);
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
	if (g_scene) {
		sprintf(buf, "%d meshes; %d vertices; %d faces ", meshcount, vertexcount, facecount);
		drawstring(8, 18+0, buf);
		if (curanim) {
			sprintf(buf, "frame %03d / %03d (%d fps)", (int)animtick+1, animlen, animfps);
			drawstring(8, 18+20, buf);
		}
	} else {
		drawstring(10, 18, "No model loaded!");
	}
	if (curanim)
		drawstring(10, screenh-10-18, "space to play/pause; [ and ] to change speed; , and . to step");

	sprintf(buf, "w - wireframe; a - transparency %d; t - textures; p - plane; c - backface; l - two-sided; r/i - perspective", doalpha);
	drawstring(10, screenh-10, buf);

	glutSwapBuffers();

	i = glGetError();
	if (i) fprintf(stderr, "opengl error: %d\n", i);
}

int main(int argc, char **argv)
{
	glutInit(&argc, argv);
	glutInitWindowPosition(50, 50+24);
	glutInitWindowSize(screenw, screenh);
	glutInitDisplayMode(GLUT_RGB | GLUT_DOUBLE | GLUT_DEPTH | GLUT_MULTISAMPLE);
	glutCreateWindow("Asset Viewer");

#ifdef __APPLE__
	int one = 1;
	void *ctx = CGLGetCurrentContext();
	CGLSetParameter(ctx, kCGLCPSwapInterval, &one);
#endif

	if (argc > 1) {
		int flags = aiProcess_Triangulate;
		flags |= aiProcess_JoinIdenticalVertices;
		flags |= aiProcess_GenSmoothNormals;
		flags |= aiProcess_GenUVCoords;
		flags |= aiProcess_TransformUVCoords;
		flags |= aiProcess_RemoveComponent;

		aiSetImportPropertyInteger(AI_CONFIG_PP_RVC_FLAGS,
			aiComponent_TANGENTS_AND_BITANGENTS |
			aiComponent_COLORS);

		strcpy(basedir, argv[1]);
		char *p = strrchr(basedir, '/');
		if (!p) p = strrchr(basedir, '\\');
		if (!p) strcpy(basedir, ""); else p[1] = 0;

		glutSetWindowTitle(argv[1]);

		g_scene = (struct aiScene*) aiImportFile(argv[1], flags);
		if (g_scene) {
			initscene(g_scene);

			float radius = measurescene(g_scene, camera.center);
			camera.distance = radius * 2;
			gridsize = (int)radius + 1;
			mindist = radius * 0.1;
			maxdist = radius * 10;

			setanim(0);
		} else {
			fprintf(stderr, "cannot import scene: '%s'\n", argv[1]);
		}
	}

	glutReshapeFunc(reshape);
	glutDisplayFunc(display);
	glutMouseFunc(mouse);
	glutMotionFunc(motion);
	glutKeyboardFunc(keyboard);

	glEnable(GL_MULTISAMPLE);
	glEnable(GL_NORMALIZE);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	glClearColor(0.22, 0.22, 0.22, 1);

	glutMainLoop();

	return 0;
}
