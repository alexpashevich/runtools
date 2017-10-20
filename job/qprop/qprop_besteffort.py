import sys
from itertools import product
from job.qprop.qprop_run import JobQprop, read_args, create_temp_dir, create_outworlds_dir
from job.qprop.qprop_gridsearch import parse_grid_args, get_gridsearch_jobs
from job.job_manager import manage

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <args_file_fixed> <args_file_gridsearch>")

    args, exp_name, overwrite = read_args(sys.argv[1])
    args_to_add_list = parse_grid_args(sys.argv[2])
    jobs_list = get_gridsearch_jobs(args, exp_name, overwrite, args_to_add_list)
    for job in jobs_list:
        job.besteffort = True
    manage(jobs_list, only_initialization=False)
