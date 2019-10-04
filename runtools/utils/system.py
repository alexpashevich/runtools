import os
import sys
import shutil

from git import Git
from copy import copy

from runtools.utils.python import cmd
from runtools.settings import CODEDIR_PATH, CACHEDIR_PATH, LOGDIR_PATH, USED_CODE_DIRS


def get_sys_path_clean():
    sys_path_clean = []
    for path in sys.path:
        if CODEDIR_PATH not in path and CODEDIR_PATH.replace('thoth/', '') not in path:
            sys_path_clean.append(path)
    return sys_path_clean


def change_sys_path(sys_path_clean, logdir):
    sys.path = copy(sys_path_clean)
    exp_name = os.path.basename(os.path.normpath(logdir))
    cachedir = os.path.join(CACHEDIR_PATH, exp_name)
    for code_dir in USED_CODE_DIRS:
        sys.path.append(os.path.join(cachedir, code_dir))


def checkout_repo(repo, commit_tag):
    g = Git(repo)
    g.checkout(commit_tag)
    print('checkouted {} to {}'.format(repo, commit_tag))


def cache_code_dir(
        exp_name, commit_rlons, commit_mime,
        sym_link=False, sym_link_to_exp=None):
    cache_dir = os.path.join(CACHEDIR_PATH, exp_name)
    if os.path.exists(cache_dir):
        if not os.path.islink(cache_dir):
            shutil.rmtree(cache_dir)
        else:
            os.unlink(cache_dir)
    if not sym_link:
        os.makedirs(cache_dir)
        for code_dir in USED_CODE_DIRS:
            cmd('cp -R {} {}/'.format(os.path.join(CODEDIR_PATH, code_dir), cache_dir))
    else:
        if not sym_link_to_exp:
            sym_link_to = CODEDIR_PATH
        else:
            sym_link_to = os.path.join(CACHEDIR_PATH, sym_link_to_exp)
        os.symlink(sym_link_to, cache_dir)
    if commit_rlons is not None:
        checkout_repo(os.path.join(cache_dir, 'rlons'), commit_rlons)
    if commit_mime is not None:
        checkout_repo(os.path.join(cache_dir, 'mime'), commit_mime)


def create_parent_log_dir(exp_name):
    log_dir = os.path.join(LOGDIR_PATH, exp_name)
    print('Logs will be saved to {}'.format(log_dir))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)