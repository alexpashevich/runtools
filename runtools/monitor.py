import socket
import curses
import os
import json
import subprocess as sp

from runtools.utils.python import cmd
from runtools.settings import LOGIN, CPU_MACHINE, GPU_MACHINE, OAR_LOG_PATH

MAX_LENGTH = 80


def get_machine_summary(machine, keywords):
    try:
        oarstat_command = 'oarstat | grep {}'.format(LOGIN)
        if socket.gethostname() != machine:
            oarstat_command = "ssh {} '{}'".format(machine, oarstat_command)
        jobs = cmd(oarstat_command)
    except sp.CalledProcessError as e:
        return []

    machine_summary = [list(keywords)]
    for job in sorted(jobs): # Monitoring only non interactive jobs
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
        info_path = os.path.join(os.environ['ALFRED_LOGS'], job_name, 'info.json')
        if not os.path.exists(info_path):
            info_path = os.path.join(os.environ['ALFRED_DATA'], job_name, 'info.json')
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
    # KEY_g = 103
    # KEY_G = 71
    KEY_u = 117

    screen = None

    def __init__(self, update_freq=5):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)
        self.screen.border(0)
        self.screen.timeout(update_freq * 1000) # update shown lines 'update_freq' miliseconds
        self.topLineNum = 0
        self.output_lines = []
        self.update_output_lines()
        self.run()

    def run(self):
        force_update = True
        while True:
            self.displayScreen(update_output_lines=force_update)
            # get user command
            c = self.screen.getch()
            if c == curses.KEY_UP or c == self.KEY_k:
                self.updown(self.UP)
            elif c == curses.KEY_DOWN or c == self.KEY_j:
                self.updown(self.DOWN)
            elif c == self.ESC_KEY or c == self.KEY_q:
                self.exit()
            do_not_update = (c in {self.KEY_q, self.KEY_k, self.KEY_j, self.ESC_KEY, curses.KEY_UP, curses.KEY_DOWN})
            force_update = not do_not_update

    def update_output_lines(self):
        # machines = [GPU_MACHINE, CPU_MACHINE]
        machines = [GPU_MACHINE]
        all_summaries = {machine: [] for machine in machines}
        keywords = ['job_name', 'job_id', 'time', 'stage', 'done']
        for machine in machines:
            all_summaries[machine] = get_machine_summary(machine, keywords)

        for machine in machines:
            if len(all_summaries[machine]) > 0:
                jobs_machine_sorted = [all_summaries[machine][0]] + sorted(all_summaries[machine][1:])
                all_summaries[machine] = jobs_machine_sorted

        self.output_lines = []
        for machine, machine_summaries in all_summaries.items():
            self.output_lines.append('### ' + machine + ' ###')
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
                    self.output_lines.append(template.format(*job_summary))
            else:
                self.output_lines += ['No jobs running', '\n']
        self.nOutputLines = len(self.output_lines)
        if self.topLineNum > self.nOutputLines:
            self.topLineNum = self.nOutputLines // curses.LINES * curses.LINES

    def displayScreen(self, update_output_lines):
        # clear screen
        self.screen.erase()
        if update_output_lines:
            self.update_output_lines()

        # now paint the rows
        top = self.topLineNum
        bottom = self.topLineNum+curses.LINES
        for (index,line,) in enumerate(self.output_lines[top:bottom]):
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
