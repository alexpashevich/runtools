import os, sys
from random import randint
from pytools.tools import cmd
from settings import EMAIL, SCRIPT_DIRNAME, OARSUB_DIRNAME, CODE_DIRNAME


class JobMeta(object):
    def __init__(self, run_argv):
        self.run_argv = run_argv
        # Organization settings
        self.job_name = None
        self.oarstat_check_frequency = 15
        # Job settings
        self.machine_name = None
        self.besteffort = False
        self.priority_level = 1
        self.interpreter = 'python'
        self.global_path_project = None
        self.local_path_exe = None
        self.librairies_to_install = []
        self.previous_jobs = []  # type: list[JobMeta]
        # Internal settings (do not override these field)
        self.job_crashed = False
        self.job_id = None
        self.script_filename_key = None

    def initialization(self):
        # print oarsub command
        print(self.oarsub_command)
        # script generation
        self.generate_script()

    def run(self):
        """
        General pipeline of the run method:
            -If previous jobs have not crashed:
                -A bash script is generated
                -A job is launched to process the bash script we just generated
        """
        # check if previous jobs have crashed or not
        for job in self.previous_jobs:
            if job.job_crashed:
                self.job_crashed = True
                break
        if not self.job_crashed:
            # run a job with oarsub (its job_id is retrieved)
            print(self.oarsub_command)
            self.job_id = cmd(self.oarsub_command)[-1].split('=')[-1]

    def add_previous_job(self, job):
        assert job not in self.previous_jobs
        self.previous_jobs.append(job)

    @property
    def job_ended(self):
        # TODO: this is the place where I will see if a job crashed or not. But this function will be called often
        # the job has crashed thus it has ended
        if self.job_crashed:
            print('job crashed')
            ended = True
        # the job has not been started
        elif self.job_id is None:
            ended = False
        # the job has been launched, we check if it is still running
        else:
            ended = True
            oarstat_lines = cmd("ssh -X -Y " + self.machine_name + " ' oarstat ' ")
            for line in oarstat_lines:
                if self.job_id in line:
                    ended = False
                    break
        return ended

    @property
    def previous_jobs_ended(self):
        ended = True
        for jobs in self.previous_jobs:
            if not jobs.job_ended:
                ended = False
                break
        return ended

    """ Management of the bash script, that are fed to oarsub """

    def generate_script(self):
        """
        Generate an executable bash script containing a list of commands
        :param argv: parameters for the script to run
        """
        # build script_dirname if it has not yet been created
        if not os.path.exists(self.script_dirname):
            os.makedirs(self.script_dirname)
        # create script_filename file
        cmd('touch ' + self.script_filename)
        # building the list of commands for the script
        commands = list()
        # install libraries that have been specified
        for library in self.librairies_to_install:
            commands.append('sudo apt-get install ' + library + ' --yes')
        # # TO IMPROVE
        #  copy the whole project to launch into it from a local directory
        # if not os.path.exists(self.code_dirname):
        #     os.makedirs(self.code_dirname)
        # new_global_path = os.path.join(self.code_dirname, os.path.basename(self.global_path_project))
        # if not os.path.exists(new_global_path):
        #     command_copy_dir = 'cp -r ' + self.global_path_project + ' ' + self.code_dirname
        #     print(command_copy_dir)
        #     cmd(command_copy_dir)
        # new_path_exe = os.path.join(new_global_path, self.local_path_exe)
        path_exe = os.path.join(self.global_path_project, self.local_path_exe)
        # launch the main exe
        if self.interpreter == '':
            command_script = self.interpreter + path_exe
        else:
            command_script = self.interpreter + ' ' + path_exe
        commands.append(' '.join([command_script] + self.run_argv))
        # script file delete itself when finished
        commands.append('rm ' + self.script_filename + '\n')
        # write into the bash script
        with open(self.script_filename, 'w') as f:
            for command in commands:
                f.write('{0} \n'.format(command))
        # give the permission to the bash script to execute
        cmd('chmod +x ' + self.script_filename)

    @property
    def oarsub_dirname(self):
        assert self.job_name is not None
        return os.path.join(OARSUB_DIRNAME, self.job_name)

    @property
    def script_dirname(self):
        assert self.job_name is not None
        return os.path.join(SCRIPT_DIRNAME, self.job_name)

    @property
    def code_dirname(self):
        assert self.job_name is not None
        return os.path.join(CODE_DIRNAME, self.job_name)

    @property
    def get_script_filename(self):
        return os.path.join(self.script_dirname,
                            str(self.script_filename_key) + '.sh')

    @property
    def script_filename(self):
        """
        A script filename must match a single run object
        Therefore each script_filename_nb must be different and have an individual key
        A natural way to define keys would be to iterate
        However, if two jobs with the same job_name create the same key at the time, it would crash
        that's the reason I decided to use a random number to define the key
        :return: a string specifying the path to the bash script
        """
        # TODO: Put the date also in the filename
        if self.script_filename_key is None:
            # initializing the script_filename_key
            self.script_filename_key = 0
            while os.path.exists(self.get_script_filename):
                self.script_filename_key = randint(0, 10000)
        return self.get_script_filename

    """ Management of the oarsub command """

    @property
    def oarsub_command(self):
        # Connect to the appropriate machine
        command = "ssh " + self.machine_name + " ' oarsub "
        # Add the running options for oarsub
        command += self.oarsub_options
        # Naming the job
        command += ' --name="' + self.job_name + '"'
        # Build the oarsub directory
        if not os.path.exists(self.oarsub_dirname):
            os.makedirs(self.oarsub_dirname)
        # Redirecting the stdout and stderr
        stdnames = ['out', 'err']
        stdfiles = [os.path.join(self.oarsub_dirname, '%jobid%_std' + stdname + '.txt') for stdname in stdnames]
        for stdname, stdfile in zip(stdnames, stdfiles):
            command += ' --std' + stdname + '="' + stdfile + '"'
        # Finally add the script to launch
        command += ' "' + self.script_filename + '"'
        command += " '"
        return command

    @property
    def oarsub_options(self):
        options = []
        if self.besteffort:
            options += ' -t besteffort -t idempotent'
        for symbol, supplementary_options in zip(['p', 'l'], [self.oarsub_p_options, self.oarsub_l_options]):
            if supplementary_options:
                for option in supplementary_options:
                    options.append('-' + symbol + ' "' + option + '"')
        return ' '.join(options)

    @property
    def oarsub_p_options(self):
        return []

    @property
    def oarsub_l_options(self):
        return []

    """ Management of the monitoring """

    def job_study(self):
        # Job study
        # check if job ended well (i.e., script should have deleted itself)
        # TODO: check if in  a killed besteffort, that the script is not deleted
        if os.path.exists(self.script_filename):
            # delete the bash script
            cmd('rm ' + self.script_filename)
            # send a report of the crash by mail
            command_mail = 'cat ' + os.path.join(self.oarsub_dirname, self.job_id + '_stderr.txt')
            command_mail += ' | mail -s "Failure report of ' + self.job_name + '" ' + EMAIL
            cmd(command_mail)
            # declare job as crashed to avoid running following jobs
            self.job_crashed = True
        else:
            self.job_done = True
            # final monitoring
            # self.monitoring()
            # TODO Philippe lui copie les fichier OAR a une destination correspond au model que l on a en entraine,
            # TODO proposer surement l empalcement du fichier ou le fichier doit etre copie
            # TODO in the process let the path to the OAR files to come back process them again if needed
            # self.path_exe_parse()
