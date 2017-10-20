import sys
from itertools import product
from job.qprop.qprop_run import JobQprop, read_args, create_temp_dir, create_outworlds_dir
from job.job_manager import manage

def parse_grid_args(grid_args_file):
    with open(grid_args_file) as f:
        args_grid_list = f.read().splitlines()
    grid = []
    grid_names = []
    for line in args_grid_list:
        arg_name = line[:line.find('=')+1]
        values = line[line.find('=')+1:]
        values_list = values.split(',')
        grid.append(values_list)
        grid_names.append(arg_name)

    # make list of grid search args
    args_to_add_list = []
    for args_to_add in product(*grid):
        args_to_add_line = ''
        for i in range(len(grid_names)):
            args_to_add_line += grid_names[i] + args_to_add[i] + ' '
        args_to_add_list.append(args_to_add_line)
    return args_to_add_list

def get_gridsearch_jobs(args, exp_name, overwrite, args_to_add_list):
    jobs_list = []
    for args_to_add in args_to_add_list:
        name_spec = args_to_add.replace(' ', '').replace('.', '-').replace('--', '-').replace('=', '-').replace('_', '-')
        new_exp_name = exp_name + name_spec
        args_full = args + ' ' + args_to_add
        args_full = args_full.replace('--exp=' + exp_name,
                                      '--exp=' + new_exp_name)
        args_full, _ = create_temp_dir(args_full, new_exp_name, overwrite)
        args_full = create_outworlds_dir(args_full, new_exp_name)
        print('running {} with args: {}'.format(new_exp_name, args_full))
        jobs_list.append(JobQprop([new_exp_name, args_full]))
    return jobs_list


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <args_file_fixed> <args_file_gridsearch>")

    args, exp_name, overwrite = read_args(sys.argv[1])
    args_to_add_list = parse_grid_args(sys.argv[2])
    jobs_list = get_gridsearch_jobs(args, exp_name, overwrite, args_to_add_list)
    manage(jobs_list, only_initialization=False)

