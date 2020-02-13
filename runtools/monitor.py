#!/usr/bin/env python

import curses
import os
import time
import json

import subprocess as sp

from runtools.utils.python import cmd
from runtools.settings import LOGIN, CPU_MACHINE, GPU_MACHINE, OAR_LOG_PATH, MODEL_LOG_PATH

MAX_LENGTH = 80


def tail(f, n):
    assert n >= 0
    pos, lines = n+1, []
    while len(lines) <= n:
        try:
            f.seek(-pos, 2)
        except IOError:
            f.seek(0)
            break
        finally:
            lines = list(f)
        pos *= 2
    return lines[-n:]


def parse_stage(oarout):
    stages = ('value_data', 'value_net', 'heatmaps_data', 'heatmaps_net')
    # skip_strings = ['Skipping stage {}'.format(s) for s in stages]
    start_strings = ['Creating config for {}'.format(s) for s in stages]
    stage_idx = -1
    for idx, start_string in enumerate(start_strings):
        if start_string in oarout:
            stage_idx = idx
    if stage_idx != -1:
        return stages[stage_idx]
    return 'n/a'


def cut_step(stage, oarout, oarerr):
    if 'net' in stage or stage == 'n/a':
        # training phase
        begin_string, end_string = 'Epoch ', '\n'
        oar_string = oarout
    else:
        # collection phase
        begin_string, end_string = '| ', ' ['
        oar_string = oarerr
    if begin_string in oar_string and end_string in oar_string:
        begin = oar_string.rfind(begin_string)
        string_temp = oar_string[begin + len(begin_string):]
        end = string_temp.find(end_string)
        step = string_temp[:end].strip()
        if len(step) < 16:
            return step
    return 'n/a'


def cut_accuracy(accuracy, oarout):
    begin_string, end_string = 'accuracy_{} '.format(accuracy[2:]), ','
    if begin_string in oarout and end_string in oarout:
        begin = oarout.rfind(begin_string)
        string_temp = oarout[begin + len(begin_string):]
        end = string_temp.find(end_string)
        accuracy = string_temp[:end].strip()
        if len(accuracy) < 10:
            return accuracy
    return 'n/a'

def old_way(job_name, job_id, job_list, keywords):
    oarout = os.path.join(OAR_LOG_PATH, job_name, job_id + '_stdout.txt')
    oarerr = os.path.join(OAR_LOG_PATH, job_name, job_id + '_stderr.txt')
    try:
        oarout_list = tail(open(oarout, 'r'), 300)
        oarerr_list = tail(open(oarerr, 'r'), 300)
        oarout_string = ' '.join(oarout_list)
        oarerr_string = ' '.join(oarerr_list)
        stage = parse_stage(oarout_string)
        job_list.append(stage)
        job_list.append(cut_step(stage, oarout_string, oarerr_string))
        for accuracy in keywords[5:]:
            job_list.append(cut_accuracy(accuracy, oarout_string))
    except:
        status = 'W' if 'W {}'.format(LOGIN) in job_name else 'n/a'
        job_list.append('n/a')
        job_list.append(status)
        job_list += ['n/a'] * len(keywords[5:])
    return job_list

def getMachineSummary(machine, keywords):
    try:
        jobs = cmd("ssh -x " + machine + " 'oarstat | grep " + LOGIN + "'")
    except sp.CalledProcessError as e:
        return []

    machine_summary = [list(keywords)]
    for job in sorted(jobs):
        # Monitoring only non interactive jobs
        if (job.split(' ')[-2]).split('J=')[-1] == 'I':
            continue
        # Extracting information and initializing a list for printing
        job_id = job.split(' ')[0]
        job_name = ''
        if len(job.split('N=')) > 1 and len((job.split('N=')[1]).split(' (')) > 0:
            job_name = (job.split('N=')[1]).split(' (')[0]
            if len(job_name.split(',')) > 1:
                job_name = job_name.split(',')[0]
        duration = (job.split(' R=')[0]).split(' ')[-1]
        job_list = [job_name, job_id, duration]
        method_info_path = os.path.join(MODEL_LOG_PATH, job_name, 'method.json')
        if os.path.exists(method_info_path):
            method_info = json.load(open(method_info_path, 'r'))
            stage = str(method_info.get('stage', 'n/a'))
            if 'heatmaps' not in stage:
                job_list.append(stage)
                job_list.append(str(method_info.get('iteration', 'n/a')))
                job_list.append(str(method_info.get('epoch', 'n/a')))
                best_losses = method_info.get('best_losses', {})
                best_losses_str = ''
                for loss_key, loss_value in best_losses.items():
                    best_losses_str += '{0}: {1:.2f}, '.format(loss_key, loss_value)
                job_list.append(best_losses_str)
            else:
                job_list = old_way(job_name, job_id, job_list, keywords)
        else:
            job_list = old_way(job_name, job_id, job_list, keywords)

        machine_summary.append(job_list)
    return machine_summary


class Monitor:
    DOWN = 1
    UP = -1
    ESC_KEY = 27
    KEY_q = 113
    KEY_j = 106
    KEY_k = 107
    KEY_g = 103
    KEY_G = 71
    KEY_u = 117

    outputLines = []
    screen = None

    def __init__(self):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)
        self.screen.border(0)
        self.topLineNum = 0
        self.lastSummariesUpdate = 0
        self.getOutputLines()
        self.run()

    def run(self):
        force_update = True
        while True:
            self.displayScreen(force_update)
            # get user command
            c = self.screen.getch()
            force_update = (c == self.KEY_u)
            if c == curses.KEY_UP or c == self.KEY_k:
                self.updown(self.UP)
            elif c == curses.KEY_DOWN or c == self.KEY_j:
                self.updown(self.DOWN)
            elif c == self.ESC_KEY or c == self.KEY_q:
                self.exit()

    def getOutputLines(self, force_update=False):
        if time.time() - self.lastSummariesUpdate < 30 and not force_update:
            return

        machines = [GPU_MACHINE, CPU_MACHINE]
        all_summaries = {machine: [] for machine in machines}
        keywords = ['job_name', 'job_id', 'time', 'stage', 'itr', 'epoch', 'info']
        for machine in machines:
            all_summaries[machine] = getMachineSummary(machine, keywords)

        for machine in machines:
            if len(all_summaries[machine]) > 0:
                jobs_machine_sorted = [all_summaries[machine][0]] + sorted(all_summaries[machine][1:])
                all_summaries[machine] = jobs_machine_sorted

        self.outputLines = ['Monitoring...']
        for machine, machine_summaries in all_summaries.items():
            self.outputLines.append('### ' + machine + ' ###')
            if len(machine_summaries) > 0:
                # first create a template for all the jobs
                lengths = []
                template_length = len(machine_summaries[0])
                for i in range(template_length):
                    lengths.append(min(max([len(x[i]) for x in machine_summaries]), MAX_LENGTH))
                template = ""
                for i in range(template_length):
                    template += "{%i:%i}" % (i, lengths[i])
                    if i != template_length - 1:
                        template += ' | '

                # cut long jobs entries if needed
                for job_summary in machine_summaries:
                    for i in range(len(job_summary)):
                        if len(job_summary[i]) > MAX_LENGTH:
                            job_summary[i] = job_summary[i][-MAX_LENGTH:]

                for job_summary in machine_summaries:
                    self.outputLines.append(template.format(*job_summary))
            else:
                self.outputLines += ['No jobs running', '\n']
        self.nOutputLines = len(self.outputLines)
        self.lastSummariesUpdate = time.time()
        # TODO: check
        if self.topLineNum > self.nOutputLines:
            self.topLineNum = self.nOutputLines // curses.LINES * curses.LINES

    def displayScreen(self, force_update):
        # clear screen
        self.screen.erase()
        self.getOutputLines(force_update)

        # now paint the rows
        top = self.topLineNum
        bottom = self.topLineNum+curses.LINES
        for (index,line,) in enumerate(self.outputLines[top:bottom]):
            linenum = self.topLineNum + index
            self.screen.addstr(index, 0, line)
        self.screen.refresh()

    # move highlight up/down one line
    def updown(self, increment):
        newTopLineNum = self.topLineNum + increment * curses.LINES
        newTopLineNum = max(0, newTopLineNum)
        newTopLineNum = min(self.nOutputLines - 1, newTopLineNum)
        if newTopLineNum % curses.LINES == 0:
            self.topLineNum = newTopLineNum

    def restoreScreen(self):
        curses.initscr()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    # catch any weird termination situations
    def __del__(self):
        self.restoreScreen()


if __name__ == '__main__':
    monitor = Monitor()
