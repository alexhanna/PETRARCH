##	PETRreader.py [module]
##
# Dictionary and text input routines for the PETRARCH event coder
##
# CODE REPOSITORY: https://github.com/eventdata/PETRARCH
##
# SYSTEM REQUIREMENTS
# This program has been successfully run under Mac OS 10.6; it is standard Python 2.5
# so it should also run in Unix or Windows.
##
# PROVENANCE:
# Programmer: Philip A. Schrodt
# Parus Analytical Systems
# State College, PA, 16801 U.S.A.
# http://eventdata.parusanalytics.com
##
# Copyright (c) 2014	Philip A. Schrodt.
##
# This project was funded in part by National Science Foundation grant SES-1259190
##
# This code is covered under the MIT license as asserted in the file PETR.coder.py
##
# Report bugs to: schrodt735@gmail.com
##
# REVISION HISTORY:
# 22-Nov-113:	Initial version
# 28-Apr-14:	Latest version
# ------------------------------------------------------------------------

import re
import os
import sys
import math  # required for ordinal date calculations
import xml.etree.ElementTree as ET
from ConfigParser import ConfigParser

import PETRglobals
import PETRwriter   # uses the error reporting functions
import utilities

"""
CONVERTING TABARI DICTIONARIES TO PETRARCH FORMAT

1. The ';' comment delimiter no longer works: replace it with '#"

2. Lines beginning with '#' and '<' are considered comments and are skipped.
   If using '<', make this a one-line XML comment: <!-- ... -->.
   [The system currently doesn't recognize multi-line XML comments but this may
   change in the future.]

3. Final underscores are no longer needed since PETR does not do stemming.

"""


# ================== STRINGS ================== #

ErrMsgMissingDate = "<Sentence> missing required date; record was skipped"


# ================== EXCEPTIONS ================== #

class DateError(Exception):  # invalid date
    pass

# ================== CONFIG FILE INPUT ================== #


def parse_Config(config_path):
    """
    Parse PETRglobals.ConfigFileName. The file should be ; the default is PETR_config.ini
    in the working directory but this can be changed using the -c option in the command
    line. Most of the entries are obvious (but will eventually be documented) with the
    exception of

    1. actorfile_list and textfile_list are comma-delimited lists. Per the usual rules
            for Python config files, these can be continued on the next line provided the
            the first char is a space or tab.

    2. If both textfile_list and textfile_name are present, textfile_list takes priority.
       textfile_list should be the name of a file containing text file names; # is allowed
       as a comment delimiter at the beginning of individual lines and following the file
       name.

    3. For additional info on config files, see
                    http://docs.python.org/3.4/library/configparser.html
       or try Google, but basically, it is fairly simple, and you can probably just
       follow the examples.
    """

    print '\n',
    parser = ConfigParser()
#		logger.info('Found a config file in working directory')
#	print "pc",PETRglobals.ConfigFileName
    confdat = parser.read(config_path)
    if len(confdat) == 0:
        print "\aError: Could not find the config file:", PETRglobals.ConfigFileName
        print "Terminating program"
        sys.exit()

    try:
        PETRglobals.VerbFileName = parser.get('Dictionaries', 'verbfile_name')
        PETRglobals.AgentFileName = parser.get(
            'Dictionaries',
            'agentfile_name')
#		print "pc",PETRglobals.AgentFileName
        PETRglobals.DiscardFileName = parser.get(
            'Dictionaries',
            'discardfile_name')

        direct = parser.get('StanfordNLP', 'stanford_dir')
        PETRglobals.stanfordnlp = os.path.expanduser(direct)

        filestring = parser.get('Dictionaries', 'actorfile_list')
        PETRglobals.ActorFileList = filestring.split(', ')

        # otherwise this was set in command line
        if len(PETRglobals.TextFileList) == 0:
            if parser.has_option('Options', 'textfile_list'):  # takes priority
                filestring = parser.get('Options', 'textfile_list')
                PETRglobals.TextFileList = filestring.split(', ')
            else:
                filename = parser.get('Options', 'textfile_name')
                try:
                    fpar = open(filename, 'r')
                except IOError:
                    print "\aError: Could not find the text file list file:", filename
                    print "Terminating program"
                    sys.exit()
                PETRglobals.TextFileList = []
                line = fpar.readline()
                while len(line) > 0:   # go through the entire file
                    if '#' in line:
                        line = line[:line.find('#')]
                    line = line.strip()
                    if len(line) > 0:
                        PETRglobals.TextFileList.append(line)
                    line = fpar.readline()
                fpar.close()

#		print "pc",PETRglobals.TextFileList

        if parser.has_option('Dictionaries', 'issuefile_name'):
            PETRglobals.IssueFileName = parser.get(
                'Dictionaries',
                'issuefile_name')

        if parser.has_option('Options', 'new_actor_length'):
            try:
                PETRglobals.NewActorLength = parser.getint(
                    'Options',
                    'new_actor_length')
            except ValueError:
                print "Error in config.ini Option: new_actor_length value must be an integer"
                raise
        print "new_actor_length =", PETRglobals.NewActorLength

        if parser.has_option('Options', 'require_dyad'):
            try:
                PETRglobals.RequireDyad = parser.getboolean(
                    'Options',
                    'require_dyad')
            except ValueError:
                print "Error in config.ini: require_dyad value must be `true' or `false'"
                raise
        print "require_dyad =", PETRglobals.RequireDyad

        if parser.has_option('Options', 'stop_on_error'):
            try:
                PETRglobals.StoponError = parser.getboolean(
                    'Options',
                    'stop_on_error')
            except ValueError:
                print "Error in config.ini: stop_on_error value must be `true' or `false'"
                raise
        print "stop_on_error =", PETRglobals.StoponError

        # otherwise this was set in command line
        if len(PETRglobals.EventFileName) == 0:
            PETRglobals.EventFileName = parser.get('Options', 'eventfile_name')

        PETRglobals.CodeBySentence = parser.has_option(
            'Options',
            'code_by_sentence')
        print "code-by-sentence", PETRglobals.CodeBySentence
        PETRglobals.PauseBySentence = parser.has_option(
            'Options',
            'pause_by_sentence')
        print "pause_by_sentence", PETRglobals.PauseBySentence
        PETRglobals.PauseByStory = parser.has_option(
            'Options',
            'pause_by_story')
        print "pause_by_story", PETRglobals.PauseByStory

        try:
            if parser.has_option('Options', 'comma_min'):
                PETRglobals.CommaMin = parser.getint('Options', 'comma_min')
            elif parser.has_option('Options', 'comma_max'):
                PETRglobals.CommaMax = parser.getint('Options', 'comma_max')
            elif parser.has_option('Options', 'comma_bmin'):
                PETRglobals.CommaBMin = parser.getint('Options', 'comma_bmin')
            elif parser.has_option('Options', 'comma_bmax'):
                PETRglobals.CommaBMax = parser.getint('Options', 'comma_bmax')
            elif parser.has_option('Options', 'comma_emin'):
                PETRglobals.CommaEMin = parser.getint('Options', 'comma_emin')
            elif parser.has_option('Options', 'comma_emax'):
                PETRglobals.CommaEMax = parser.getint('Options', 'comma_emax')
        except ValueError:
            print "Error in config.ini Option: comma_*  value must be an integer"
            raise
        print "Comma-delimited clause elimination:"
        print "Initial :",
        if PETRglobals.CommaBMax == 0:
            print "deactivated"
        else:
            print "min =", PETRglobals.CommaBMin, "   max =", PETRglobals.CommaBMax
        print "Internal:",
        if PETRglobals.CommaMax == 0:
            print "deactivated"
        else:
            print "min =", PETRglobals.CommaMin, "   max =", PETRglobals.CommaMax
        print "Terminal:",
        if PETRglobals.CommaEMax == 0:
            print "deactivated"
        else:
            print "min =", PETRglobals.CommaEMin, "   max =", PETRglobals.CommaEMax

    except Exception as e:
        print 'parse_config() encountered an error: check the options in', PETRglobals.ConfigFileName
        print "Terminating program"
        sys.exit()
#		logger.warning('Problem parsing config file. {}'.format(e))


# ================== PRIMARY INPUT USING FIN ================== #


def open_FIN(filename, descrstr):
# opens the global input stream fin using filename;
# descrstr provides information about the file in the event it isn't found
    global FIN
    global FINline, FINnline, CurrentFINname
    try:
        FIN = open(filename, 'r')
        CurrentFINname = filename
        FINnline = 0
    except IOError:
        print "\aError: Could not find the", descrstr, "file:", filename
        print "Terminating program"
        sys.exit()


def close_FIN():
# closes the global input stream fin.
# IOError should only happen during debugging or if something has seriously gone wrong
# with the system, so exit if this occurs.
    global FIN
    try:
        FIN.close()
    except IOError:
        print "\aError: Could not close the input file"
        print "Terminating program"
        sys.exit()


def read_FIN_line():
    """
    def read_FIN_line():
    Reads a line from the input stream fin, deleting xml comments and lines beginning with #
    returns next non-empty line or EOF
    tracks the current line number (FINnline) and content (FINline)
    calling function needs to handle EOF (len(line) == 0)
    """
    """
	Comments in input files:
	Comments should be delineated in the XML style (which is inherited from HTML which
	inherited it from SGML) are allowed, as long as you don't get too clever. Basically,
	anything that looks like any of these

		<!-- [comment] -->

		things I want to actually read <!-- [comment] -->

		some things I want <!-- [comment] --> and more of them

		<!-- start of the comment
		 [1 or more additional lines
	  	end of the comment -->

	is treated like a comment and skipped.

	Note: the system doesn't use the formal definition that also says '--' is not allowed
	inside a comment: it just looks for --> as a terminator

	The system is *not* set up to handle clever variations like nested comments,  multiple
	comments on a line, or non-comment information in multi-line comments: yes, we are
	perfectly capable of writing code that could handle these contingencies, but it
	is not a priority at the moment. We trust you can cope within these limits.

	For legacy purposes, the perl/Python one-line comment delimiter # the beginning of a
	line is also recognized.

	To accommodate my habits, the perl/Python one-line comment delimiter ' #' is also
	recognized at the end of a line and material following it is eliminated. Note that the
	initial space is required.

	Blank lines and lines with only whitespace are also skipped.
	"""
    global FIN
    global FINline, FINnline

    line = FIN.readline()
    FINnline += 1
    while True:
#		print '==',line,
        if len(line) == 0:
            break  # calling function needs to handle EOF
        # deal with simple lines we need to skip
        if line[0] == '#' or line[0] == '\n' or line[0:2] == '<!' or len(line.strip()) == 0:
            line = FIN.readline()
            FINnline += 1
            continue
        if not line:  # handle EOF
            print "EOF hit in read_FIN_line()"
            raise EOFError
            return line
        if (' #' in line):
            line = line[:line.rfind(' #')]

        if ('<!--' in line):
            if ('-->' in line):  # just remove the substring
                pline = line.partition('<!--')
                line = pline[0] + pline[2][pline[2].find('-->') + 3:]
            else:
                while ('-->' not in line):
                    line = FIN.readline()
                    FINnline += 1
                line = FIN.readline()
                FINnline += 1
        if len(line.strip()) > 0:
            break
        line = FIN.readline()
        FINnline += 1
#	print "++",line
    FINline = line
    return line


# ========================== TAG EVALUATION FUNCTIONS ========================== #

def find_tag(tagstr):
# reads fin until tagstr is found
# can inherit EOFError raised in PETRreader.read_FIN_line()
    line = read_FIN_line()
    while (tagstr not in line):
        line = read_FIN_line()


def extract_attributes(theline):
# puts list of attribute and content pairs in the global AttributeList. First item is
# the tag itself
# If a twice-double-quote occurs -- "" -- this treated as "\"
# still to do: need error checking here
    """
    Structure of attributes extracted to AttributeList
    At present, these always require a quoted field which follows an '=', though it
    probably makes sense to make that optional and allow attributes without content
    """
#	print "PTR-1:", theline,
    theline = theline.strip()
    if ' ' not in theline:  # theline only contains a keyword
        PETRglobals.AttributeList = theline[1:-2]
#		print "PTR-1.1:", PETRglobals.AttributeList
        return
    pline = theline[1:].partition(' ')  # skip '<'
    PETRglobals.AttributeList = [pline[0]]
    theline = pline[2]
    while ('=' in theline):  # get the field and content pairs
        pline = theline.partition('=')
        PETRglobals.AttributeList.append(pline[0].strip())
        theline = pline[2]
        pline = theline.partition('"')
        if pline[2][0] == '"':   # twice-double-quote
            pline = pline[2][1:].partition('"')
            PETRglobals.AttributeList.append('"' + pline[0] + '"')
            theline = pline[2][1:]
        else:
            pline = pline[2].partition('"')
            PETRglobals.AttributeList.append(pline[0].strip())
            theline = pline[2]
#	print "PTR-2:", PETRglobals.AttributeList


def check_attribute(targattr):
    """ Looks for targetattr in AttributeList; returns value if found, null string otherwise."""
# This is used if the attribute is optional (or if error checking is handled by the calling
# routine); if an error needs to be raised, use get_attribute()
    if (targattr in PETRglobals.AttributeList):
        return (
            PETRglobals.AttributeList[
                PETRglobals.AttributeList.index(targattr) + 1]
        )
    else:
        return ""


def get_attribute(targattr):
    """ Similar to check_attribute() except it raises a MissingAttr error when the attribute is missing."""
    if (targattr in PETRglobals.AttributeList):
        return (
            PETRglobals.AttributeList[
                PETRglobals.AttributeList.index(targattr) + 1]
        )
    else:
        raise MissingAttr
        return ""


# ================== ANCILLARY DICTIONARY INPUT ================== #

def read_discard_list(discard_path):
    """
    Reads file containing the discard list: these are simply lines containing strings.
    If the string, prefixed with ' ', is found in the <Text>...</Text> sentence, the
    sentence is not coded. Prefixing the string with a '+' means the entire story is not
    coded with the string is found [see read_record() for details on story/sentence
    identification]. If the string ends with '_', the matched string must also end with
    a blank or punctuation mark; otherwise it is treated as a stem. The matching is not
    case sensitive.

    The file format allows # to be used as a in-line comment delimiter.

    File is stored as a simple list and the interpretation of the strings is done in
    check_discards()

    ===== EXAMPLE =====
    +5K RUN #  ELH 06 Oct 2009
    +ACADEMY AWARD   # LRP 08 Mar 2004
    AFL GRAND FINAL   # MleH 06 Aug 2009
    AFRICAN NATIONS CUP   # ab 13 Jun 2005
    AMATEUR BOXING TOURNAMENT   # CTA 30 Jul 2009
    AMELIA EARHART
    ANDRE AGASSI   # LRP 10 Mar 2004
    ASIAN CUP   # BNL 01 May 2003
    ASIAN FOOTBALL   # ATS 9/27/01
    ASIAN MASTERS CUP   # CTA 28 Jul 2009
    +ASIAN WINTER GAMES   # sls 14 Mar 2008
    ATP HARDCOURT TOURNAMENT   # mj 26 Apr 2006
    ATTACK ON PEARL HARBOR   # MleH 10 Aug 2009
    AUSTRALIAN OPEN
    AVATAR   # CTA 14 Jul 2009
    AZEROTH   # CTA 14 Jul 2009  (World of Warcraft)
    BADMINTON  # MleH 28 Jul 2009
    BALLCLUB   # MleH 10 Aug 2009
    BASEBALL
    BASKETBALL
    BATSMAN  # MleH 14 Jul 2009
    BATSMEN  # MleH 12 Jul 2009
    """

    PETRwriter.write_ErrorFile(
        "Reading " +
        PETRglobals.DiscardFileName +
        "\n")  # assumes this is already open
    open_FIN(discard_path, "discard")

    line = read_FIN_line()
    while len(line) > 0:  # loop through the file
        if '#' in line:
            line = line[:line.find('#')]
        targ = line.strip()
        if targ.startswith('+'):
            targ = '+ ' + targ[1:]
        else:
            targ = ' ' + targ
        PETRglobals.DiscardList.append(targ.upper())  # case insensitive match
        line = read_FIN_line()
    close_FIN()
# 	print PETRglobals.DiscardList[:8]


def read_issue_list(issue_path):
    """
    "Issues" do simple string matching and return a comma-delimited list of codes.
    The standard format is simply
            <string> [<code>]
    For purposes of matching, a ' ' is added to the beginning and end of the string: at
    present there are not wild cards, though that is easily added.

    The following expansions can be used (these apply to the string that follows up to
    the next blank)
            n: Create the singular and plural of the noun
            v: Create the regular verb forms ('S','ED','ING')
            +: Create versions with ' ' and '-'

    The file format allows # to be used as a in-line comment delimiter.

    File is stored in PETRglobals.IssueList as a list of tuples (string, index) where
    index refers to the location of the code in PETRglobals.IssueCodes. The coding is done
    in check_issues()

    Issues are written to the event record as a comma-delimited list to a tab-delimited
    field, e.g.

    20080801	ABC	EDF	0001	POSTSECONDARY_EDUCATION 2, LITERACY 1	AFP0808-01-M008-02
    20080801	ABC	EDF	0004		AFP0808-01-M007-01
    20080801	ABC	EDF	0001	NUCLEAR_WEAPONS 1	AFP0808-01-M008-01

    where XXXX NN, corresponds to the issue code and the number of matched phrases in the
    sentence that generated the event.

    This feature is optional and triggered by a file name in the PETR_config.ini file at

            issuefile_name = Phoenix.issues.140225.txt

    <14.02.28> NOT YET FULLY IMPLEMENTED
    The prefixes '~' and '~~' indicate exclusion phrases:
            ~ : if the string is found in the current sentence, do not code any of the issues
                    in section -- delimited by <ISSUE CATEGORY="...">...</ISSUE> -- containing
                    the string
            ~~ : if the string is found in the current *story*, do not code any of the issues
                    in section
    In the current code, the occurrence of an ignore phrase of either type cancels all
    coding of issues from the sentence

    ===== EXAMPLE =====

    <ISSUE CATEGORY="ID_ATROCITY">
    n:atrocity [ID_ATROCITY]
    n:genocide [ID_ATROCITY]
    ethnic cleansing [ID_ATROCITY]
    ethnic v:purge [ID_ATROCITY]
    ethnic n:purge [ID_ATROCITY]
    war n:crime [ID_ATROCITY]
    n:crime against humanity [ID_ATROCITY]
    n:massacre [ID_ATROCITY]
    v:massacre [ID_ATROCITY]
    al+zarqawi network [NAMED_TERROR_GROUP]
    ~Saturday Night massacre
    ~St. Valentine's Day massacre
    ~~Armenian genocide  # not coding historical cases
    </ISSUE>

    """

    PETRwriter.write_ErrorFile(
        "Reading " +
        PETRglobals.IssueFileName +
        "\n")  # assumes this is already open
    open_FIN(issue_path, "issues")

    PETRglobals.IssueCodes.append('~')  # initialize the ignore codes
    PETRglobals.IssueCodes.append('~~')

    line = read_FIN_line()
    while len(line) > 0:  # loop through the file
        if '#' in line:
            line = line[:line.find('#')]
        if line[0] == '~':  # ignore codes are only partially implemented
            if line[1] == '~':
                target = line[2:].strip().upper()
                codeindex = 1
            else:
                target = line[1:].strip().upper()
                codeindex = 0
        else:
            if '[' not in line:  # just do the codes now
                line = read_FIN_line()
                continue
            code = line[line.find('[') + 1:line.find(']')]  # get the code
            if code in PETRglobals.IssueCodes:
                codeindex = PETRglobals.IssueCodes.index(code)
            else:
                PETRglobals.IssueCodes.append(code)
                codeindex = len(PETRglobals.IssueCodes) - 1
            target = line[:line.find('[')].strip().upper()

        forms = [target]
        madechange = True
        while madechange:  # iterate until no more changes to make
            ka = 0
            madechange = False
            while ka < len(forms):
                if '+' in forms[ka]:
                    str = forms[ka]
                    forms[ka] = str.replace('+', ' ', 1)
                    forms.insert(ka + 1, str.replace('+', '-', 1))
                    madechange = True
                if 'N:' in forms[ka]:  # regular noun forms
                    part = forms[ka].partition('N:')
                    forms[ka] = part[0] + part[2]
                    plur = part[2].partition(' ')
                    if 'Y' == plur[0][-1]:
                        plural = plur[0][:-1] + 'IES'
                    else:
                        plural = plur[0] + 'S'
                    forms.insert(ka + 1, part[0] + plural + ' ' + plur[2])
                    madechange = True
                if 'V:' in forms[ka]:  # regular verb forms
                    part = forms[ka].partition('V:')
                    forms[ka] = part[0] + part[2]
                    root = part[2].partition(' ')
                    vscr = root[0] + "S"
                    forms.insert(ka + 1, part[0] + vscr + ' ' + root[2])
                    if root[0][-1] == 'E':  # root ends in 'E'
                        vscr = root[0] + "D "
                        forms.insert(ka + 2, part[0] + vscr + ' ' + root[2])
                        vscr = root[0][:-1] + "ING "
                    else:
                        vscr = root[0] + "ED "
                        forms.insert(ka + 2, part[0] + vscr + ' ' + root[2])
                        vscr = root[0] + "ING "
                    forms.insert(ka + 3, part[0] + vscr + ' ' + root[2])
                    madechange = True

                ka += 1

        for item in forms:
            PETRglobals.IssueList.append(tuple([' ' + item + ' ', codeindex]))
        line = read_FIN_line()
    close_FIN()

    """ debug
	ka = 0
	while ka < 128 :
		print PETRglobals.IssueList[ka],PETRglobals.IssueCodes[PETRglobals.IssueList[ka][1]]
		ka += 1
	"""

# ================== VERB DICTIONARY INPUT ================== #


def read_verb_dictionary(verb_path):
    """ Reads the verb dictionary from VerbFileName """
# <13.07.27> Still need to do
# 1. New WordNet dictionary format
# 2. % compound actor token: patterns with this are skipped
    """ Verb dictionary list elements:
	For basic verb/pattern combinations, the dictionary format is identical to TABARI; it
	differs on the specification and interpretation of synsets, and does not allow
	disconjunctive sets in patterns (these are skipped, and should be replaced with synsets).

	[0] True: primary form
		[1] Code
		[2:] 3-tuples of lower pattern, upper pattern and code. Upper pattern is stored
		     in reverse order
	[0] False
		[1]: primary form (use as a pointer)

	Dictionary automatically generates the regular forms of the verb if it is regular;
	otherwise the irregular forms can be specified in {...} following the primary verb.

	SYNSETS
	Synonym sets (synsets) are labelled with a string beginning with & and defined using
	the label followed by a series of lines beginning with + containing words or phrases.
	The phrases are interpreted as requiring consecutive words; the words can be separated
	with either spaces or underscores (they are converted to spaces). Synset phrases can
	only contain words, not $, +, % or ^ tokens or synsets. At present, a synsets cannot
	contain another synset as an element. [see note below] Synsets be used anywhere in a
	pattern that a word or phrase can be used. A synset must be defined before it is used:
	a pattern containing an undefined synset will be ignored -- but those definitions can
	occur anywhere in the file.

	====== EXAMPLE =====

	&CURRENCY
	+DOLLARS
	+EUROS
	+AUSTRIAN FLORIN
	+GOLDEN_GOBLIN_GALLEONS
	+PESO
	+KRONER
	+YUM YENNYEN
	+JAVANESE YEN
	+SWISS FRANCS
	+YEN

	&ALTCURR
	+BITCOIN
	+PIRATE GOLD
	+LEPRECHAUN GOLD

	 CONTRIBUTE [070] ;tony  3/12/91
	- * &CURRENCY [903]; -PAS 12.01.12
	- * &ALTCURR [904]; -PAS 14.05.08
	- * RUPEES  [071]

	&TESTSYN3
	+TO THE END
	+TO THE DEATH
	+UNTIL HELL FREEZES OVER

	&TESTSYN4
	+TO THE END OF THE EARTH
	+TO THE DEATH

	VOW  [170] ;tony  3/9/91
	- * RESIST &TESTSYN3 [113] ; pas 4/20/03
	- * RESIST &TESTSYN4  [115] ; pas 4/20/03
	- * RESISTANCE TO THE INVADING  [114] ; pas 4/20/03
	- * RESIST  [112] ;tony  4/29/91
	- * WAR  [173] ;tony  4/22/91

	Notes
	1. 	TABARI allowed recursive synsets -- that is, synsetS embedded in patterns and other
	    synsets. It should be possible to do this fairly easily, at least with basic
	    synsets as elements (not as patterns) but a simple call in syn_match(isupperseq)
	    was not sufficient, so this needs more work.

	ADDITIONAL PROGRAMMING NOTES

	1.	The construction "XXXX_ " is ambiguous in PETR, but in almost all cases in a TAB
		dictionary means an unstemmed word (which is all PETR allows anyway) followed by
		an open match, and is automatically converted to this.

	"""
    global theverb, verb  # <14.05.07> : not needed, right?

    def make_phrase_list(thepat):
        """ Converts a pattern phrase into a list of alternating words and connectors """
        if len(thepat) == 0:
            return []
        phlist = []
        start = 0
        maxlen = len(thepat) + 1  # this is just a telltail
        while start < len(thepat):  # break phrase on ' ' and '_'
            spfind = thepat.find(' ', start)
            if spfind == -1:
                spfind = maxlen
            unfind = thepat.find('_', start)
            if unfind == -1:
                unfind = maxlen
            # somehow think I don't need this check...well, I just need the
            # terminating point, still need to see which is lower
            if unfind < spfind:
                phlist.append(thepat[start:unfind])
                phlist.append('_')
                start = unfind + 1
            else:
                phlist.append(thepat[start:spfind])
                phlist.append(' ')
                start = spfind + 1
                                                        # check for missing
                                                        # synsets
        ka = 0
        while ka < len(phlist):
            if len(phlist[ka]) > 0:
                if (phlist[ka][0] == '&') and (phlist[ka] not in PETRglobals.VerbDict):
                    PETRwriter.write_FIN_error(
                        "Synset " + phlist[ka] + " has not been defined; pattern skipped")
                    raise ValueError  # this will do...
            ka += 2
        return phlist

    def get_verb_forms():
        """  Read the irregular forms of a verb. """
        global verb, theverb
        scr = verb.partition('{')
        sc1 = scr[2].partition('}')
        forms = sc1[0].split()
        for wrd in forms:
            vscr = wrd + " "
            PETRglobals.VerbDict[vscr] = [False, theverb]

    def make_verb_forms():
        """ Create the regular forms of a verb. """
        global theverb
        vroot = theverb[:-1]
        vscr = vroot + "S "
        PETRglobals.VerbDict[vscr] = [False, theverb]
        if vroot[-1] == 'E':  # root ends in 'E'
            vscr = vroot + "D "
            PETRglobals.VerbDict[vscr] = [False, theverb]
            vscr = vroot[:-1] + "ING "
        else:
            vscr = vroot + "ED "
            PETRglobals.VerbDict[vscr] = [False, theverb]
            vscr = vroot + "ING "
        PETRglobals.VerbDict[vscr] = [False, theverb]

    # note that this will be ignored if there are no errors
    PETRwriter.write_ErrorFile("Reading " + PETRglobals.VerbFileName + "\n")
    open_FIN(verb_path, "verb")

    theverb = ''
    ka = 0   # primary verb count ( debug )
    line = read_FIN_line()
    while len(line) > 0:  # loop through the file
        # this code, obviously, was written while I was still thinking in
        # perl...
        part = line.partition('[')
        verb = part[0].strip() + ' '
        scr = part[2].partition(']')
        code = scr[0]
#		print verb, code
        if verb[0] == '-':
            # currently aren't processing these
            if '%' in verb or '{' in verb:
                line = read_FIN_line()
                continue
#			print 'RVD-1',verb
            if not hasforms:
                make_verb_forms()
                hasforms = True
            # resolve the ambiguous '_ ' construction to ' '
            verb = verb.replace('_ ', ' ')
            targ = verb[1:].partition('*')
            try:
                highpat = make_phrase_list(targ[0].lstrip())
    #			print 'RVD-2',highpat
                highpat.reverse()
                lowphrase = targ[2].rstrip()
                if len(lowphrase) == 0:
                    lowpat = []
                else:
                    lowpat = [targ[2][0]]   # start with connector
                    loclist = make_phrase_list(lowphrase[1:])
                    lowpat.extend(loclist[:-1])   # don't need the final blank
    #			print 'RVD-3',lowpat
                PETRglobals.VerbDict[theverb].append([highpat, lowpat, code])
            except ValueError:
                # just trap the error, which will skip the line containing it
                pass
            line = read_FIN_line()

        elif verb[0] == '{':
            get_verb_forms()
            hasforms = True
            line = read_FIN_line()

        elif verb[0] == '&':  # Read and store a synset.
            verb = verb[:-1]  # remove final blank
            PETRglobals.VerbDict[verb] = []
            line = read_FIN_line()
            while line[0] == '+':
                wordstr = line[1:].replace('_', ' ').strip()
                # <14.05.08> Multi-word phrases are always converted to lists between checking, so probably it would be useful to store them as tuples once
                PETRglobals.VerbDict[verb].append(wordstr)
                line = read_FIN_line()
#			print "rvd/gs:",verb, PETRglobals.VerbDict[verb]

        else:
    #		if theverb != '': print '::', theverb, PETRglobals.VerbDict[theverb]
            # create forms for the previous verb
            if len(theverb) > 0 and not hasforms:
                make_verb_forms()
            theverb = verb
            PETRglobals.VerbDict[verb] = [True, code]
            hasforms = False
            ka += 1   # counting primary verbs
#			if ka > 10: break
            line = read_FIN_line()

#		print "--:",line,
    close_FIN()


def show_verb_dictionary(filename=''):
# debugging function: displays VerbDict to screen or writes to filename
    if len(filename) > 0:
        fout = open(filename, 'w')
        fout.write('PETRARCH Verb Dictionary Internal Format\n')
        fout.write('Run time: ' + PETRglobals.RunTimeString + '\n')

        for locword, loclist in PETRglobals.VerbDict.iteritems():
            fout.write(locword)
            if loclist[0]:
                if len(loclist) > 1:
                    # pattern list
                    fout.write("::\n" + str(loclist[1:]) + "\n")
                else:
                    fout.write(":: " + str(loclist[1]) + "\n")    # simple code
            else:
                fout.write('-> ' + str(loclist[1]) + "\n")    # pointer
        fout.close()

    else:
        for locword, loclist in PETRglobals.VerbDict.iteritems():
            print locword,
            if loclist[0]:
                if len(loclist) > 2:
                    print '::\n', loclist[1:]   # pattern list
                else:
                    print ':: ', loclist[1]   # simple code
            else:
                print '-> ', loclist[1]    # pointer


# ================== ACTOR DICTIONARY INPUT ================== #
def make_noun_list(nounst):
# parses a noun string -- actor, agent or agent plural -- and returns in a list which
# has the keyword and initial connector in the first tuple
    nounlist = []
    start = 0
    maxlen = len(nounst) + 1  # this is just a telltail
    while start < len(nounst):  # break phrase on ' ' and '_'
        spfind = nounst.find(' ', start)
        if spfind == -1:
            spfind = maxlen
        unfind = nounst.find('_', start)
        if unfind == -1:
            unfind = maxlen
        # <13.06.05> not sure we need this check...well, I just need the terminating point, still need to see which is lower
        if unfind < spfind:
            # this won't change, so use a tuple
            nounlist.append((nounst[start:unfind], '_'))
            start = unfind + 1
        else:
            nounlist.append((nounst[start:spfind], ' '))
            start = spfind + 1
    return nounlist


def dstr_to_ordate(datestring):
    """ Computes an ordinal date from a Gregorian calendar date string YYYYMMDD or YYMMDD."""
    """
	This uses the 'ANSI date' with the base -- ordate == 1 -- of 1 Jan 1601.  This derives
	from [OMG!] COBOL (see http://en.wikipedia.org/wiki/Julian_day) but in fact should
	work fairly well for our applications.

	For consistency with KEDS and TABARI, YY years between 00 and 30 are interpreted as
	20YY; otherwise 19YY is assumed.

	Formatting and error checking:
	1. YYMMDD dates *must* be <=7 characters, otherwise YYYYMMDD is assumed
	2. If YYYYMMDD format is used, only the first 8 characters are checked so it is okay
       to have junk at the end of the string.
	3. Days are checked for validity according to the month and year, e.g. 20100931 is
	   never allowed; 20100229 is not valid but 20120229 is valid
	4. Invalid dates raise DateError

	Source of algorithm: http://en.wikipedia.org/wiki/Julian_day

	Unit testing:
	Julian dates from http://aa.usno.navy.mil/data/docs/JulianDate.php (set time to noon)
	Results:
		dstr_to_ordate("20130926") # 2456562
		dstr_to_ordate("090120") # 2454852
		dstr_to_ordate("510724")  # 2433852
		dstr_to_ordate("19411207")  # 2430336
		dstr_to_ordate("18631119")  # 2401829
		dstr_to_ordate("17760704")  # 2369916
		dstr_to_ordate("16010101")  # 2305814
	"""

# print datestring        # debug
    try:
        if len(datestring) > 7:
            year = int(datestring[:4])
            month = int(datestring[4:6])
            day = int(datestring[6:8])
        else:
            year = int(datestring[:2])
            if year <= 30:
                year += 2000
            else:
                year += 1900
            month = int(datestring[2:4])
            day = int(datestring[4:6])
    except ValueError:
        raise DateError
# print year, month, day    # debug

    if day <= 0:
        raise DateError

    if month == 2:
        if year % 400 == 0:
            if day > 29:
                raise DateError
        elif year % 100 == 0:
            if day > 28:
                raise DateError
        elif year % 4 == 0:
            if day > 29:
                raise DateError
        else:
            if day > 28:
                raise DateError
    elif month in [4, 6, 9, 11]:         # 30 days have September...
        if day > 30:
            raise DateError
    else:                             # all the rest I don't remember...
        if day > 31:
            raise DateError

    if (month < 3):
        adj = 1
    else:
        adj = 0
    yr = year + 4800 - adj
    mo = month + (12 * adj) - 3
    ordate = day + math.floor((153 * mo + 2) / 5) + 365 * yr
    ordate += math.floor(yr / 4) - math.floor(yr / 100) + \
        math.floor(yr / 400) - 32045  # pure Julian date
# print "Julian:", ordate        # debug to cross-check for unit test
    ordate -= 2305813   # adjust for ANSI date

# print ordate        # debug
    return int(ordate)


def read_actor_dictionary(actorfile):
    """ Reads a TABARI-style actor dictionary. """
    """
	Actor dictionary list elements:
	Actors are stored in a dictionary of a list of pattern lists keyed on the first word
	of the phrase. The pattern lists are sorted by length.
	The individual pattern lists begin with an integer index to the tuple of possible codes
	(that is, with the possibility of date restrictions) in PETRglobals.ActorCodes,
	followed by the connector from the key, and then a series of 2-tuples containing the
	remaining words and connectors. A 2-tuple of the form ('', ' ') signals the end of the
	list. <14.02.26: Except at the moment these are just 2-item lists, not tuples, but
	this could be easily changed and presumably would be more efficient: these are not
	changed so they don't need to be lists.<>

	Connector:
		blank: words can occur between the previous word and the next word
		_ (underscore): words must be consecutive: no intervening words

	The codes with possible date restrictions are stored as lists in a [genuine] tuple in
	PETRglobals.ActorCodes in the following format where
	'ordate' is an ordinal date:
		[code] : unrestricted code
		[0,ordate,code] : < restriction
		[1,ordate,code] : > restriction
		[2,ordate,ordate, code] : - (interval) restriction

	Synonyms simply use the integer code index to point to these tuples.

	STRICT FORMATTING OF THE ACTOR DICTIONARY
	[With some additional coding, this can be relaxed, but anything following these
	rules should read correctly]
	Basic structure is a series of records of the form
		[primary phrase]
		[optional synonym phrases beginning with '+']
		[optional date restrictions beginning with '\t']

	Material that is ignored
	1. Anything following ';' (this is the old KEDS/TABARI format and should probably
	   be replaced with '#' for consistency
	2. Any line beginning with '#' or <!
	3. Any null line (that is, line consisting of only \n

	A "phrase string" is a set of character strings separated by either blanks or
	underscores.

	A "code" is a character string without blanks

	A "date" has the form YYYYMMDD or YYMMDD. These can be mixed, e.g.
		JAMES_BYRNES_  ; CountryInfo.txt
			[USAELI 18970101-450703]
			[USAGOV 450703-470121]

	Primary phrase format:
	phrase_string  { optional [code] }
		if the code is present, it becomes the default code if none of the date restrictions
		are satisfied. If it is not present and none of the restrictions are satisfied,
		this is equivalent to a null code

	Synonym phrase
	+phrase_string

	Date restriction
	\t[code restriction]
	where restriction -- everything is interpret as 'or equal' -- takes the form
	<date : applies to times before date
	>date : applies to times after date
	date-date: applies to times between dates

	A date restriction of the form
	\t[code]
	is the same as a default restriction.


	== Example ===
	# .actor file produced by translate.countryinfo.pl from CountryInfo.120106.txt
	# Generated at: Tue Jan 10 14:09:48 2012
	# Version: CountryInfo.120106.txt

	AFGHANISTAN_  [AFG]
	+AFGHAN_
	+AFGANISTAN_
	+AFGHANESTAN_
	+AFGHANYSTAN_
	+KABUL_
	+HERAT_

	MOHAMMAD_ZAHIR_SHAH_  ; CountryInfo.txt
		[AFGELI 320101-331108]
		[AFGGOV 331108-730717]
		[AFGELI 730717-070723]

	ABDUL_QADIR_  ; CountryInfo.txt
	+NUR_MOHAMMAD_TARAKI_  ; CountryInfo.txt
	+HAFIZULLAH_AMIN_  ; CountryInfo.txt
		[AFGELI 620101-780427]
		[AFGGOV 780427-780430]
		[AFGELI]

	HAMID_KARZAI_  [AFGMIL]; CountryInfo.txt
	+BABRAK_KARMAL_  ; CountryInfo.txt
	+SIBGHATULLAH_MOJADEDI_  ; CountryInfo.txt
		[AFGGOV 791227-861124]
		[AFGGOV 791227-810611]

	"""

    dateerrorstr = "String in date restriction could not be interpreted; line skipped"

    PETRwriter.write_ErrorFile("Reading " + actorfile + "\n")
    open_FIN(actorfile, "actor")

    # location where codes for current actor will be stored
    codeindex = len(PETRglobals.ActorCodes)
    # list of codes -- default and date restricted -- for current actor
    curlist = []

    line = read_FIN_line()
    while len(line) > 0:  # loop through the file
        if '---STOP---' in line:
            break
        if line[0] == '\t':  # deal with date restriction
# print "DR:",line,   # debug
            try:
                brack = line.index('[')
            except ValueError:
# PETRwriter.write_FIN_error('Mk1'+dateerrorstr) 	# debug
                PETRwriter.write_FIN_error(dateerrorstr)
                line = read_FIN_line()
                continue
            part = line[brack + 1:].strip().partition(' ')
            code = part[0].strip()
            rest = part[2].lstrip()
            if '<' in rest or '>' in rest:
                # find an all-digit string: this is more robust than the TABARI
                # equivalent
                ka = 1
                while (ka < len(rest)) and (not rest[ka].isdigit()):
                    # if this fails the length test, it will be caught as
                    # DateError
                    ka += 1
                kb = ka + 6
                while (kb < len(rest)) and (rest[kb].isdigit()):
                    kb += 1
                try:
                    ord = dstr_to_ordate(rest[ka:kb])
                except DateError:
                    PETRwriter.write_FIN_error(dateerrorstr)
                    line = read_FIN_line()
                    continue

                if rest[0] == '<':
                    curlist.append([0, ord, code])
                else:
                    curlist.append([1, ord, code])
            elif '-' in rest:
                part = rest.partition('-')
                try:
                    pt0 = part[0].strip()
                    ord1 = dstr_to_ordate(pt0)
                    part2 = part[2].partition(']')
                    pt2 = part2[0].strip()
                    ord2 = dstr_to_ordate(pt2)
                except DateError:
                    PETRwriter.write_FIN_error(dateerrorstr)
#					PETRwriter.write_FIN_error('Mk3: -'+ pt0 + '- -' + pt2 + '-' )
                    line = read_FIN_line()
                    continue
                if ord2 < ord1:
                    PETRwriter.write_FIN_error(
                        "End date in interval date restriction is less than starting date; line skipped")
                    line = read_FIN_line()
                    continue
                curlist.append([2, ord1, ord2, code])
            else:  # replace default code
                # list containing a single code
                curlist.append([code[:code.find(']')]])

        else:
            if line[0] == '+':  # deal with synonym
#				print "Syn:",line,
                part = line.partition(';')  # split on comment, if any
                actor = part[0][1:].strip() + ' '
            else:  					# primary phrase with code
                if len(curlist) > 0:
                    PETRglobals.ActorCodes.append(tuple(curlist))
                    codeindex = len(PETRglobals.ActorCodes)
                    curlist = []
                if '[' in line:  # code specified?
                    part = line.partition('[')
                    # list containing a single code
                    curlist.append([part[2].partition(']')[0].strip()])
                else:
                    # no code, so don't update curlist
                    part = line.partition(';')
                actor = part[0].strip() + ' '
            nounlist = make_noun_list(actor)
            keyword = nounlist[0][0]
            phlist = [codeindex, nounlist[0][1]] + nounlist[1:]
            # we don't need to store the first word, just the connector
            if keyword in PETRglobals.ActorDict:
                PETRglobals.ActorDict[keyword].append(phlist)
            else:
                PETRglobals.ActorDict[keyword] = [phlist]
            if isinstance(phlist[0], str):
                # save location of the list if this is a primary phrase
                curlist = PETRglobals.ActorDict[keyword]

        line = read_FIN_line()

    close_FIN()

    # sort the patterns by the number of words
    for lockey in PETRglobals.ActorDict.keys():
        PETRglobals.ActorDict[lockey].sort(key=len, reverse=True)


def show_actor_dictionary(filename=''):
# debugging function: displays ActorDict to screen or writes to filename
    if len(filename) > 0:
        fout = open(filename, 'w')
        fout.write(
            'PETRARCH Actor Dictionary and Actor Codes Internal Format\n')
        fout.write('Run time: ' + PETRglobals.RunTimeString + '\n')

        for locword, loclist in PETRglobals.ActorDict.iteritems():
            fout.write(locword + " ::\n" + str(loclist) + "\n")

        fout.write('\nActor Codes\n')
        ka = 0
        while ka < len(PETRglobals.ActorCodes):
            fout.write(str(ka) + ': ' + str(PETRglobals.ActorCodes[ka]) + '\n')
            ka += 1

        fout.close()

    else:
        for locword, loclist in PETRglobals.ActorDict.iteritems():
            print locword, "::"
            if isinstance(loclist[0][0], str):
                print loclist   # debug
            else:
                print 'PTR,', loclist


# ================== AGENT DICTIONARY INPUT ================== #
def read_agent_dictionary(agent_path):
    """ Reads an agent dictionary
    Agents are stored in a simpler version of the Actors dictionary: a list of phrases
    keyed on the first word of the phrase.
    The individual phrase lists begin with the code, the connector from the key, and then
    a series of 2-tuples containing the remaining words and connectors. A 2-tuple of the
    form ('', ' ') signals the end of the list.

    Connector:
            blank: words can occur between the previous word and the next word
            _ (underscore): words must be consecutive: no intervening words

    FORMATTING OF THE AGENT DICTIONARY
    [With some additional coding, this can be relaxed, but anything following these
    rules should read correctly]
    Basic structure is a series of records of the form
            phrase_string {optional plural}  [agent_code]

    Material that is ignored
    1. Anything following '#'
    2. Any line beginning with '#' or '<!'
    3. Any null line (that is, line consisting of only \n

    A "phrase string" is a set of character strings separated by either blanks or
    underscores.

    A "agent_code" is a character string without blanks that is either preceded (typically)
    or followed by '~'. If the '~' precedes the code, the code is added after the actor
    code; if it follows the code, the code is added before the actor code (usually done
    for organizations, e.g. NGO~)

    Plurals:
            Regular plurals -- those formed by adding 'S' to the root, adding 'IES' if the
            root ends in 'Y', and added 'ES' if the root ends in 'SS' -- are generated automatically

            If the plural has some other form, it follows the root inside {...}

            If a plural should not be formed -- that is, the root is only singular or only
            plural, or the singular and plural have the same form (e.g. "police"), use a null
            string inside {}.

            If there is more than one form of the plural -- "attorneys general" and "attorneys
            generals" are both in use -- just make a second entry with one of the plural forms
            nulled (though in this instance -- ain't living English wonderful? -- you could null
            the singular and use an automatic plural on the plural form) Though in a couple
            test sentences, this phrase confused SCNLP.

    Substitution Markers:
            These are used to handle complex equivalents, notably

                    !PERSON! = MAN, MEN, WOMAN, WOMEN, PERSON
                    !MINST! = MINISTER, MINISTERS, MINISTRY, MINISTRIES

            and used in the form

                    CONGRESS!PERSON! [~LEG}
                    !MINIST!_OF_INTERNAL_AFFAIRS

            The marker for the substitution set is of the form !...! and is followed by an =
            and a comma-delimited list; spaces are stripped from the elements of the list so
            these can be added for clarity. Every time in the list is substituted for the marker,
            with no additional plural formation, so the first construction would generate

                    CONGRESSMAN [~LEG}
                    CONGRESSMEN [~LEG}
                    CONGRESSWOMAN [~LEG}
                    CONGRESSWOMEN [~LEG}
                    CONGRESSPERSON [~LEG}


    Agent code combination rules
            By default, agent codes are assigned in the order they are found, and all phrases
            that correspond to an agent are coded, followed by the removal of duplicate codes.
            \footnote{This is in contrast to patterns,
            where only the longest matching pattern is used. Someone is also welcome to
            implement this alternative, but in the spirit of maximizing the information that
            the agent system can extract, we're defaulting to ``all matches''}. This can lead
            to information that is either redundant (e.g. (e.g. 'REBEL OPPOSITION GROUP [ROP]'
            and 'OPPOSITION GROUP' [OPP] would yield ROPOPP where ROP is sufficient) or
            situations where the same information produces codes in a different order, e.g.
            'OPPOSITION' [OPP], 'LEGISLATOR' [LEG], 'PARIAMENTARY' [LEG] produces LEGOPP for
            "pariamentary opposition" and "OPPLEG" for "opposition legislators."

            Agent code combination rules provide a systematic way of deal with this. Rules can
            have two forms:
            [original code] => [replacement code] : substitute the replacement when the exact
                                                                                            original code occurs
            [original code] +> [replacement code] : substitute the replacement when the any
                                                                                            permutation of the 3-character blocks in
                                                                                            the original code occurs

            Rules are applied until none occur, to 6- and 9-character codes can be transformed
            using temporary substitutions.

            Rules can be specified either in-line -- typically associated with a set of agents
            relevant to the rules -- or in a block

            Inline: <Combine rule = "...">
            Block: delimited by <CombineBlock>
                                                    ...
                                                    </CombineBlock>
                       with the rules on the intervening lines, one per line.

            The command <Combine rule = "alphabetic"> specifies that the agents will first
            be alphabetized by 3-character blocks -- prefixed and suffixed sets are treated
            separately -- and then the rules applied. Again, longer codes can be dealt with
            using substitutions.

    == Example ===
    <!-- PETRARCH VALIDATION SUITE AGENTS DICTIONARY -->
    <!-- VERSION: 0.1 -->
    <!-- Last Update: 27 November 2013 -->

    PARLIAMENTARY_OPPOSITION {} [~OPP] #jap 11 Oct 2002
    AMBASSADOR [~GOV] # LRP 02 Jun 2004
    COPTIC_CHRISTIAN [~CHRCPT] # BNL 10 Jan 2002
    FOREIGN_MINISTER [~GOVFRM] # jap 4/14/01
    PRESIDENT [~GOVPRS] # ns 6/26/01
    AIR_FORCE {} [~MIL] # ab 06 Jul 2005
    OFFICIAL_MEDIA {} [~GOVMED] # ab 16 Aug 2005
    ATTORNEY_GENERAL {ATTORNEYS_GENERAL} [~GOVATG] # mj 05 Jan 2006
    <Combine rule = "LAWGOVATGMIL => GOV">  # remove match to ATTORNEY and GENERAL
    FOREIGN_MINISTRY [~GOV] # mj 17 Apr 2006
    HUMAN_RIGHTS_ACTIVISTS  [NGM~] # ns 6/14/01
    HUMAN_RIGHTS_BODY  [NGO~] # BNL 07 Dec 2001
    <Combine rule = "NGMNGO +> NGM">
    TROOP {} [~MIL] # ab 22 Aug 2005

    """
    global subdict

    def store_agent(nounst, code):
    # parses nounstring and stores the result with code
        nounlist = make_noun_list(nounst)
        keyword = nounlist[0][0]
        phlist = [code, nounlist[0][1]] + nounlist[1:]
        # we don't need to store the first word, just the connector
        if keyword in PETRglobals.AgentDict:
            PETRglobals.AgentDict[keyword].append(phlist)
        else:
            PETRglobals.AgentDict[keyword] = [phlist]
        # <13.12.16> : this isn't needed for agents, correct?
        if isinstance(phlist[0], str):
            # save location of the list if this is a primary phrase
            curlist = PETRglobals.AgentDict[keyword]

    def define_marker(line):
        global subdict
        if line[line.find('!') + 1:].find('!') < 0 or line[line.find('!'):].find('=') < 0:
            PETRwriter.write_FIN_error(markdeferrorstr + enderrorstr)
            return
        ka = line.find('!') + 1
        marker = line[ka:line.find('!', ka)]
#		print marker
        loclist = line[line.find('=', ka) + 1:].strip()
        subdict[marker] = []
        for item in loclist.split(','):
            subdict[marker].append(item.strip())
#		print subdict[marker]

    def store_marker(agent, code):
        global subdict
        if agent[agent.find('!') + 1:].find('!') < 0:
            ka = agent.find('!')
            PETRwriter.write_FIN_error(
                "Substitution marker \"" +
                agent[
                    ka:agent.find(
                        ' ',
                        ka) +
                    1] +
                "\" syntax incorrect" +
                enderrorstr)
            return
        part = agent.partition('!')
        part2 = part[2].partition('!')
        if part2[0] not in subdict:
            PETRwriter.write_FIN_error(
                "Substitution marker !" +
                part2[
                    0] +
                "! missing in .agents file; line skipped")
            return
        for subst in subdict[part2[0]]:
#			print part[0]+subst+part2[2]
            store_agent(part[0] + subst + part2[2], code)

    # this is just called when the program is loading, so keep them local.
    # <14.04.22> Or just put these as constants in the function calls: does it make a difference?
    enderrorstr = " in .agents file ; line skipped"
    codeerrorstr = "Codes are required for agents"
    brackerrorstr = "Missing '}'"
    markdeferrorstr = "Substitution marker incorrectly defined"

    subdict = {}  # substitution set dictionary

    # note that this will be ignored if there are no errors
    PETRwriter.write_ErrorFile("Reading " + PETRglobals.AgentFileName + "\n")
    open_FIN(agent_path, "agent")

    line = read_FIN_line()
    while len(line) > 0:  # loop through the file

        if '!' in line and '=' in line:  # synonym set
            define_marker(line)
            line = read_FIN_line()
            continue

        if '[' not in line:  # code specified?
            PETRwriter.write_FIN_error(codeerrorstr + enderrorstr)
            line = read_FIN_line()
            continue

        part = line.partition('[')
        code = part[2].partition(']')[0].strip()
        agent = part[0].strip() + ' '
        if '!' in part[0]:
            store_marker(agent, code)  # handle a substitution marker
        elif '{' in part[0]:
            if '}' not in part[0]:
                PETRwriter.write_FIN_error(brackerrorstr + enderrorstr)
                line = read_FIN_line()
                continue
            agent = part[0][:part[0].find('{')].strip() + ' '
            # this will automatically set the null case
            plural = part[0][part[0].find('{') + 1:part[0].find('}')].strip()
        else:
            if 'Y' == agent[-2]:
                plural = agent[:-2] + 'IES'  # space is added below
            elif 'S' == agent[-2]:
                plural = agent[:-1] + 'ES'
            else:
                plural = agent[:-1] + 'S'

#			print agent,plural
        store_agent(agent, code)
        if len(plural) > 0:
            store_agent(plural + ' ', code)

        line = read_FIN_line()

    close_FIN()

    # sort the patterns by the number of words
    for lockey in PETRglobals.AgentDict.keys():
        PETRglobals.AgentDict[lockey].sort(key=len, reverse=True)


def show_AgentDict(filename=''):
# debugging function: displays AgentDict to screen or writes to filename
    if len(filename) > 0:
        fout = open(filename, 'w')
        fout.write('PETRARCH Agent Dictionary Internal Format\n')
        fout.write('Run time: ' + PETRglobals.RunTimeString + '\n')

        for locword, loclist in PETRglobals.AgentDict.iteritems():
            fout.write(locword + " ::\n")
            fout.write(str(loclist) + "\n")
        fout.close()

    else:
        for locword, loclist in PETRglobals.AgentDict.iteritems():
            print locword, "::"
            print loclist

# ==== Input format reading


def read_xml_input(filepaths, parsed=False):
    holding = {}

    for path in filepaths:
        tree = ET.iterparse(path)

        for event, elem in tree:
            if event == "end" and elem.tag == "Sentence":
                story = elem

                #Check to make sure all the proper XML attributes are included
                attribute_check = [key in story.attrib for key in
                                   ['date', 'id', 'sentence']]
                if not attribute_check:
                    print 'Need to properly format your XML...'
                    break

                #If the XML contains StanfordNLP parsed data, pull that out
                if parsed:
                    parsed_content = story.find('Parse').text
                    parsed_content = utilities._format_parsed_str(parsed_content)
                else:
                    parsed_content = ''

                #Get the sentence information
                if story.attrib['sentence'] == 'True':
                    entry_id, sent_id = story.attrib['id'].split('_')

                    text = story.find('Text').text
                    text = text.replace('\n', '').replace('  ', '')
                    sent_dict = {'content': text, 'parsed': parsed_content}
                else:
                    entry_id = story.attrib['id']

                    text = story.find('Text').text
                    text = text.replace('\n', '').replace('  ', '')
                    #Create unique dicts for each

                meta_content = {'date': story.attrib['date']}
                content_dict = {'sents': {sent_id: sent_dict},
                                'meta': meta_content}

                if entry_id not in holding:
                    holding[entry_id] = content_dict
                else:
                    holding[entry_id]['sents'][sent_id] = sent_dict

                elem.clear()

    return holding


def read_pipeline_input(pipeline_list):
    holding = {}
    for entry in pipeline_list:
        entry_id = str(entry['_id'])
        meta_content = {'date': utilities._format_datestr(entry['date']),
                        'date_added': entry['date_added'],
                        'source': entry['source'],
                        'story_title': entry['title']}
        split_sents = _sentence_segmenter(entry['content'])
        #TODO Make the number of sents a setting
        sent_dict = {}
        for i, sent in enumerate(split_sents[:7]):
            sent_dict[i] = {'content': sent}

        content_dict = {'sents': sent_dict, 'meta': meta_content}
        holding[entry_id] = content_dict

    return holding


def _sentence_segmenter(paragr):
    """
    Function to break a string 'paragraph' into a list of sentences based on
    the following rules:

    1. Look for terminal [.,?,!] followed by a space and [A-Z]
    2. If ., check against abbreviation list ABBREV_LIST: Get the string
    between the . and the previous blank, lower-case it, and see if it is in
    the list. Also check for single-letter initials. If true, continue search
    for terminal punctuation
    3. Extend selection to balance (...) and "...". Reapply termination rules
    4. Add to sentlist if the length of the string is between MIN_SENTLENGTH
    and MAX_SENTLENGTH
    5. Returns sentlist

    Parameters
    ----------

    paragr: String.
            Content that will be split into constituent sentences.

    Returns
    -------

    sentlist: List.
                List of sentences.

    """
    # this is relatively high because we are only looking for sentences that
    # will have subject and object
    MIN_SENTLENGTH = 100
    MAX_SENTLENGTH = 512

    # sentence termination pattern used in sentence_segmenter(paragr)
    terpat = re.compile('[\.\?!]\s+[A-Z\"]')

    # source: LbjNerTagger1.11.release/Data/KnownLists/known_title.lst from
    # University of Illinois with editing
    ABBREV_LIST = ['mrs.', 'ms.', 'mr.', 'dr.', 'gov.', 'sr.', 'rev.', 'r.n.',
                   'pres.', 'treas.', 'sect.', 'maj.', 'ph.d.', 'ed. psy.',
                   'proc.', 'fr.', 'asst.', 'p.f.c.', 'prof.', 'admr.',
                   'engr.', 'mgr.', 'supt.', 'admin.', 'assoc.', 'voc.',
                   'hon.', 'm.d.', 'dpty.',  'sec.', 'capt.', 'c.e.o.',
                   'c.f.o.', 'c.i.o.', 'c.o.o.', 'c.p.a.', 'c.n.a.', 'acct.',
                   'llc.', 'inc.', 'dir.', 'esq.', 'lt.', 'd.d.', 'ed.',
                   'revd.', 'psy.d.', 'v.p.',  'senr.', 'gen.', 'prov.',
                   'cmdr.', 'sgt.', 'sen.', 'col.', 'lieut.', 'cpl.', 'pfc.',
                   'k.p.h.', 'cent.', 'deg.', 'doz.', 'Fahr.', 'Cel.', 'F.',
                   'C.', 'K.', 'ft.', 'fur.',  'gal.', 'gr.', 'in.', 'kg.',
                   'km.', 'kw.', 'l.', 'lat.', 'lb.', 'lb per sq in.', 'long.',
                   'mg.', 'mm.,, m.p.g.', 'm.p.h.', 'cc.', 'qr.', 'qt.', 'sq.',
                   't.', 'vol.',  'w.', 'wt.']

    sentlist = []
    # controls skipping over non-terminal conditions
    searchstart = 0
    terloc = terpat.search(paragr)
    while terloc:
        isok = True
        if paragr[terloc.start()] == '.':
            if (paragr[terloc.start() - 1].isupper() and
                    paragr[terloc.start() - 2] == ' '):
                        isok = False      # single initials
            else:
                # check abbreviations
                loc = paragr.rfind(' ', 0, terloc.start() - 1)
                if loc > 0:
                    if paragr[loc + 1:terloc.start() + 1].lower() in ABBREV_LIST:
                        isok = False
        if paragr[:terloc.start()].count('(') != paragr[:terloc.start()].count(')'):
            isok = False
        if paragr[:terloc.start()].count('"') % 2 != 0:
            isok = False
        if isok:
            if (len(paragr[:terloc.start()]) > MIN_SENTLENGTH and
                    len(paragr[:terloc.start()]) < MAX_SENTLENGTH):
                sentlist.append(paragr[:terloc.start() + 2])
            paragr = paragr[terloc.end() - 1:]
            searchstart = 0
        else:
            searchstart = terloc.start() + 2

        terloc = terpat.search(paragr, searchstart)

    # add final sentence
    if (len(paragr) > MIN_SENTLENGTH and len(paragr) < MAX_SENTLENGTH):
        sentlist.append(paragr)

    return sentlist
