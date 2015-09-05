#!/usr/bin/env python

# default options; feel free to change!
defaultCompiler = "pdflatex"
defaultArguments = "-synctex=1 -interaction=nonstopmode"
defaultSpeechSetting = "never"

#
# texliveonfly.py (formerly lualatexonfly.py) - "Downloading on the fly"
#     (similar to miktex) for texlive.
#
# Given a .tex file, runs lualatex (by default) repeatedly, using error messages
#     to install missing packages.
#
#
# Version 1.10 ; October 3, 2011
#
# Written on Ubuntu 10.04 with TexLive 2011
# Python 2.6+ or 3
# Should work on Linux and OS X
#
# Copyright (C) 2011 Saitulaa Naranong
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/copyleft/gpl.html>.

import re, subprocess, os, time,  optparse, sys, shlex

scriptName = os.path.basename(__file__)     #the name of this script file
py3 = sys.version_info[0]  >= 3

#functions to support python3's usage of bytes in some places where 2 uses strings
tobytesifpy3 = lambda s = None  : s.encode() if py3 and s != None else s
frombytesifpy3 = lambda b = None : b.decode("UTF-8") if py3 and b != None else b

#version of Popen.communicate that always takes and returns strings
#regardless of py version
def communicateStr ( process,  s = None ):
    (a,b) = process.communicate( tobytesifpy3(s) )
    return ( frombytesifpy3(a), frombytesifpy3(b) )

subprocess.Popen.communicateStr = communicateStr

class Sudoer(object):
    def __init__(self, thisTerminalOnly = False,  tempDirectory = os.path.join(os.getenv("HOME"), ".texliveonfly") ):
        self._tempDirectory = tempDirectory
        self._lockfilePath = os.path.join(self._tempDirectory,  "newterminal_lock")
        self._this_terminal_only = thisTerminalOnly

    #NOTE: double-escaping \\ is neccessary for a slash to appear in the bash command
    # in particular, double quotations in the command need to be written \\"
    def spawnInNewTerminal(self,  bashCommand):
        #makes sure the temp directory exists
        try:
            os.mkdir(self._tempDirectory)
        except OSError:
            print(scriptName + ": Our temp directory " + self._tempDirectory +  " already exists; good.")

        #creates lock file
        lockfile = open(self._lockfilePath, 'w')
        lockfile.write( "Terminal privilege escalator running.")
        lockfile.close()

        #adds intro and line to remove lock
        bashCommand = '''echo \\"The graphical privilege escalator failed for some reason; we'll try asking for your administrator password here instead.\\n{0}\\n\\";{1}; rm \\"{2}\\"'''.format("-"*18,  bashCommand, self._lockfilePath)

        #runs the bash command in a new terminal
        try:
            subprocess.Popen ( ['x-terminal-emulator', '-e',  'sh -c "{0}"'.format(bashCommand) ]  )
        except OSError:
            try:
                subprocess.Popen ( ['xterm', '-e',  'sh -c "{0}"'.format(bashCommand) ]  )
            except OSError:
                os.remove(self._lockfilePath)
                raise

        #doesn't let us proceed until the lock file has been removed by the bash command
        while os.path.exists(self._lockfilePath):
            time.sleep(0.1)

    def runSudoCommand(self, bashCommand):
        if self._this_terminal_only:
            process = subprocess.Popen( ['sudo'] + shlex.split(bashCommand) )
            process.wait()
        elif os.name == "mac":
            process = subprocess.Popen(['osascript'], stdin=subprocess.PIPE )
            process.communicateStr( '''do shell script "{0}" with administrator privileges'''.format(bashCommand) )
        else:
            #raises OSError if neither exist
            try:
                process = subprocess.Popen( ['gksudo', bashCommand] )
            except OSError:
                process = subprocess.Popen( ['kdesudo', bashCommand] )

            process.wait()

    # First tries one-liner graphical/terminal sudo, then opens extended command in new terminal
    # raises OSError if both do
    def attemptSudo(self, oneLiner, newTerminalCommand):
        try:
            self.runSudoCommand(oneLiner)
        except OSError:
            if self._this_terminal_only:
                print("The sudo command has failed and we can't launch any more terminals.")
                raise
            else:
                print("Default graphical priviledge escalator has failed for some reason.")
                print("A new terminal will open and you may be prompted for your sudo password.")
                self.spawnInNewTerminal(newTerminalCommand)

class TLPackageManager(Sudoer):
    #raises OSError if tlmgr_name is bad
    def __init__(self, tlmgr_name, thisTerminalOnly = False, speechSetting = "",  tempDirectory = None ):
        self.tlmgr = tlmgr_name
        self._installation_initialized = False   #have we checked for updates yet?
        self._search_performed = False       #have we tried to search yet?

        #checks that tlmgr is installed, raises OSError otherwise
        #also checks whether we need to escalate permissions, using fake remove command
        process = subprocess.Popen( [ self.tlmgr,  "remove" ], stdin=subprocess.PIPE, stdout = subprocess.PIPE,  stderr=subprocess.PIPE  )
        (tlmgr_out,  tlmgr_err) = process.communicateStr()

        #does our default user have update permissions?
        self._default_permission = "don't have permission" not in tlmgr_err

        if tempDirectory == None:
            Sudoer.__init__(self, thisTerminalOnly)
        else:
            Sudoer.__init__(self, thisTerminalOnly,  tempDirectory)

        self._speech_setting = speechSetting.lower()
        if self._speech_setting != "" and "never" not in self._speech_setting: #user entered nonempty value
            try:
                if os.name == "mac":
                    self.speaker = subprocess.Popen(['say'], stdin=subprocess.PIPE )
                else:
                    self.speaker = subprocess.Popen(['espeak'], stdin=subprocess.PIPE )
            except:
                self.speaker = None

    #always call on first update; updates tlmgr and checks permissions
    def initializeInstallation(self):
        if not self._installation_initialized:
            self._installation_initialized = True
            updateInfo = "Updating tlmgr prior to installing packages\n(this is necessary to avoid complaints from itself)."
            print( scriptName + ": " + updateInfo)

            if self._default_permission:
                process = subprocess.Popen( [ self.tlmgr,  "update",  "--self" ] )
                process.wait()
            else:
                print( "\n{0}: Default user doesn't have permission to modify the TeX Live distribution; upgrading to superuser for all future tasks.\n".format(scriptName) )
                basicCommand = ''''{0}' update --self'''.format(self.tlmgr)
                self.attemptSudo( basicCommand, '''echo \\"This is {0}'s 'install packages on the fly' feature.\\n\\n{1}\\n\\" ; sudo {2}'''.format(scriptName, updateInfo, basicCommand ) )

    #strictmatch requires an entire /file match in the search results
    def getSearchResults(self,  preamble, term, strictMatch):
        self._search_performed = True
        fontOrFile =  "font" if "font" in preamble else "file"
        self.speak("Searching for missing {0}: {1} ".format(fontOrFile, term))
        print( "{0}: Searching repositories for missing {1} {2}".format(scriptName, fontOrFile,  term) )

        process = subprocess.Popen([ self.tlmgr, "search", "--global", "--file", term], stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE )
        ( output ,  stderrdata ) = process.communicateStr()
        outList = output.split("\n")

        results = ["latex"]    #latex 'result' for removal later

        for line in outList:
            line = line.strip()
            if line.startswith(preamble) and (not strictMatch or line.endswith("/" + term)):
                #filters out the package in:
                #   texmf-dist/.../package/file
                #and adds it to packages
                results.append(line.split("/")[-2].strip())
                results.append(line.split("/")[-3].strip()) #occasionally the package is one more slash before

        results = list(set(results))    #removes duplicates
        results.remove("latex")     #removes most common fake result

        if len(results) == 0:
            self.speak("File not found.")
            print("{0}: No results found for {1}".format( scriptName,  term ) )
        else:
            self.speak("Installing.")

        return results

    def searchFilePackage(self,  file):
        return self.getSearchResults("texmf-dist/", file, True)

    def searchFontPackage(self,  font):
        font = re.sub(r"\((.*)\)", "", font)    #gets rid of parentheses
        results = self.getSearchResults("texmf-dist/fonts/", font , False)

        #allow for possibility of lowercase
        if len(results) == 0:
            return [] if font.islower() else self.searchFontPackage(font.lower())
        else:
            return results

    def installPackages(self,  packages):
        if len(packages) == 0:
            return

        self.initializeInstallation()

        packagesString = " ".join(packages)
        print("{0}: Attempting to install LaTex package(s): {1}".format( scriptName,  packagesString ) )

        if self._default_permission:
            process = subprocess.Popen( [ self.tlmgr,  "install"] + packages , stdin=subprocess.PIPE )
            process.wait()
        else:
            basicCommand = ''''{0}' install {1}'''.format(self.tlmgr,  packagesString)
            bashCommand='''echo \\"This is {0}'s 'install packages on the fly' feature.\\n\\nAttempting to install LaTeX package(s): {1} \\"
echo \\"(Some of them might not be real.)\\n\\"
sudo {2}'''.format(scriptName, packagesString, basicCommand)

            self.attemptSudo(basicCommand, bashCommand)

    def searchAndInstall(self,  searcher,  entry):
        self.installPackages(searcher(entry))

    def speak(self, expression, failure = False):
        if  "never" in self._speech_setting or  "always" not in self._speech_setting and not \
        ("install" in self._speech_setting and self._search_performed) and not (failure and "fail" in self._speech_setting ):
            return

        if not expression.endswith("\n"):
            expression += "\n"

        try:
            self.speaker.stdin.write(tobytesifpy3(expression))
            self.speaker.stdin.flush()
        except: #very tolerant of errors here, including self.speaker being None or not being declared
            print("An error has occurred when using the speech synthesizer.")

def readFromProcess(process):
    getProcessLine = lambda : frombytesifpy3(process.stdout.readline())

    output = ""
    line = getProcessLine()
    while line != '':
        output += line
        sys.stdout.write(line)
        line = getProcessLine()

    returnCode = None
    while returnCode == None:
        returnCode = process.poll()

    return (output, returnCode)

def compileTex(compiler, arguments, texDoc):
    try:
        process = subprocess.Popen( [compiler] + shlex.split(arguments) + [texDoc], stdin=sys.stdin, stdout = subprocess.PIPE )
        return readFromProcess(process)
    except OSError:
        print( "{0}: Unable to start {1}; are you sure it is installed?{2}".format(scriptName, compiler,
            "  \n\n(Or run " + scriptName + " --help for info on how to choose a different compiler.)" if compiler == defaultCompiler else "" )
            )
        exitScript(1)

def exitScript(code = 0,  speaker = None):
    if speaker != None:
        speaker("Compilation{0}successful.".format(", un" if code != 0 else " "),  failure = code != 0 )

    sys.exit(code)

### MAIN PROGRAM ###

if __name__ == '__main__':
    # Parse command line
    parser = optparse.OptionParser(
        usage="\n\n\t%prog [options] file.tex\n\nUse option --help for more info.",
        description = 'This program downloads TeX Live packages "on the fly" while compiling .tex documents.  ' +
            'Some of its default options can be directly changed in {0}.  For example, the default compiler can be edited on line 4.'.format(scriptName) ,
        version='1.10',
        epilog = 'Copyright (C) 2011 Saitulaa Naranong.  This program comes with ABSOLUTELY NO WARRANTY; see the GNU General Public License v3 for more info.' ,
        conflict_handler='resolve'
    )

    parser.add_option('-h', '--help', action='help', help='print this help text and exit')
    parser.add_option('-c', '--compiler', dest='compiler', metavar='COMPILER',
        help='your LaTeX compiler; defaults to {0}'.format(defaultCompiler), default=defaultCompiler)
    parser.add_option('-a', '--arguments', dest='arguments', metavar='ARGS',
        help='arguments to pass to compiler; default is: "{0}"'.format(defaultArguments) , default=defaultArguments)
    parser.add_option('--texlive_bin', dest='texlive_bin', metavar='LOCATION',
        help='Custom location for the TeX Live bin folder', default="")
    parser.add_option('--terminal_only', action = "store_true" , dest='terminal_only', default=False,
        help="Forces us to assume we can run only in this terminal.  Permission escalators will appear here rather than graphically or in a new terminal.")
    parser.add_option('-s',  '--speech_when' , dest='speech_setting', metavar="OPTION",  default=defaultSpeechSetting ,
        help='Toggles speech-synthesized notifications (where supported).  OPTION can be "always", "never", "installing", "failed", or some combination.')
    parser.add_option('-f', '--fail_silently', action = "store_true" , dest='fail_silently',
        help="If tlmgr cannot be found, compile document anyway.", default=False)

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.error( "{0}: You must specify a .tex file to compile.".format(scriptName) )

    texDoc = args[0]

    #initializes tlmgr, responds if the program not found
    try:
        tlmgr_path = os.path.join(options.texlive_bin, "tlmgr")
        tlmgr = TLPackageManager( tlmgr_path ,  options.terminal_only, options.speech_setting )
    except OSError:
        if options.fail_silently:
            (output, returnCode)  = compileTex( os.path.join( options.texlive_bin, options.compiler), options.arguments, texDoc)
            exitScript(returnCode)
        else:
            parser.error( "{0}: It appears {1} is not installed.  {2}".format(scriptName, tlmgr_path,
                "Are you sure you have TeX Live 2010 or later?" if tlmgr_path == "tlmgr" else "" ) )

    #loop constraints
    done = False
    previousFile = ""
    previousFontFile = ""
    previousFont =""

    #keeps running until all missing font/file errors are gone, or the same ones persist in all categories
    while not done:
        (output, returnCode)  = compileTex( os.path.join( options.texlive_bin, options.compiler), options.arguments, texDoc)

        #most reliable: searches for missing file
        filesSearch = re.findall(r"! LaTeX Error: File `([^`']*)' not found" , output) + re.findall(r"! I can't find file `([^`']*)'." , output)
        filesSearch = [ name for name in filesSearch if name != texDoc ]  #strips our .tex doc from list of files
        #next most reliable: infers filename from font error
        fontsFileSearch = [ name + ".tfm" for name in re.findall(r"! Font \\[^=]*=([^\s]*)\s", output) ]
        #brute force search for font name in files
        fontsSearch =  re.findall(r"! Font [^\n]*file\:([^\:\n]*)\:", output) + re.findall(r"! Font \\[^/]*/([^/]*)/", output)

        try:
            if len(filesSearch) > 0 and filesSearch[0] != previousFile:
                tlmgr.searchAndInstall(tlmgr.searchFilePackage,filesSearch[0] )
                previousFile = filesSearch[0]
            elif len(fontsFileSearch) > 0 and fontsFileSearch[0] != previousFontFile:
                tlmgr.searchAndInstall(tlmgr.searchFilePackage,fontsFileSearch[0])
                previousFontFile = fontsFileSearch[0]
            elif len(fontsSearch) > 0 and fontsSearch[0] != previousFont:
                tlmgr.searchAndInstall(tlmgr.searchFontPackage,fontsSearch[0])
                previousFont = fontsSearch[0]
            else:
                done = True
        except OSError:
            print("\n{0}: Unable to update; all privilege escalation attempts have failed!".format(scriptName) )
            print("We've already compiled the .tex document, so there's nothing else to do.\n  Exiting..")
            exitScript(returnCode,  tlmgr.speak)

    exitScript(returnCode, tlmgr.speak)
