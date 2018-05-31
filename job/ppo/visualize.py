import os
import argparse
import shutil
import json

import tensorflow as tf

from pytools.tools import cmd
from job.ppo import utils


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logdir', type=str,
                        help='Logdir with checkpoints (seed folder).')
    parser.add_argument('-s0', '--render_seed0', type=utils.str2bool, default=False, required=False,
                        help='Whether to render the seed0 policies.')
    parser.add_argument('-o', '--only_seeds', type=str, default=None, required=False,
                        help='List of seeds to render in Json format (default = all).')

    args = parser.parse_args()

    # clear path from local codes of agents and rlgrasp
    sys_path_clean = utils.get_sys_path_clean()
    # set correct python path
    utils.change_sys_path(sys_path_clean, args.logdir)
    import agents.scripts.visualize as visualizer

    outdirs = []
    if args.only_seeds:
        seed_list = json.loads(args.only_seeds)
    else:
        seed_list = None

    for seed_folder in next(os.walk(args.logdir))[1]:
        if 'seed' not in seed_folder:
            continue
        if seed_folder == 'seed0' and not args.render_seed0:
            continue
        if seed_list is not None and int(seed_folder.replace('seed', '')) not in seed_list:
            continue

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
        visualizer.visualize(finallogdir, finaloutdir, num_agents=2, num_episodes=8,
                  checkpoint=None, env_processes=True)
        cmd('rm {}/*.manifest.json'.format(finaloutdir))
        cmd('rm {}/*.meta.json'.format(finaloutdir))
        tf.reset_default_graph()
    print('Videos are written to:')
    for outdir in outdirs:
        print(outdir)
    print('Hope that policies do grasp :)')


if __name__ == '__main__':
    main()
