#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <assimp.h>
#include <aiMatrix4x4.h>
#include <aiMatrix3x3.h>
#include <aiColor4D.h>
#include <aiVector3D.h>
#include <aiPostProcess.h>
#include <aiScene.h>

// ASS: winding = CCW
// ASS: axis = Y-up, right handed (same as OpenGL)
// ASS: texture = origin at bottom left (same as OpenGL)
// ASS: matrix = row-major

// OBJ: Y-up
// OBJ: texture origin at top left

static int numvp = 1;
static int numvt = 1;
static int numvn = 1;

void export_materials(FILE *out, const struct aiScene *scene)
{
	struct aiString str;
	struct aiColor4D c;
	float f;
	int i;

	fprintf(out, "# Wavefront Material Library\n");
	fprintf(out, "# Created by assobj exporter\n");

	for (i = 0; i < scene->mNumMaterials; i++) {
		aiGetMaterialString(scene->mMaterials[i], AI_MATKEY_NAME, &str);
		fprintf(out, "\nnewmtl %s\n", str.data);

		if (!aiGetMaterialString(scene->mMaterials[i], AI_MATKEY_TEXTURE_AMBIENT(0), &str))
			fprintf(out, "map_Ka %s\n", str.data+1);
		if (!aiGetMaterialString(scene->mMaterials[i], AI_MATKEY_TEXTURE_DIFFUSE(0), &str))
			fprintf(out, "map_Kd %s\n", str.data+1);
		if (!aiGetMaterialString(scene->mMaterials[i], AI_MATKEY_TEXTURE_SPECULAR(0), &str))
			fprintf(out, "map_Ks %s\n", str.data+1);
		if (!aiGetMaterialString(scene->mMaterials[i], AI_MATKEY_TEXTURE_EMISSIVE(0), &str))
			fprintf(out, "map_Ke %s\n", str.data+1);

		if (!aiGetMaterialColor(scene->mMaterials[i], AI_MATKEY_COLOR_AMBIENT, &c))
			fprintf(out, "Ka %g %g %g\n", c.r, c.g, c.b);
		if (!aiGetMaterialColor(scene->mMaterials[i], AI_MATKEY_COLOR_DIFFUSE, &c))
			fprintf(out, "Kd %g %g %g\n", c.r, c.g, c.b);
		if (!aiGetMaterialColor(scene->mMaterials[i], AI_MATKEY_COLOR_SPECULAR, &c))
			fprintf(out, "Ks %g %g %g\n", c.r, c.g, c.b);
		if (!aiGetMaterialColor(scene->mMaterials[i], AI_MATKEY_COLOR_EMISSIVE, &c))
			fprintf(out, "Ke %g %g %g\n", c.r, c.g, c.b);

		if (!aiGetMaterialFloatArray(scene->mMaterials[i], AI_MATKEY_SHININESS, &f, 0))
			fprintf(out, "Ns %g\n", f);
	}
}

void export_scene(FILE *out, const struct aiScene *scene, const struct aiNode *node, struct aiMatrix4x4 mat,
	char *nodename)
{
	struct aiMatrix3x3 mat3;
	int i, k, t;

	aiMultiplyMatrix4(&mat, &node->mTransformation);
	mat3.a1 = mat.a1; mat3.a2 = mat.a2; mat3.a3 = mat.a3;
	mat3.b1 = mat.b1; mat3.b2 = mat.b2; mat3.b3 = mat.b3;
	mat3.c1 = mat.c1; mat3.c2 = mat.c2; mat3.c3 = mat.c3;

	if (!strstr(node->mName.data, "$ColladaAutoName$"))
		nodename = (char*)node->mName.data;

	for (i = 0; i < node->mNumMeshes; i++) {
		const struct aiMesh *mesh = scene->mMeshes[node->mMeshes[i]];
		const struct aiMaterial *material = scene->mMaterials[mesh->mMaterialIndex];
		struct aiString str;

		fprintf(out, "\n");
		if (node->mNumMeshes > 99)
			fprintf(out, "g %s,%03d\n", nodename, i);
		else if (node->mNumMeshes > 9)
			fprintf(out, "g %s,%02d\n", nodename, i);
		else if (node->mNumMeshes > 1)
			fprintf(out, "g %s,%d\n", nodename, i);
		else
			fprintf(out, "g %s\n", nodename);

		aiGetMaterialString(material, AI_MATKEY_NAME, &str);
		fprintf(out, "usemtl %s\n", str.data);

		for (k = 0; k < mesh->mNumVertices; k++) {
			struct aiVector3D vp = mesh->mVertices[k];
			aiTransformVecByMatrix4(&vp, &mat);
			fprintf(out, "v %.9g %.9g %.9g\n", vp.x, vp.y, vp.z);
			if (mesh->mTextureCoords[0]) {
				float u = mesh->mTextureCoords[0][k].x;
				float v = mesh->mTextureCoords[0][k].y;
				fprintf(out, "vt %.9g %.9g\n", u, v);
			}
			if (mesh->mNormals) {
				struct aiVector3D vn = mesh->mNormals[k];
				aiTransformVecByMatrix3(&vn, &mat3);
				fprintf(out, "vn %.9g %.9g %.9g\n", vn.x, vn.y, vn.z);
			}
		}
		for (k = 0; k < mesh->mNumFaces; k++) {
			const struct aiFace *face = mesh->mFaces + k;
			fprintf(out, "f");
			for (t = 0; t < face->mNumIndices; t++) {
				if (mesh->mTextureCoords[0] && mesh->mNormals)
					fprintf(out, " %d/%d/%d",
						face->mIndices[t]+numvp,
						face->mIndices[t]+numvt,
						face->mIndices[t]+numvn);
				else if (mesh->mTextureCoords[0])
					fprintf(out, " %d/%d",
						face->mIndices[t]+numvp,
						face->mIndices[t]+numvt);
				else if (mesh->mNormals)
					fprintf(out, " %d//%d",
						face->mIndices[t]+numvp,
						face->mIndices[t]+numvn);
				else
					fprintf(out, " %d",
						face->mIndices[t]+numvp);
			}
			fprintf(out, "\n");
		}
		numvp += mesh->mNumVertices;
		if (mesh->mTextureCoords[0]) numvt += mesh->mNumVertices;
		if (mesh->mNormals) numvn += mesh->mNumVertices;
	}

	for (i = 0; i < node->mNumChildren; i++) {
		export_scene(out, scene, node->mChildren[i], mat, nodename);
	}
}

int main(int argc, char **argv)
{
	char basename[1024];
	char objname[1024];
	char mtlname[1024];
	FILE *file;
	const struct aiScene *scene;
	struct aiMatrix4x4 mat;
	char *p;
	int i;

	int flags = aiProcess_Triangulate |
		aiProcess_JoinIdenticalVertices |
		aiProcess_GenSmoothNormals |
		aiProcess_LimitBoneWeights |
		aiProcess_GenUVCoords |
		aiProcess_TransformUVCoords |
		aiProcess_FindInvalidData;

	aiIdentityMatrix4(&mat);

	for (i = 1; i < argc; i++) {
		strcpy(basename, argv[i]);
		p = strrchr(basename, '.');
		if (p) *p = 0;
		strcpy(objname, basename); strcat(objname, ".obj");
		strcpy(mtlname, basename); strcat(mtlname, ".mtl");

		fprintf(stderr, "loading %s\n", argv[i]);
		scene = aiImportFile(argv[i], flags);
		if (!scene) {
			fprintf(stderr, "cannot import '%s'\n", argv[1]);
			exit(1);
		}

		p = strrchr(mtlname, '/');
		if (!p) p = strrchr(mtlname, '\\');
		if (!p) p = mtlname;

		numvp = numvt = numvn = 1;

		fprintf(stderr, "saving %s\n", mtlname);
		file = fopen(mtlname, "w");
		export_materials(file, scene);
		fclose(file);

		fprintf(stderr, "saving %s\n", objname);
		file = fopen(objname, "w");
		fprintf(file, "# Wavefront Model\n");
		fprintf(file, "# Created by assobj exporter\n");
		fprintf(file, "mtllib %s\n", p);
		export_scene(file, scene, scene->mRootNode, mat, "unnamed");
		fclose(file);

		aiReleaseImport(scene);
	}

	return 0;
}
