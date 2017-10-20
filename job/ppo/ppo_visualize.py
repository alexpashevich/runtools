import os
import sys
import argparse
import shutil
import importlib
from pytools.tools import cmd
from settings import CODE_DIRNAME
from copy import copy
import agents.scripts.visualize as visualizer
import tensorflow as tf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logdir', type=str,
                        help='Logdir with checkpoints.')
    parser.add_argument('-s0', '--render_seed0', type=bool, default=False, required=False,
                        help='Whether to render the seed0 policies.')

    args = parser.parse_args()
    # clear path from local codes of agents and rlgrasp
    sys_path_clean = []
    for path in sys.path:
        if CODE_DIRNAME not in path:
            sys_path_clean.append(path)
    exp_name_general = os.path.basename(os.path.normpath(args.logdir))
    outdirs = []

    for seed_folder in next(os.walk(args.logdir))[1]:
        if 'seed' not in seed_folder:
            continue
        if seed_folder == 'seed0' and not args.render_seed0:
            continue
        # set correct python path
        sys.path = copy(sys_path_clean)
        exp_name = exp_name_general + '-' + seed_folder.replace('seed', 's')
        cachedir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Links/", exp_name)
        sys.path.append(os.path.join(cachedir, 'agents'))
        sys.path.append(os.path.join(cachedir, 'rlgrasp'))

        timestamp_folders = next(os.walk(os.path.join(args.logdir, seed_folder)))[1]
        if len(timestamp_folders) > 1:
            print('WARNING: will render from {} and ignore {}'.format(timestamp_folders[-1],
                                                                      timestamp_folders[:-1]))
        finallogdir = os.path.join(args.logdir, seed_folder, timestamp_folders[-1])
        assert(os.path.exists(finallogdir))

        finaloutdir = finallogdir.replace('Logs/agents', 'Logs/renders')
        if os.path.exists(finaloutdir):
            shutil.rmtree(finaloutdir)
        os.makedirs(finaloutdir)
        outdirs.append(finaloutdir)
        script = 'python3 -m agents.scripts.visualize --logdir={} --outdir={}'.format(finallogdir,
                                                                                      finaloutdir)
        importlib.reload(visualizer)
        visualizer.visualize(finallogdir, finaloutdir, num_agents=4, num_episodes=8,
                  checkpoint=None, env_processes=True)
        # cmd(script)
        cmd('rm {}/*.manifest.json'.format(finaloutdir))
        cmd('rm {}/*.meta.json'.format(finaloutdir))
        tf.reset_default_graph()
    print('Videos are written to:')
    for outdir in outdirs:
        print(outdir)
    print('Hope that policies do grasp :)')


if __name__ == '__main__':
    main()
