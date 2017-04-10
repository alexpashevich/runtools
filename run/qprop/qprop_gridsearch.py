import sys
from itertools import product
from run.qprop.qprop_run import RunQprop, read_args, create_temp_dir
from run.qprop.qprop_run import create_outworlds_dir, create_success_report_dir


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <args_file_fixed> <args_file_gridsearch>")

    args, exp_name, overwrite = read_args(sys.argv[1])

    # read args for gridsearch
    with open(sys.argv[2]) as f:
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

    for args_to_add in args_to_add_list:
        name_spec = args_to_add.replace(' ', '').replace('--', '-').replace('=', '-').replace('_', '-')
        new_exp_name = exp_name + name_spec
        args_full = args + ' ' + args_to_add
        args_full = args_full.replace('--exp=' + exp_name,
                                      '--exp=' + new_exp_name)
        args_full, overwrite_local = create_temp_dir(args_full, new_exp_name, overwrite)
        args_full = create_outworlds_dir(args_full, new_exp_name)
        args_full = create_success_report_dir(args_full, new_exp_name)
        print('running {} with args: {}'.format(new_exp_name, args_full))
        RunQprop([new_exp_name, args_full]).run()
