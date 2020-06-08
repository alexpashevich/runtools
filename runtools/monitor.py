#!/usr/bin/env python

import curses
import os
import time
import json

import subprocess as sp

from runtools.utils.python import cmd
from runtools.settings import LOGIN, CPU_MACHINE, GPU_MACHINE, OAR_LOG_PATH, MODEL_LOG_PATH

# from rlons.utils import losses

MAX_LENGTH = 80


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
        info_path = os.path.join(MODEL_LOG_PATH, job_name, 'info.json')
        if not os.path.exists(info_path):
            info_path = info_path.replace(MODEL_LOG_PATH, os.environ['ALFRED_DATA'])
        if os.path.exists(info_path):
            info = json.load(open(info_path, 'r'))[-1]
            stage = str(info['stage'])
            job_list.append(stage)
            progress = info.get('progress', -1)
            total = info.get('total', -1)
            job_list.append('{}/{}'.format(progress, total))
        else:
            job_list.extend(['n/a'] * (len(keywords) - len(job_list)))
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
        keywords = ['job_name', 'job_id', 'time', 'stage', 'done']
        for machine in machines:
            all_summaries[machine] = getMachineSummary(machine, keywords)

        for machine in machines:
            if len(all_summaries[machine]) > 0:
                jobs_machine_sorted = [all_summaries[machine][0]] + sorted(all_summaries[machine][1:])
                all_summaries[machine] = jobs_machine_sorted

        self.outputLines = []
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
