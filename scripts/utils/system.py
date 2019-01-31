import os
import sys
import shutil

from git import Git
from copy import copy
from pytools.tools import cmd

from settings import CODE_DIRNAME

USED_CODE_DIRS = 'mime', 'ppo', 'bc'


def get_sys_path_clean():
    sys_path_clean = []
    for path in sys.path:
        if CODE_DIRNAME not in path and CODE_DIRNAME.replace('thoth/', '') not in path:
            sys_path_clean.append(path)
    return sys_path_clean


def change_sys_path(sys_path_clean, logdir):
    sys.path = copy(sys_path_clean)
    exp_name = os.path.basename(os.path.normpath(logdir))
    cachedir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    for code_dir in USED_CODE_DIRS:
        sys.path.append(os.path.join(cachedir, code_dir))


def checkout_repo(repo, commit_tag):
    g = Git(repo)
    g.checkout(commit_tag)
    print('checkouted {} to {}'.format(repo, commit_tag))


def cache_code_dir(
        exp_name, commit_agents, commit_grasp_env,
        sym_link=False, sym_link_to_exp=None):
    cache_dir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    if os.path.exists(cache_dir):
        if not os.path.islink(cache_dir):
            shutil.rmtree(cache_dir)
        else:
            os.unlink(cache_dir)
    if not sym_link:
        os.makedirs(cache_dir)
        for code_dir in USED_CODE_DIRS:
            cmd('cp -R /home/thoth/apashevi/Code/{} {}/'.format(code_dir, cache_dir))
    else:
        if not sym_link_to_exp:
            sym_link_to = '/home/thoth/apashevi/Code'
        else:
            sym_link_to = os.path.join('/scratch/gpuhost7/apashevi/Cache/Code/', sym_link_to_exp)
        os.symlink(sym_link_to, cache_dir)
    if commit_agents is not None:
        checkout_repo(os.path.join(cache_dir, 'agents'), commit_agents)
    if commit_grasp_env is not None:
        checkout_repo(os.path.join(cache_dir, 'rlgrasp'), commit_grasp_env)


def create_parent_log_dir(exp_name):
    print('exp_name is {}'.format(exp_name))
    log_dir = os.path.join("/scratch/gpuhost7/apashevi/Logs/agents", exp_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
