"""Bounded subprocess boundary. No shell evaluation, logs retained on failure."""
from pathlib import Path
import subprocess

def run_logged(command,logfile,timeout):
    logfile=Path(logfile)
    try:
        with logfile.open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Blender timed out; see '+str(logfile)) from exc
    if result.returncode:raise RuntimeError('Blender failed '+str(result.returncode)+'; see '+str(logfile))
    return result.returncode
