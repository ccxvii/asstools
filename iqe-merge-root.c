#include "iqe.c"

int
main(int argc, char **argv)
{
	struct model *model;

	if (argc != 2) {
		fprintf(stderr, "usage: iqe-merge-root model.iqe\n");
		return 1;
	}

	model = load_iqe_model(argv[1]);

	delete_bone(model, "name");
	delete_bone(model, "dummy01");
	delete_bone(model, "dummy01popopo");

	if (findbone(model, "bip01") > -1)
	{
		delete_bone(model, "bip01_footsteps");
		if (findbone(model, "unnamed") > -1)
			merge_bones(model, "unnamed", "bip01");
		if (findbone(model, "bip01_pelvis") > -1)
			merge_bones(model, "bip01", "bip01_pelvis");
	}

	if (findbone(model, "bip02") > -1)
	{
		delete_bone(model, "bip02_footsteps");
		if (findbone(model, "bip02_pelvis") > -1)
			merge_bones(model, "bip02", "bip02_pelvis");
	}

	save_iqe_model(model);

	return 0;
}
