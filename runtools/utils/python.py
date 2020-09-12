import subprocess


# Call bash function from python
def cmd(command, print_command=False):
    if print_command:
        print(command)
    else:
        out = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
        if isinstance(out, bytes):
            out = out.decode("utf-8")
        return out.split('\n')[:-1]
