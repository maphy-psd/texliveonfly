# texliveonfly
Script to download TeX Live Packages "on the fly"

Original written by Saitulaa Naranong 

Download of the last version by Saitulaa Naranong [v1.2](https://github.com/maphy-psd/texliveonfly/archive/v1.20.zip)

##### From the original thread http://latex-community.org/forum/viewtopic.php?f=12&t=15194

From reading the forums and groups, I gather that a lot of us miss the "download on the fly" feature offered by MiKTeX. I've written a script that should allow us to do just that. Make sure you have python (most OS X and linux distributions provide it by default; if not, you can get either the 2 or 3 version from here), then run the command

`texliveonfly.py [options] file.tex`

or, for python 3,

`python3 texliveonfly.py [options] file.tex`

instead of "lualatex" or "pdflatex".

The current options are:
```
Options:
  --version             show program version number and exit
  -h, --help            print this help text and exit
  -c COMPILER, --compiler=COMPILER
                        your LaTeX compiler; defaults to pdflatex
  -a ARGS, --arguments=ARGS
                        arguments to pass to compiler; default is: "-synctex=1
                        -interaction=nonstopmode"
  --texlive_bin=LOCATION
                        Custom location for the TeX Live bin folder
  --terminal_only       Forces us to assume we can run only in this terminal.
                        Permission escalators will appear here rather than
                        graphically or in a new terminal.
  -s OPTION, --speech_when=OPTION
                        Toggles speech-synthesized notifications (where
                        supported).  OPTION can be "always", "never",
                        "installing", "failed", or some combination.
  -f, --fail_silently   If tlmgr cannot be found, compile document anyway.
```
Setting this command within your favourite editor will allow you to download packages on the fly. The script defaults to PdfLaTeX with arguments '-synctex=1 -interaction=nonstopmode'.

As of the Sep 27 version, the script should be compatible with either python 2 or 3. It depends strongly on the TeX Live Package Manager (tlmgr), so please make sure you are using at least TeX Live 2010. It should resolve all missing included packages and a fair number of missing fonts. It was written on Ubuntu 10.04 and should work on all Linux systems; the Sep 26th version should also work on OS X (but hasn't been tested as of this posting).

Any comments, suggestions, or bug reports are appreciated, and I hope you enjoy.

[ Updates/Changelog](https://github.com/maphy-psd/texliveonfly/releases)
