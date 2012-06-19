#include "iqe.c"

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
