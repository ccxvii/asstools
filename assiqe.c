#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <ctype.h>
#include <math.h>

#include <assimp.h>
#include <aiMatrix4x4.h>
#include <aiMatrix3x3.h>
#include <aiColor4D.h>
#include <aiVector3D.h>
#include <aiPostProcess.h>
#include <aiScene.h>

#define noFLIP

#include "getopt.h"

float aiDeterminant(struct aiMatrix4x4 m)
{
	return m.a1*m.b2*m.c3*m.d4 - m.a1*m.b2*m.c4*m.d3 + m.a1*m.b3*m.c4*m.d2 - m.a1*m.b3*m.c2*m.d4 
		+ m.a1*m.b4*m.c2*m.d3 - m.a1*m.b4*m.c3*m.d2 - m.a2*m.b3*m.c4*m.d1 + m.a2*m.b3*m.c1*m.d4 
		- m.a2*m.b4*m.c1*m.d3 + m.a2*m.b4*m.c3*m.d1 - m.a2*m.b1*m.c3*m.d4 + m.a2*m.b1*m.c4*m.d3 
		+ m.a3*m.b4*m.c1*m.d2 - m.a3*m.b4*m.c2*m.d1 + m.a3*m.b1*m.c2*m.d4 - m.a3*m.b1*m.c4*m.d2 
		+ m.a3*m.b2*m.c4*m.d1 - m.a3*m.b2*m.c1*m.d4 - m.a4*m.b1*m.c2*m.d3 + m.a4*m.b1*m.c3*m.d2
		- m.a4*m.b2*m.c3*m.d1 + m.a4*m.b2*m.c1*m.d3 - m.a4*m.b3*m.c1*m.d2 + m.a4*m.b3*m.c2*m.d1;
}

struct aiMatrix4x4 aiInverseMatrix(struct aiMatrix4x4 m)
{
	float det = aiDeterminant(m);
	assert(det != 0.0f);
	float invdet = 1.0f / det;
	struct aiMatrix4x4 res;
	res.a1= invdet*(m.b2*(m.c3*m.d4-m.c4*m.d3)+m.b3*(m.c4*m.d2-m.c2*m.d4)+m.b4*(m.c2*m.d3-m.c3*m.d2));
	res.a2=-invdet*(m.a2*(m.c3*m.d4-m.c4*m.d3)+m.a3*(m.c4*m.d2-m.c2*m.d4)+m.a4*(m.c2*m.d3-m.c3*m.d2));
	res.a3= invdet*(m.a2*(m.b3*m.d4-m.b4*m.d3)+m.a3*(m.b4*m.d2-m.b2*m.d4)+m.a4*(m.b2*m.d3-m.b3*m.d2));
	res.a4=-invdet*(m.a2*(m.b3*m.c4-m.b4*m.c3)+m.a3*(m.b4*m.c2-m.b2*m.c4)+m.a4*(m.b2*m.c3-m.b3*m.c2));
	res.b1=-invdet*(m.b1*(m.c3*m.d4-m.c4*m.d3)+m.b3*(m.c4*m.d1-m.c1*m.d4)+m.b4*(m.c1*m.d3-m.c3*m.d1));
	res.b2= invdet*(m.a1*(m.c3*m.d4-m.c4*m.d3)+m.a3*(m.c4*m.d1-m.c1*m.d4)+m.a4*(m.c1*m.d3-m.c3*m.d1));
	res.b3=-invdet*(m.a1*(m.b3*m.d4-m.b4*m.d3)+m.a3*(m.b4*m.d1-m.b1*m.d4)+m.a4*(m.b1*m.d3-m.b3*m.d1));
	res.b4= invdet*(m.a1*(m.b3*m.c4-m.b4*m.c3)+m.a3*(m.b4*m.c1-m.b1*m.c4)+m.a4*(m.b1*m.c3-m.b3*m.c1));
	res.c1= invdet*(m.b1*(m.c2*m.d4-m.c4*m.d2)+m.b2*(m.c4*m.d1-m.c1*m.d4)+m.b4*(m.c1*m.d2-m.c2*m.d1));
	res.c2=-invdet*(m.a1*(m.c2*m.d4-m.c4*m.d2)+m.a2*(m.c4*m.d1-m.c1*m.d4)+m.a4*(m.c1*m.d2-m.c2*m.d1));
	res.c3= invdet*(m.a1*(m.b2*m.d4-m.b4*m.d2)+m.a2*(m.b4*m.d1-m.b1*m.d4)+m.a4*(m.b1*m.d2-m.b2*m.d1));
	res.c4=-invdet*(m.a1*(m.b2*m.c4-m.b4*m.c2)+m.a2*(m.b4*m.c1-m.b1*m.c4)+m.a4*(m.b1*m.c2-m.b2*m.c1));
	res.d1=-invdet*(m.b1*(m.c2*m.d3-m.c3*m.d2)+m.b2*(m.c3*m.d1-m.c1*m.d3)+m.b3*(m.c1*m.d2-m.c2*m.d1));
	res.d2= invdet*(m.a1*(m.c2*m.d3-m.c3*m.d2)+m.a2*(m.c3*m.d1-m.c1*m.d3)+m.a3*(m.c1*m.d2-m.c2*m.d1));
	res.d3=-invdet*(m.a1*(m.b2*m.d3-m.b3*m.d2)+m.a2*(m.b3*m.d1-m.b1*m.d3)+m.a3*(m.b1*m.d2-m.b2*m.d1));
	res.d4= invdet*(m.a1*(m.b2*m.c3-m.b3*m.c2)+m.a2*(m.b3*m.c1-m.b1*m.c3)+m.a3*(m.b1*m.c2-m.b2*m.c1));
	return res;
}

struct aiMatrix4x4 aiQuaternion_GetMatrix(struct aiQuaternion q)
{
	struct aiMatrix4x4 res;
	memset(&res, 0, sizeof res);
	res.a1 = 1.0f - 2.0f * (q.y * q.y + q.z * q.z);
	res.a2 = 2.0f * (q.x * q.y - q.z * q.w);
	res.a3 = 2.0f * (q.x * q.z + q.y * q.w);
	res.a4 = 0;
	res.b1 = 2.0f * (q.x * q.y + q.z * q.w);
	res.b2 = 1.0f - 2.0f * (q.x * q.x + q.z * q.z);
	res.b3 = 2.0f * (q.y * q.z - q.x * q.w);
	res.b4 = 0;
	res.c1 = 2.0f * (q.x * q.z - q.y * q.w);
	res.c2 = 2.0f * (q.y * q.z + q.x * q.w);
	res.c3 = 1.0f - 2.0f * (q.x * q.x + q.y * q.y);
	res.c4 = 0;
	res.d1 = 0; res.d2 = 0; res.d3 = 0; res.d4 = 1;
	return res;
}

char basename[1024];

int numtags = 0;
char **taglist = NULL;

#define MAXBLEND 12
#define MIN(a,b) ((a)<(b)?(a):(b))

struct vb {
	int b[MAXBLEND];
	float w[MAXBLEND];
	int n;
};

struct material {
	struct aiMaterial *material;
	char file[100];
	char name[100];
};

struct material matmap[1000];
int nummats = 0;

struct bone {
	char *name;
	int number; // for iqe export
	int parent;
	int isbone;
	struct aiNode *node;
	struct aiMatrix4x4 invpose; // inv(parent * pose)
	struct aiMatrix4x4 abspose; // (parent * pose)
	struct aiMatrix4x4 pose;
	struct aiMatrix4x4 firstpose; // pose for the first frame of an animation, to test for looping
};

int need_to_bake_skin = 0;
int save_all_bones = 0;
int doanim = 0;
int dobone = 0;

struct bone bonelist[1000];
int numbones = 0;

int find_bone(char *name)
{
	int i;
	for (i = 0; i < numbones; i++)
		if (!strcmp(name, bonelist[i].name))
			return i;
	return -1;
}

char *get_base_name(char *s)
{
	char *p = strrchr(s, '/');
	if (!p) p = strrchr(s, '\\');
	if (!p) return s;
	return p + 1;
}

char *node_name(char *orig)
{
	static char buf[200];
	if (orig == buf) return orig; // no need to clean the same name twice ;)
	char *p = orig;
	if (strstr(orig, "node-") == orig)
		orig += 5;
	strcpy(buf, orig);
	for (p = buf; *p; p++)
		*p = tolower(*p);
	return buf;
}

char *find_material(struct aiMaterial *material)
{
	int i, count;
	char buf[200], *p;
	struct aiString str;

	for (i = 0; i < nummats; i++)
		if (matmap[i].material == material)
			return matmap[i].name;

	if (!aiGetMaterialString(material, AI_MATKEY_TEXTURE_DIFFUSE(0), &str))
		strcpy(buf, get_base_name(str.data));
	else
		strcpy(buf, "unknown.png");
	p = strrchr(buf, '.');
	if (p) *p = 0;

	count = 0;
	for (i = 0; i < nummats; i++)
		if (!strcmp(matmap[i].file, buf))
			count++;

	matmap[nummats].material = material;
	strcpy(matmap[nummats].file, buf);
	sprintf(matmap[nummats].name, "%s,%d", buf, count);
	nummats++;

	p = matmap[nummats-1].name;
	while (*p) { *p = tolower(*p); p++; }

	return matmap[nummats-1].name;
}

void print_matrix(char *name, struct aiMatrix4x4 m)
{
	fprintf(stderr, "matrix %s %f %f %f %f %f %f %f %f %f\n", name,
			m.a1, m.a2, m.a3,
			m.b1, m.b2, m.b3,
			m.c1, m.c2, m.c3);
}

// --- figure out which bones are part of armature ---

void mark_bone_parents(int i)
{
	while (i >= 0) {
		bonelist[i].isbone |= 0x20;
		i = bonelist[i].parent;
	}
}

void mark_tags(void)
{
	int i, k;
	for (k = 0; k < numtags; k++) {
		fprintf(stderr, "marking tag %s\n", taglist[k]);
		for (i = 0; i < numbones; i++) {
			if (!strcmp(taglist[k], node_name(bonelist[i].name))) {
				bonelist[i].isbone |= 0x4000;
				break;
			}
		}
		if (i == numbones)
			fprintf(stderr, "\tnot found!\n");
	}
}

void build_bone_list_imp(struct aiNode *node, int parent)
{
	int i;

	bonelist[numbones].name = node->mName.data;
	bonelist[numbones].parent = parent;
	bonelist[numbones].isbone = 0;
	bonelist[numbones].node = node;

	// all non-bone nodes in our animated models have identity matrix
	// or are bones with no weights, so don't matter
	aiIdentityMatrix4(&bonelist[numbones].invpose);
	aiIdentityMatrix4(&bonelist[numbones].abspose);
	aiIdentityMatrix4(&bonelist[numbones].pose);

	parent = numbones++;
	for (i = 0; i < node->mNumChildren; i++)
		build_bone_list_imp(node->mChildren[i], parent);
}

void build_bone_list(const struct aiScene *scene)
{
	int i, k, a, b;
	int number = 0;

	// build list of all nodes
	build_bone_list_imp(scene->mRootNode, -1);

	// walk through all meshes and mark used bones
	for (k = 0; k < scene->mNumMeshes; k++) {
		struct aiMesh *mesh = scene->mMeshes[k];
		for (a = 0; a < mesh->mNumBones; a++) {
			b = find_bone(mesh->mBones[a]->mName.data);
			if (!bonelist[b].isbone) {
				bonelist[b].invpose = mesh->mBones[a]->mOffsetMatrix;
				bonelist[b].isbone |= 1;
			} else if (!need_to_bake_skin) {
				if (memcmp(&bonelist[b].invpose, &mesh->mBones[a]->mOffsetMatrix, sizeof bonelist[b].invpose))
					need_to_bake_skin = 1;
			}
		}
	}

	// we now (in the single mesh case) have our bind pose
	// our invpose is set to the inv_bind_pose matrix
	// compute forward abspose and pose matrices here
	for (i = 0; i < numbones; i++) {
		if (bonelist[i].isbone) {
			bonelist[i].abspose = aiInverseMatrix(bonelist[i].invpose);
			bonelist[i].pose = bonelist[i].abspose;
			if (bonelist[i].parent >= 0) {
				struct aiMatrix4x4 m = bonelist[bonelist[i].parent].invpose;
				aiMultiplyMatrix4(&m, &bonelist[i].pose);
				bonelist[i].pose = m;
			}
		} else {
			// no inv_bind_pose matrix (so not used by skin)
			// take the pose from the first frame of animation
			bonelist[i].pose = bonelist[i].node->mTransformation;
			bonelist[i].abspose = bonelist[i].pose;
			if (bonelist[i].parent >= 0) {
				bonelist[i].abspose = bonelist[bonelist[i].parent].abspose;
				aiMultiplyMatrix4(&bonelist[i].abspose, &bonelist[i].pose);
			}
			bonelist[i].invpose = aiInverseMatrix(bonelist[i].abspose);
		}
	}

	// walk through all anims and mark used bones
	for (i = 0; i < scene->mNumAnimations; i++) {
		const struct aiAnimation *anim = scene->mAnimations[i];
		for (k = 0; k < anim->mNumChannels; k++) {
			b = find_bone(anim->mChannels[k]->mNodeName.data);
			bonelist[b].isbone |= 0x300;
		}
	}

	// mark special bones named on command line as "tags" to attach stuff
	mark_tags();

	// select all parents of bones
	for (i = 0; i < numbones; i++) {
		if (bonelist[i].isbone)
			mark_bone_parents(i);
	}

	// select all children of bones as well
	if (save_all_bones) {
		for (i = 0; i < numbones; i++) {
			if (!bonelist[i].isbone)
				if (bonelist[i].parent >= 0 && bonelist[bonelist[i].parent].isbone)
					bonelist[i].isbone |= 0x1000;
		}
	}

	// skip 'MaxScene' node
	if (!strcmp(bonelist[0].name, "MaxScene")) {
		bonelist[0].isbone = 0;
		bonelist[0].number = -1;
	}

	for (i = 0; i < numbones; i++)
		if (!bonelist[i].isbone)
			fprintf(stderr, "skipping bone %s\n", node_name(bonelist[i].name));

	// assign IQE numbers to bones
	for (i = 0; i < numbones; i++)
		if (bonelist[i].isbone)
			bonelist[i].number = number++;
}

// --- armature hierarchy and bind pose ---

void export_pose(FILE *out, struct aiMatrix4x4 m, int i, int frame)
{
	struct aiMatrix4x4 reflect = { 1,0,0,0, 0,1,0,0, 0,0,-1,0, 0,0,0,1 };
	struct aiQuaternion rot;
	struct aiVector3D pos, scale;

	// ZO_MO_Gibbai, Box05, among others have a "mirror" component.
	// This screws up quaternion calculations.
	// Negate that by mirroring in the Z direction and hope for the best.
	if (aiDeterminant(m) < 0) {
		aiMultiplyMatrix4(&m, &reflect);
		fprintf(stderr, "correcting mirror transformation in pose %d: %s\n", frame, bonelist[i].name);
		// compensate for reflection in rotation?
		// ... or rebuild bone from vector, and force angle to be up
	}

	// Double test that the quat conversion is okay (call it paranoia)
	aiDecomposeMatrix(&m, &scale, &rot, &pos);
	float mag = sqrtf(rot.x*rot.x+rot.y*rot.y+rot.z*rot.z+rot.w*rot.w);
	if (fabs(mag-1)>0.001) {
		fprintf(stderr, "strange matrix in pose %d: %s (quat mag=%g)\n", frame, bonelist[i].name, mag);
		print_matrix("strange matrix", m);
		aiMultiplyMatrix4(&m, &reflect);
	}

#if 1
	aiDecomposeMatrix(&m, &scale, &rot, &pos);

	// truncate near-zero values to zero to save space in ascii export format
	float PREC = 3e-5; // 15 bits for 0..1, give or take
	if (fabs(pos.x) < PREC) pos.x = 0;
	if (fabs(pos.y) < PREC) pos.y = 0;
	if (fabs(pos.z) < PREC) pos.z = 0;
	if (fabs(rot.x) < PREC) rot.x = 0;
	if (fabs(rot.y) < PREC) rot.y = 0;
	if (fabs(rot.z) < PREC) rot.z = 0;
	if (fabs(rot.w) < PREC) rot.w = 0;
	if (fabs(scale.x-1) < PREC) scale.x = 1;
	if (fabs(scale.y-1) < PREC) scale.y = 1;
	if (fabs(scale.z-1) < PREC) scale.z = 1;

	if (scale.x != 1 || scale.y != 1 || scale.z != 1)
		fprintf(out, "pq %g %g %g %g %g %g %g %g %g %g\n",
			pos.x, pos.y, pos.z,
			rot.x, rot.y, rot.z, rot.w,
			scale.x, scale.y, scale.z);
	else
		fprintf(out, "pq %g %g %g %g %g %g %g\n",
			pos.x, pos.y, pos.z,
			rot.x, rot.y, rot.z, rot.w);
#else
	fprintf(out, "pm %g %g %g %g %g %g %g %g %g %g %g %g\n",
			m.a4, m.b4, m.c4,
			m.a1, m.a2, m.a3,
			m.b1, m.b2, m.b3,
			m.c1, m.c2, m.c3);
#endif
}

void export_bone_list(FILE *out)
{
	int i;

	fprintf(out, "\n");
	for (i = 0; i < numbones; i++) {
		if (bonelist[i].isbone) {
			if (bonelist[i].parent >= 0)
				fprintf(out, "joint %s %d\n",
					node_name(bonelist[i].name),
					bonelist[bonelist[i].parent].number);
			else
				fprintf(out, "joint %s -1\n", node_name(bonelist[i].name));
		}
	}

	fprintf(out, "\n");
	for (i = 0; i < numbones; i++)
		if (bonelist[i].isbone)
			export_pose(out, bonelist[i].pose, i, -1);
}

void export_frame(FILE *out, int frame)
{
	int i;
	fprintf(out, "\n");
	fprintf(out, "frame\n");
	for (i = 0; i < numbones; i++) {
		bonelist[i].abspose = bonelist[i].pose;
		if (bonelist[i].parent >= 0) {
			bonelist[i].abspose = bonelist[bonelist[i].parent].abspose;
			aiMultiplyMatrix4(&bonelist[i].abspose, &bonelist[i].pose);
		}
		if (bonelist[i].isbone)
			export_pose(out, bonelist[i].pose, i, frame);
	}
}

void apply_initial_frame(void)
{
	int i;
	for (i = 0; i < numbones; i++) {
		bonelist[i].pose = bonelist[i].node->mTransformation;
	}
}

void apply_frame(const struct aiAnimation *anim, int frame, int len)
{
	int i, a;
	for (i = 0; i < anim->mNumChannels; i++) {
		struct aiNodeAnim *chan = anim->mChannels[i];
		int rotframe = MIN(frame, chan->mNumRotationKeys - 1);
#if 0
		int posframe = MIN(frame, chan->mNumPositionKeys - 1);
		int scaleframe = MIN(frame, chan->mNumScalingKeys - 1);
		struct aiVector3D pos = chan->mPositionKeys[posframe].mValue;
 		struct aiQuaternion rot = chan->mRotationKeys[rotframe].mValue;
 		struct aiVector3D scale = chan->mScalingKeys[rotframe].mValue;
		if (fabs(scale.x - 1) > 0.001 || fabs(scale.y - 1) > 0.001 || fabs(scale.z - 1) > 0.001)
			fprintf(stderr, "scale %s = %g %g %g\n", chan->mNodeName.data, scale.x, scale.y, scale.z);
		struct aiMatrix4x4 m = aiQuaternion_GetMatrix(rot);
		m.a4 = pos.x; m.b4 = pos.y; m.c4 = pos.z;
#else
		// requires modified assimp
		struct aiMatrix4x4 m = chan->mRotationKeys[rotframe].mMatrixValue;
#endif
		a = find_bone(chan->mNodeName.data);
		bonelist[a].pose = m;
	}
}

int cmpmat(struct aiMatrix4x4 a, struct aiMatrix4x4 b, int boneidx)
{
	float PREC = 0.02; // voodoo value, but only used to automatically set "loop" flag
	int r =	fabs(a.a1 - b.a1) > PREC || fabs(a.a2 - b.a2) > PREC ||
		fabs(a.a3 - b.a3) > PREC || fabs(a.a4 - b.a4) > PREC ||
		fabs(a.b1 - b.b1) > PREC || fabs(a.b2 - b.b2) > PREC ||
		fabs(a.b3 - b.b3) > PREC || fabs(a.b4 - b.b4) > PREC ||
		fabs(a.c1 - b.c1) > PREC || fabs(a.c2 - b.c2) > PREC ||
		fabs(a.c3 - b.c3) > PREC || fabs(a.c4 - b.c4) > PREC;
	if (r)
		printf("diffing first and last pose (%s):\n\t%.4f %.4f %.4f %.4f\n\t%.4f %.4f %.4f %.4f\n\t%.4f %.4f %.4f %.4f\n",
			bonelist[boneidx].name,
			fabs(a.a1 - b.a1), fabs(a.a2 - b.a2),
			fabs(a.a3 - b.a3), fabs(a.a4 - b.a4),
			fabs(a.b1 - b.b1), fabs(a.b2 - b.b2),
			fabs(a.b3 - b.b3), fabs(a.b4 - b.b4),
			fabs(a.c1 - b.c1), fabs(a.c2 - b.c2),
			fabs(a.c3 - b.c3), fabs(a.c4 - b.c4));
	return r;
}

void export_animations(FILE *out, const struct aiScene *scene)
{
	int i, k, a, len, loop;
	for (i = 0; i < scene->mNumAnimations; i++) {
		const struct aiAnimation *anim = scene->mAnimations[i];
		if (scene->mNumAnimations > 1)
			fprintf(out, "\nanimation %s,%02d\n", basename, i);
		else
			fprintf(out, "\nanimation %s\n", basename);
		len = anim->mChannels[0]->mNumPositionKeys;

		apply_initial_frame();

		// compare first and last frames. if they are (nearly) the same,
		// skip the last frame and set the loop flag
		if (len > 1) {
			apply_frame(anim, 0, len);
			for (k = 0; k < numbones; k++)
				if (bonelist[k].isbone)
					bonelist[k].firstpose = bonelist[k].pose;
			apply_frame(anim, len-1, len);
			loop = 1;
			for (k = 0; k < numbones; k++)
				if (bonelist[k].isbone)
					if (cmpmat(bonelist[k].firstpose, bonelist[k].pose, k)) {
						loop = 0;
						break;
					}
		} else {
			loop = 0;
		}

		fprintf(out, "framerate 30\n");
		if (loop) {
			printf("detected looping animation\n");
			fprintf(out, "loop\n");
		}

		// TODO: len - loop -- skip last frame in loops?
		for (a = 0; a < len; a++) {
			apply_frame(anim, a, len);
			export_frame(out, a);
		}
	}
}

void bake_mesh_skin(const struct aiMesh *mesh)
{
	int i, k, b;
	struct aiMatrix3x3 mat3;
	struct aiMatrix4x4 bonemat[1000], mat;
	struct aiVector3D *outpos, *outnorm;

	if (mesh->mNumBones == 0)
		return;

	outpos = malloc(mesh->mNumVertices * sizeof *outpos);
	outnorm = malloc(mesh->mNumVertices * sizeof *outnorm);
	memset(outpos, 0, mesh->mNumVertices * sizeof *outpos);
	memset(outnorm, 0, mesh->mNumVertices * sizeof *outpos);

	for (i = 0; i < numbones; i++) {
		bonelist[i].abspose = bonelist[i].pose;
		if (bonelist[i].parent >= 0) {
			bonelist[i].abspose = bonelist[bonelist[i].parent].abspose;
			aiMultiplyMatrix4(&bonelist[i].abspose, &bonelist[i].pose);
		}
	}

	for (i = 0; i < mesh->mNumBones; i++) {
		b = find_bone(mesh->mBones[i]->mName.data);
		bonemat[i] = bonelist[b].abspose;
		aiMultiplyMatrix4(&bonemat[i], &mesh->mBones[i]->mOffsetMatrix);
	}

	for (k = 0; k < mesh->mNumBones; k++) {
		struct aiBone *bone = mesh->mBones[k];
		b = find_bone(mesh->mBones[k]->mName.data);
		mat = bonemat[k];
		mat3.a1 = mat.a1; mat3.a2 = mat.a2; mat3.a3 = mat.a3;
		mat3.b1 = mat.b1; mat3.b2 = mat.b2; mat3.b3 = mat.b3;
		mat3.c1 = mat.c1; mat3.c2 = mat.c2; mat3.c3 = mat.c3;
		for (i = 0; i < bone->mNumWeights; i++) {
			struct aiVertexWeight vw = bone->mWeights[i];
			int v = vw.mVertexId;
			float w = vw.mWeight;
			struct aiVector3D srcpos = mesh->mVertices[v];
			struct aiVector3D srcnorm = mesh->mNormals[v];
			aiTransformVecByMatrix4(&srcpos, &mat);
			aiTransformVecByMatrix3(&srcnorm, &mat3);
			outpos[v].x += srcpos.x * w;
			outpos[v].y += srcpos.y * w;
			outpos[v].z += srcpos.z * w;
			outnorm[v].x += srcnorm.x * w;
			outnorm[v].y += srcnorm.y * w;
			outnorm[v].z += srcnorm.z * w;
		}
	}

	memcpy(mesh->mVertices, outpos, mesh->mNumVertices * sizeof *outpos);
	memcpy(mesh->mNormals, outnorm, mesh->mNumVertices * sizeof *outnorm);

	free(outpos);
	free(outnorm);
}

void bake_scene_skin(const struct aiScene *scene)
{
	int i;
	fprintf(stderr, "baking skin to recreate base pose in multi-mesh model\n");
	for (i = 0; i < scene->mNumMeshes; i++)
		bake_mesh_skin(scene->mMeshes[i]);
}

void export_node(FILE *out, const struct aiScene *scene, const struct aiNode *node,
	struct aiMatrix4x4 mat, char *nodename)
{
	struct aiMatrix3x3 mat3;
	int i, k, t, a;

	aiMultiplyMatrix4(&mat, &node->mTransformation);
	mat3.a1 = mat.a1; mat3.a2 = mat.a2; mat3.a3 = mat.a3;
	mat3.b1 = mat.b1; mat3.b2 = mat.b2; mat3.b3 = mat.b3;
	mat3.c1 = mat.c1; mat3.c2 = mat.c2; mat3.c3 = mat.c3;

	if (!strstr(node->mName.data, "$ColladaAutoName$"))
		nodename = (char*)node->mName.data;

	nodename = node_name(nodename);

	for (i = 0; i < node->mNumMeshes; i++) {
		struct aiMesh *mesh = scene->mMeshes[node->mMeshes[i]];
		struct aiMaterial *material = scene->mMaterials[mesh->mMaterialIndex];

		/* skip non-boned meshes if we have a skeleton */
		if (mesh->mNumBones == 0 && dobone) {
			fprintf(stderr, "skipping mesh %d in node %s (no bones)\n", i, nodename);
			continue;
		}

		struct vb *vb = (struct vb*) malloc(mesh->mNumVertices * sizeof(*vb));
		memset(vb, 0, mesh->mNumVertices * sizeof(*vb));

		fprintf(out, "\n");
		if (node->mNumMeshes > 99)
			fprintf(out, "mesh %s,%03d\n", nodename, i);
		else if (node->mNumMeshes > 9)
			fprintf(out, "mesh %s,%02d\n", nodename, i);
		else if (node->mNumMeshes > 1)
			fprintf(out, "mesh %s,%d\n", nodename, i);
		else
			fprintf(out, "mesh %s\n", nodename);

		fprintf(out, "material %s\n", find_material(material));

		for (k = 0; k < mesh->mNumBones; k++) {
			struct aiBone *bone = mesh->mBones[k];
			a = find_bone(bone->mName.data);
			for (t = 0; t < bone->mNumWeights; t++) {
				struct aiVertexWeight *w = mesh->mBones[k]->mWeights + t;
				int idx = w->mVertexId;
				if (vb[idx].n < MAXBLEND) {
					vb[idx].b[vb[idx].n] = bonelist[a].number;
					vb[idx].w[vb[idx].n] = w->mWeight;
					vb[idx].n++;
				}
			}
		}

		for (k = 0; k < mesh->mNumVertices; k++) {
			struct aiVector3D vp = mesh->mVertices[k];
			aiTransformVecByMatrix4(&vp, &mat);
			fprintf(out, "vp %g %g %g\n", vp.x, vp.y, vp.z);
			if (mesh->mTextureCoords[0]) {
				float u = mesh->mTextureCoords[0][k].x;
				float v = 1 - mesh->mTextureCoords[0][k].y;
				fprintf(out, "vt %g %g\n", u, v);
			} else fprintf(out, "vt 0 0\n");
			if (mesh->mNormals) {
				struct aiVector3D vn = mesh->mNormals[k];
				aiTransformVecByMatrix3(&vn, &mat3);
#ifdef FLIP
				fprintf(out, "vn %g %g %g\n", -vn.x, -vn.y, -vn.z);
#else
				fprintf(out, "vn %g %g %g\n", vn.x, vn.y, vn.z);
#endif
			}
			if (mesh->mColors[0]) {
				float r = mesh->mColors[0][k].r; r = floorf(r * 255) / 255;
				float g = mesh->mColors[0][k].g; g = floorf(g * 255) / 255;
				float b = mesh->mColors[0][k].b; b = floorf(b * 255) / 255;
				float a = mesh->mColors[0][k].a; a = floorf(a * 255) / 255;
				fprintf(out, "vc %g %g %g %g\n", r, g, b, 1.0);
			}
			if (mesh->mNumBones > 0) {
				fprintf(out, "vb");
				for (t = 0; t < vb[k].n; t++)
					fprintf(out, " %d %g", vb[k].b[t], vb[k].w[t]);
				fprintf(out, "\n");
			}
		}

		for (k = 0; k < mesh->mNumFaces; k++) {
			struct aiFace *face = mesh->mFaces + k;
			assert(face->mNumIndices == 3);
#ifdef FLIP
			fprintf(out, "fm %d %d %d\n", face->mIndices[0], face->mIndices[2], face->mIndices[1]);
#else
			fprintf(out, "fm %d %d %d\n", face->mIndices[0], face->mIndices[1], face->mIndices[2]);
#endif
		}

		free(vb);
	}

	for (i = 0; i < node->mNumChildren; i++)
		export_node(out, scene, node->mChildren[i], mat, nodename);
}

void usage()
{
	fprintf(stderr, "usage: assiqe [options] [-o out.iqe] input.dae [tags ...]\n");
	fprintf(stderr, "\t-a -- only export animations\n");
	fprintf(stderr, "\t-b -- export unused bones too\n");
	fprintf(stderr, "\t-m -- force bind pose to first animation\n");
	fprintf(stderr, "\t-o filename -- save output to file\n");
	exit(1);
}

int main(int argc, char **argv)
{
	FILE *file;
	const struct aiScene *scene;
	struct aiMatrix4x4 mat;
	char *p;
	int c, k;

	int flags = aiProcess_Triangulate;
	flags |= aiProcess_JoinIdenticalVertices;
	flags |= aiProcess_GenSmoothNormals;
	flags |= aiProcess_GenUVCoords;
	flags |= aiProcess_TransformUVCoords;
	//flags |= aiProcess_LimitBoneWeights;
	//flags |= aiProcess_FindInvalidData;
	flags |= aiProcess_ImproveCacheLocality;
	//flags |= aiProcess_RemoveRedundantMaterials;
	//flags |= aiProcess_OptimizeMeshes;
	//flags |= aiProcess_OptimizeGraph;
	//flags |= aiProcess_RemoveComponent;

	aiIdentityMatrix4(&mat);

//	struct aiLogStream stream;
//	stream = aiGetPredefinedLogStream(aiDefaultLogStream_FILE, "import.log");
//	aiAttachLogStream(&stream);

	char *output = NULL;
	char *input = NULL;
	int domesh = 1;

	while ((c = getopt(argc, argv, "abmo:")) != -1) {
		switch (c) {
		case 'a': domesh = 0; break;
		case 'b': save_all_bones = 1; break;
		case 'm': need_to_bake_skin = 1; break;
		case 'o': output = optarg++; break;
		default: usage(); break;
		}
	}

	if (optind == argc)
		usage();

	input = argv[optind++];

	p = strrchr(input, '/');
	if (!p) p = strrchr(input, '\\');
	if (!p) p = input; else p++;
	strcpy(basename, p);
	p = strrchr(basename, '.');
	if (p) *p = 0;

	numtags = argc - optind;
	taglist = argv + optind;

	fprintf(stderr, "loading %s\n", input);
	scene = aiImportFile(input, flags);
	if (!scene) {
		fprintf(stderr, "cannot import '%s'\n", input);
		exit(1);
	}

	if (output) {
		fprintf(stderr, "saving %s\n", output);
		file = fopen(output, "w");
		if (!file) {
			fprintf(stderr, "cannot open output file: '%s'\n", output);
			exit(1);
		}
	} else {
		file = stdout;
	}

	fprintf(file, "# Inter-Quake Export\n");

	// Nuke the Z-UP to Y-UP rotation matrix (if MaxScene)
	if (!strcmp(scene->mRootNode->mName.data, "MaxScene"))
		aiIdentityMatrix4(&scene->mRootNode->mTransformation);

	for (k = 0; k < scene->mNumMeshes; k++)
		if (scene->mMeshes[k]->mNumBones > 0)
			dobone = 1;
	if (scene->mNumAnimations > 0)
		doanim = 1;

	build_bone_list(scene);
	if (need_to_bake_skin) {
		apply_initial_frame();
		bake_scene_skin(scene);
	}

	// Nuke all non-bone transforms.
	// Should take care of icky mesh transforms that mess up our bind pose
	// since mOffsetMatrix is in local mesh space, not global model space.
	if (dobone) {
		for (k = 0; k < numbones; k++)
			if (!bonelist[k].isbone)
				aiIdentityMatrix4(&bonelist[k].node->mTransformation);
	}

	if (dobone) export_bone_list(file);
	if (domesh) export_node(file, scene, scene->mRootNode, mat, "unnamed");
	if (doanim) export_animations(file, scene);
	else if (!domesh) { // oops, forced anim but only one frame
		// 1-frame animation
		fprintf(file, "\nanimation %s\n", basename);
		fprintf(file, "framerate 30\n");
		apply_initial_frame();
		export_frame(file, 0);
	}

	fclose(file);

	aiReleaseImport(scene);

	return 0;
}
