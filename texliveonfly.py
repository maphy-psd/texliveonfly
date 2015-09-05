#!/usr/bin/env python

# texliveonfly.py (formerly lualatexonfly.py) - "Downloading on the fly"
#     (similar to miktex) for texlive.
#
# Given a .tex file, runs lualatex (by default) repeatedly, using error messages
#     to install missing packages.
#
#
# September 27, 2011 Release
#
# Written on Ubuntu 10.04 with TexLive 2011
# Python 2.6+ or 3 (might work on low as 2.4)
# Other systems may have not been tested.
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
tobytesifpy3 = lambda s : s.encode() if py3 else s
frombytesifpy3 = lambda b : b.decode("UTF-8") if py3 else b

#sets up temp directory and paths
tempDirectory =  os.path.join(os.getenv("HOME"), ".texliveonfly")
lockfilePath = os.path.join(tempDirectory,  "newterminal_lock")

#makes sure the temp directory exists
try:
    os.mkdir(tempDirectory)
except OSError:
    print(scriptName + ": Our temp directory " + tempDirectory +  " already exists; good.")

checkedForUpdates = False   #have we checked for updates yet?

#NOTE: double-escaping \\ is neccessary for a slash to appear in the bash command
# in particular, double quotations in the command need to be written \\"
#NOTE: This function assumes it's only called after doc is compiled; otherwise remove sys.exit
def spawnInNewTerminal(bashCommand):
    #creates lock file
    lockfile = open(lockfilePath, 'w')
    lockfile.write( scriptName + " currently performing task in separate terminal.")
    lockfile.close()

    #adds intro and line to remove lock
    bashCommand = '''echo \\"This is {0}'s 'install packages on the fly' feature.\\n{1}\\n\\";{2}; rm \\"{3}\\"'''.format(scriptName, "-"*18,  bashCommand, lockfilePath)

    #runs the bash command in a new terminal
    try:
        if os.name == "mac":
            #possible OS X bash implementation (needs testing)
            process = subprocess.Popen(['osascript'], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate( tobytesifpy3( '''tell application "Terminal"\nactivate\ndo script with command "{0} ; exit"\nend tell'''.format(bashCommand) ) )
            process.wait()
        else:
            process = subprocess.Popen ( ['x-terminal-emulator', '-e',  'sh -c "{0}"'.format(bashCommand) ]  )
            process.wait()
    except OSError:
        print("\n{0}: Unable to update because we can't spawn new terminal:\n  {1}".format(scriptName,
            "osascript does not seem to be working!" if os.name == "mac" else "there is no x-terminal-emulator!" ) )
        print("We've already compiled the .tex document, so there's nothing else to do.\n  Exiting..")
        os.remove(lockfilePath)
        sys.exit(returnCode)

    #doesn't let us proceed until the lock file has been removed by the bash command
    while os.path.exists(lockfilePath):
        time.sleep(0.1)

def updateTLMGR():
    global checkedForUpdates
    if not checkedForUpdates:
        spawnInNewTerminal('''echo \\"Updating tlmgr prior to installing packages\n(this is necessary to avoid complaints from itself).\\n\\" ; sudo tlmgr update --self''')
        checkedForUpdates = True

#strictmatch requires an entire /file match in the search results
def getSearchResults(preamble, term, strictMatch):
    print( "{0}: Searching repositories for missing {1} {2}".format(scriptName, "font" if "font" in preamble else "file",  term) )

    process = subprocess.Popen(["tlmgr", "search", "--global", "--file", term], stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE )
    ( output ,  stderrdata ) = process.communicate()
    outList = frombytesifpy3(output).split("\n")

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
        print("No results found for " + term)

    return results

def getFilePackage(file):
    return " ".join( getSearchResults("texmf-dist/", file, True) )

def getFontPackage(font):
    font = re.sub(r"\((.*)\)", "", font)    #gets rid of parentheses
    results = getSearchResults("texmf-dist/fonts/", font , False)

    #allow for possibility of lowercase
    if len(results) == 0:
        return "" if font.islower() else getFontPackage(font.lower())
    else:
        return " ".join(results)

#string can contain more than one package
def installPackages(packagesString):
    if packagesString.strip() == "":
        return

    #New terminal is required: we're not guaranteed user can input sudo password into editor
    print("Attempting to install LaTex package(s): " + packagesString )
    print("A new terminal will open and you may be prompted for your sudo password.")

    updateTLMGR()  #avoids complaints about tlmgr not being updated

    #bash command to download
    bashCommand='''echo \\"Attempting to install LaTeX package(s): {0} \\"
echo \\"(Some of them might not be real.)\\n\\"
sudo tlmgr install {0}'''.format(packagesString)

    spawnInNewTerminal(bashCommand)

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
        sys.exit(1)

### MAIN PROGRAM ###
licenseinfo = """texliveonfly.py Copyright (C) 2011 Saitulaa Naranong
This program comes with ABSOLUTELY NO WARRANTY;
See the GNU General Public License v3 for more info."""

defaultArgs = "-synctex=1 -interaction=nonstopmode"
defaultCompiler = "lualatex"

if __name__ == '__main__':
    # Parse command line
    parser = optparse.OptionParser(
        usage="\n\n\t%prog [options] file.tex\n\nUse option --help for more info.\n\n" + licenseinfo ,
        version='2011.27.9',
        conflict_handler='resolve'
    )

    parser.add_option('-h', '--help', action='help', help='print this help text and exit')
    parser.add_option('-c', '--compiler', dest='compiler', metavar='COMPILER',
        help='your LaTeX compiler; defaults to {0}'.format(defaultCompiler), default=defaultCompiler)
    parser.add_option('-a', '--arguments', dest='arguments', metavar='ARGS',
        help='arguments to pass to compiler; default is: "{0}"'.format(defaultArgs) , default=defaultArgs)
    parser.add_option('-f', '--fail_silently', action = "store_true" , dest='fail_silently',
        help="If tlmgr cannot be found, compile document anyway.", default=False)

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.error( "{0}: You must specify a .tex file to compile.".format(scriptName) )

    texDoc = args[0]

    #checks that tlmgr is installed, responds based on --fail_silently flag
    try:
        process = subprocess.Popen( ["tlmgr"] , stdout = subprocess.PIPE,  stderr=subprocess.PIPE )
    except OSError:
        if options.fail_silently:
            (output, returnCode)  = compileTex(options.compiler, options.arguments, texDoc)
            sys.exit(returnCode)
        else:
            parser.error( "{0}: It appears tlmgr is not installed.  Are you sure you have TeX Live 2010 or later?".format(scriptName) )

    #loop constraints
    done = False
    previousFile = ""
    previousFontFile = ""
    previousFont =""

    #keeps running until all missing font/file errors are gone, or the same ones persist in all categories
    while not done:
        (output, returnCode)  = compileTex(options.compiler, options.arguments, texDoc)

        #most reliable: searches for missing file
        filesSearch = re.findall(r"! LaTeX Error: File `([^`']*)' not found" , output) + re.findall(r"! I can't find file `([^`']*)'." , output)
        filesSearch = [ name for name in filesSearch if name != texDoc ]  #strips our .tex doc from list of files
        #next most reliable: infers filename from font error
        fontsFileSearch = [ name + ".tfm" for name in re.findall(r"! Font \\[^=]*=([^\s]*)\s", output) ]
        #brute force search for font name in files
        fontsSearch =  re.findall(r"! Font [^\n]*file\:([^\:\n]*)\:", output) + re.findall(r"! Font \\[^/]*/([^/]*)/", output)

        if len(filesSearch) > 0 and filesSearch[0] != previousFile:
            installPackages(getFilePackage(filesSearch[0]))
            previousFile = filesSearch[0]
        elif len(fontsFileSearch) > 0 and fontsFileSearch[0] != previousFontFile:
            installPackages(getFilePackage(fontsFileSearch[0]))
            previousFontFile = fontsFileSearch[0]
        elif len(fontsSearch) > 0 and fontsSearch[0] != previousFont:
            installPackages(getFontPackage(fontsSearch[0]))
            previousFont = fontsSearch[0]
        else:
            done = True

    sys.exit(returnCode)