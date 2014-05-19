psm
===

Python SLURM Manager

Installing
----------
* make sure psm.py is in your $PATH
* copy psm_config.py.template to psm_config.py in your project directory
* edit psm_config.py (especially your default partition)
* create ~/.psm/outputs (or whatever path you specified in your psm_config.py)

Running
-------
* run psm in your project directory
* If you use the default configuration, PSM will save job definitions in your project directory and your joblist globally in your user directory.

User Interface
--------------

### Left Pane
The left Pane shows a list of all jobs.

#### Buttons
* enable automatic refresh
* delete current item
* clear all finished/cancelled jobs
* cancel current job

### Middle Pane
The middle pane shows a list of all defined jobs.

#### Buttons
* execute current job definition
* create/edit/delete job (opens job definition window)

### Right pane
The right pane shows the output of the currently (left pane) selected job.

### Job definition window
This window has four fields (from top to bottom):
#### Job name
This name will be shown in lists in PSM and as title in slurm. Names must be unique.
#### Commands
List of commands to execute. Use python format-style placeholders for parameters, e.g.

    sleep {0}
    sleep {1}

#### Per-instance parameters
List of parameters given to each instance. These parameters are formatted into the command template. Separate multiple instances with linebreaks and multiple parameters with `,`, e.g.

    1,1
    1,10
    10,10

#### Global parameters
Global parameters are passed to SLURM to request e.g. additional memory or a certain number of CPUs. Separate multiple options with linebreaks and key/value pairs with `=`, e.g.

    mem-per-cpu=5000
    num-tasks=2

For a list of possible options, refer to the SLURM manual.

License
-------
This code is released under the MIT License (see LICENSE file for more information).
