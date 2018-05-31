#!/usr/bin/env python

"""
Lyle Scott, III
lyle@digitalfoo.net

A simple demo that uses curses to scroll the terminal.
"""
import curses
import os
import sys
import random
import time

import subprocess as sp

from pytools.tools import cmd
from settings import LOGIN, CPU_MACHINE, GPU_MACHINE, OARSUB_DIRNAME

KEYWORDS = []
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

def cut_value(string, keyword):
    try:
        begin = string.find(keyword)
        end = string[begin:].find('\n')
        string_temp = string[begin: begin + end]
        last_space = string_temp.rfind(' ')
        value = string_temp[last_space + 1:]
        if value.find('.') > 0 and value.find('.') + NB_DECIMAL < len(value):
            value = value[:value.find('.') + NB_DECIMAL]
        if len(value) > 15:
            return 'n/a'
        return value
    except:
        return 'n/a'

def cut_step(string):
    try:
        substring = 'global step '
        begin = string.rfind(substring)
        string_temp = string[begin + len(substring):]
        end = string_temp.find(')')
        step = string_temp[:end].strip()
        if len(step) > 15:
            return 'n/a'
        if len(step) > 3:
            step = step[:-3] + 'K'
            if len (step) > 4:
                step = step[:-4] + '.' + step[-4:]
        return step
    except:
        return 'n/a'

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
        # oarout = os.path.join(OARSUB_DIRNAME, job_name, job_id + '_stdout.txt')
        oarout = os.path.join(OARSUB_DIRNAME, job_name, job_id + '_stderr.txt')
        try:
            oarout_list = tail(open(oarout, 'r'), 300)
        except:
            continue

        oarout_string = ' '.join(oarout_list)
        job_list.append(cut_step(oarout_string))
        for keyword in KEYWORDS:
            job_list.append(cut_value(oarout_string, keyword))
            # TODO: fix cutting when a job has just started
        machine_summary.append(job_list)
    return machine_summary

class MenuDemo:
    DOWN = 1
    UP = -1
    ESC_KEY = 27
    KEY_q = 113
    KEY_j = 106
    KEY_k = 107
    KEY_g = 103
    KEY_G = 71

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
        while True:
            self.displayScreen()
            # get user command
            c = self.screen.getch()
            if c == curses.KEY_UP or c == self.KEY_k:
                self.updown(self.UP)
            elif c == curses.KEY_DOWN or c == self.KEY_j:
                self.updown(self.DOWN)
            elif c == self.ESC_KEY or c == self.KEY_q:
                self.exit()

    def getOutputLines(self):
        if time.time() - self.lastSummariesUpdate < 30:
            return

        machines = [GPU_MACHINE, CPU_MACHINE]
        all_summaries = {machine: [] for machine in machines}
        keywords = ['job_name', 'job_id', 'time', 'itr'] + KEYWORDS
        for machine in machines:
            all_summaries[machine] = getMachineSummary(machine, keywords)

        # TODO: refactor
        if len(all_summaries[CPU_MACHINE]) > 0:
            jobs_cpu = [all_summaries[CPU_MACHINE][0]] + sorted(all_summaries[CPU_MACHINE][1:])
            all_summaries[CPU_MACHINE] = jobs_cpu

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

    def displayScreen(self):
        # clear screen
        self.screen.erase()
        self.getOutputLines()

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
    ih = MenuDemo()
    
