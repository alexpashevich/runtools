import os
import sys
import shutil

from copy import copy

from runtools.utils.python import cmd
from runtools.settings import CODEDIR_PATH, CACHEDIR_PATH, USED_CODE_DIRS


def get_python_path(exp_name):
    python_paths = os.environ['PYTHONPATH'].split(':')
    python_paths = [p for p in python_paths if len([True for dir in USED_CODE_DIRS if dir in p]) == 0]
    for code_dir in USED_CODE_DIRS:
        python_paths.append(os.path.join(CACHEDIR_PATH, exp_name, code_dir))
    return ':'.join(python_paths)


def checkout_repo(repo, commit_tag):
    from git import Git
    g = Git(repo)
    g.checkout('.')
    g.checkout(commit_tag)
    print('checkouted {} to {}'.format(repo, commit_tag))


def create_cache_dir(exp_name_list, cache_mode, git_commit_alfred, source_exp=None):
    cache_dir = os.path.join(CACHEDIR_PATH, exp_name_list[0])
    assert cache_mode in ('keep', 'copy', 'link')
    if cache_mode == 'keep':
        if not os.path.exists(cache_dir) and not os.path.islink(cache_dir):
            copy_code_dir(cache_dir, git_commit_alfred, sym_link=True, source_exp=source_exp)
        return

    copy_code_dir(cache_dir, git_commit_alfred, sym_link=(cache_mode == 'link'), source_exp=source_exp)

    # cache only the first exp directory, others are sym links to it
    for exp_id, exp_name in enumerate(exp_name_list[1:]):
        if exp_name not in exp_name_list[:1 + exp_id]:
            cache_dir = os.path.join(CACHEDIR_PATH, exp_name)
            copy_code_dir(cache_dir, None, sym_link=True, source_exp=exp_name_list[0])


def copy_code_dir(cache_dir, commit_alfred, sym_link=False, source_exp=None):
    source_code_dir = os.path.join(CACHEDIR_PATH, source_exp) if source_exp else CODEDIR_PATH
    print('{} code to {} from {}'.format('Symlinking' if sym_link else 'Copying', cache_dir, source_code_dir))
    # first free the distination code dir if it exists
    if os.path.exists(cache_dir):
        if not os.path.islink(cache_dir):
            shutil.rmtree(cache_dir)
        else:
            os.unlink(cache_dir)

    # then copy or symlink code there
    if not sym_link:
        os.makedirs(cache_dir)
        for code_dir in USED_CODE_DIRS:
            code_dir_path = os.path.join(source_code_dir, code_dir)
            # we do it in case the code dirs are symlinks
            os.makedirs(os.path.join(cache_dir, code_dir))
            cmd('cp -R {}/. {}/'.format(code_dir_path, os.path.join(cache_dir, code_dir)))
    else:
        os.symlink(source_code_dir, cache_dir)
    if commit_alfred is not None:
        checkout_repo(os.path.join(cache_dir, 'alfred'), commit_alfred)
