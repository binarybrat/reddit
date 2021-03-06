#/u/GoldenSights
import datetime
import json
import os
import praw
import random
import string
import sqlite3
import subprocess
import sys
import time
import tkinter
import traceback


'''USER CONFIGURATION'''
USERAGENT = '''
/u/GoldenSights SubredditBirthdays data collection:
Gathering the creation dates of subreddits for visualization.
More at https://github.com/voussoir/reddit/tree/master/SubredditBirthdays
'''.replace('\n', ' ')
APP_ID = ""
APP_SECRET = ""
APP_URI = ""
APP_REFRESH = ""
# https://www.reddit.com/comments/3cm1p8/how_to_make_your_bot_use_oauth2/
# This is a short description of what the bot does.
# For example "/u/GoldenSights' Newsletter bot"

WAIT = 20
# This is how many seconds you will wait between cycles.
# The bot is completely inactive during this time.

LOWERBOUND_STR = '2qh0j'
LOWERBOUND_INT = 4594339

MEMBERFORMAT = '_idstr_, _human_, _nsfw_, _name__spacer__subscribers_'

'''All done!'''

try:
    import bot
    #USERAGENT = bot.aG
    APP_ID = bot.oG_id
    APP_SECRET = bot.oG_secret
    APP_URI = bot.oG_uri
    APP_REFRESH = bot.oG_scopes['all']
except ImportError:
    pass


WAITS = str(WAIT)

GOODCHARS = string.ascii_letters + string.digits + '_'

sql = sqlite3.connect('C:/git/reddit/subredditbirthdays/sql.db')
cur = sql.cursor()
cur2 = sql.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS subreddits(
    idint INT,
    idstr TEXT,
    created INT,
    human TEXT,
    name TEXT,
    nsfw INT,
    subscribers INT,
    jumble INT,
    subreddit_type INT,
    submission_type INT)
    ''')
cur.execute('CREATE INDEX IF NOT EXISTS subindex ON subreddits(idint)')
sql.commit()
#  0 - idint
#  1 - idstr
#  2 - created
#  3 - human
#  4 - name
#  5 - nsfw
#  6 - subscribers
#  7 - jumble
#  8 - subreddit type
#  9 - submission type
SQL_COLUMNCOUNT = 10
SQL_IDINT = 0
SQL_IDSTR = 1
SQL_CREATED = 2
SQL_HUMAN = 3
SQL_NAME = 4
SQL_NSFW = 5
SQL_SUBSCRIBERS = 6
SQL_JUMBLE = 7
SQL_SUBREDDIT_TYPE = 8
SQL_SUBMISSION_TYPE = 9

print('Logging in.')
r = praw.Reddit(USERAGENT)
r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
r.refresh_access_information(APP_REFRESH)

olds = 0
noinfolist = []
errormess = None
monthnumbers = {
    "Jan":"01",
    "Feb":"02",
    "Mar":"03",
    "Apr":"04",
    "May":"05",
    "Jun":"06",
    "Jul":"07",
    "Aug":"08",
    "Sep":"09",
    "Oct":"10",
    "Nov":"11",
    "Dec":"12"
}

SUBREDDIT_TYPE = {
    'public':0,
    'restricted':1,
    'private':2,
    'archived':3,
    None:4,
    'employees_only':5,
    'gold_restricted':6,
    'gold_only':7
}
SUBMISSION_TYPE = {
    'any':0,
    'link':1,
    'self':2,
    None:3
}


def human(timestamp):
    day = datetime.datetime.utcfromtimestamp(timestamp)
    human = datetime.datetime.strftime(day, "%b %d %Y %H:%M:%S UTC")
    return human

def now():
    return datetime.datetime.now(datetime.timezone.utc).timestamp()

def processi(sr, doupdates=True, enablekilling=False):
    global olds
    if 't5_' not in sr:
        sr = 't5_' + sr
    cur.execute('SELECT * FROM subreddits WHERE idint=?', [b36(sr[3:])])
    if not cur.fetchone() or doupdates==True:
        sro = r.get_info(thing_id=sr)
        try:
            sro.id
            process(sro)
        except AttributeError:
            print('Could not fetch subreddit')
            if enablekilling:
                i = input('Kill?\n> ')
                if i.lower() == 'y':
                    kill(sr[3:])
    else:
        olds += 1

def process(sr, database="subreddits", delaysaving=False, doupdates=True,
            isjumbled=False, nosave=False):
    global olds
    subs = []

    if type(sr) == str:
        for splitted in sr.split(','):
            splitted = splitted.replace(' ', '')
            if doupdates==False:
                cur.execute('SELECT * FROM subreddits WHERE LOWER(name)=?',
                            [splitted.lower()])
                if not cur.fetchone():
                    sr = r.get_subreddit(splitted)
                    subs.append(sr)
                else:
                    olds += 1
                    pass
            else:
                sr = r.get_subreddit(splitted)
                subs.append(sr)

    elif type(sr) in [praw.objects.Submission, praw.objects.Comment]:
        sr = sr.subreddit
        subs.append(sr)

    else:
        subs.append(sr)

    for sub in subs:
        try:
            idint = b36(sub.id)
            cur.execute('SELECT * FROM subreddits WHERE idint=?', [idint])
            f = cur.fetchone()
            if not f:
                h = human(sub.created_utc)
                isnsfw = 1 if sub.over18 else 0
                subscribers = sub.subscribers if sub.subscribers else 0
                isjumbled = 1 if isjumbled else 0
                print('New: %s : %s : %s : %s : %d' % (
                      sub.id, h, isnsfw, sub.display_name, subscribers))
                subreddit_type = SUBREDDIT_TYPE[sub.subreddit_type]
                submission_type = SUBMISSION_TYPE[sub.submission_type]
                data = ['.'] * SQL_COLUMNCOUNT
                data[SQL_IDINT] = idint
                data[SQL_IDSTR] = sub.id
                data[SQL_CREATED] = sub.created_utc
                data[SQL_HUMAN] = h
                data[SQL_NSFW] = isnsfw
                data[SQL_NAME] = sub.display_name
                data[SQL_SUBSCRIBERS] = subscribers
                data[SQL_JUMBLE] = isjumbled
                data[SQL_SUBREDDIT_TYPE] = subreddit_type
                data[SQL_SUBMISSION_TYPE] = submission_type
                cur.execute('''
                    INSERT INTO subreddits VALUES(
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
            elif doupdates:
                if sub.subscribers is not None:
                    subscribers = sub.subscribers
                else:
                    subscribers = 0

                h = human(sub.created_utc)

                isnsfw = 1 if sub.over18 else 0
                if isjumbled is True or int(f[SQL_JUMBLE]) == 1:
                    isjumbled = 1
                else:
                    isjumbled = 0

                subreddit_type = SUBREDDIT_TYPE[sub.subreddit_type]
                submission_type = SUBMISSION_TYPE[sub.submission_type]

                oldsubs = f[SQL_SUBSCRIBERS]
                subscriberdiff = subscribers - oldsubs
                if subscribers == 0 and oldsubs > 2 and subreddit_type != SUBREDDIT_TYPE['private']:
                    print('SUSPICIOUS %s' % sub.display_name)
                    cur.execute('INSERT INTO suspicious VALUES(?, ?, ?, ?)', [idint, sub.id, sub.display_name, oldsubs])
                print('Upd: %s : %s : %s : %s : %d (%d)' % (sub.id, h, isnsfw,
                      sub.display_name, subscribers, subscriberdiff))
                cur.execute('''
                    UPDATE subreddits SET
                    subscribers=?,
                    jumble=?,
                    subreddit_type=?,
                    submission_type=?
                    WHERE idint=?
                    ''',
                    [subscribers, isjumbled, subreddit_type,
                     submission_type, idint])
                olds += 1
            else:
                olds += 1
            if not delaysaving and not nosave:
                sql.commit()
        except praw.errors.HTTPException:
            print('HTTPError:', sub)
    if not nosave:          
        sql.commit()


def chunklist(inputlist, chunksize):
    if len(inputlist) < chunksize:
        return [inputlist]
    else:
        outputlist = []
        while len(inputlist) > 0:
            outputlist.append(inputlist[:chunksize])
            inputlist = inputlist[chunksize:]
        return outputlist

def processmega(srinput, isrealname=False, chunksize=100, docrash=False,
                delaysaving=False, doupdates=True, nosave=False):
    global olds
    global noinfolist
    #This is the new standard in sr processing
    #Other methods will be deprecated
    #Heil
    if type(srinput) == str:
        srinput = srinput.replace(' ', '')
        srinput = srinput.split(',')

    if isrealname is False:
        remaining = len(srinput)
        for x in range(len(srinput)):
            if 't5_' not in srinput[x]:
                srinput[x] = 't5_' + srinput[x]
        srinput = chunklist(srinput, chunksize)
        for subset in srinput:
            try:
                print(subset[0] + ' - ' + subset[-1], remaining)
                subreddits = r.get_info(thing_id=subset)
                try:
                    for sub in subreddits:
                        process(sub, delaysaving=delaysaving, doupdates=doupdates, nosave=nosave)
                except TypeError:
                    noinfolist = subset[:]
                    if len(noinfolist) == 1:
                        print('Received no info. See variable `noinfolist`')
                    else:
                        for item in noinfolist:
                            processmega([item])

                remaining -= len(subset)
            except praw.errors.HTTPException as e:
                print(e)
                print(vars(e))
                if docrash:
                    raise Exception("I've been commanded to crash")
    else:
        for subname in srinput:
            process(subname)


def processrand(count, doublecheck=False, sleepy=0, delaysaving=False, doupdates=True):
    """
    Gets random IDs between a known lower bound and the newest collection
    *int count= How many you want
    bool doublecheck= Should it reroll duplicates before running
    int sleepy= Used to sleep longer than the reqd 2 seconds
    """
    global olds
    olds = 0
    lower = LOWERBOUND_INT

    cur.execute('SELECT * FROM subreddits ORDER BY idint DESC LIMIT 1')
    upper = cur.fetchone()[SQL_IDSTR]
    print('<' + b36(lower).lower() + ',',  upper + '>', end=', ')
    upper = b36(upper)
    totalpossible = upper-lower
    print(totalpossible, 'possible')
    rands = []
    if doublecheck:
        allids = [x[SQL_IDSTR] for x in fetched]
    for x in range(count):
        rand = random.randint(lower, upper)
        rand = b36(rand).lower()
        if doublecheck:
            while rand in allids or rand in rands:
                if rand in allids:
                    print('Old:', rand, 'Rerolling: in allid')
                else:
                    print('Old:', rand, 'Rerolling: in rands')
                rand = random.randint(lower, upper)
                rand = b36(rand).lower()
                olds += 1
        rands.append(rand)

    rands.sort()
    processmega(rands, delaysaving=delaysaving, doupdates=doupdates)

    print('Rejected', olds)

def kill(sr):
    data = ['.'] * SQL_COLUMNCOUNT
    data[SQL_IDINT] = b36(sr)
    data[SQL_IDSTR] = sr
    data[SQL_CREATED] = 0
    data[SQL_HUMAN] = None
    data[SQL_NSFW] = None
    data[SQL_NAME] = None
    data[SQL_SUBSCRIBERS] = None
    data[SQL_JUMBLE] = 0
    data[SQL_SUBREDDIT_TYPE] = None
    data[SQL_SUBMISSION_TYPE] = None
    cur.execute('INSERT INTO subreddits VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
    sql.commit()

def fetchgenerator(cur):
    while True:
        fetch = cur.fetchone()
        if fetch is None:
            break
        yield fetch

def datetimedict(outputdict, timestamp, strftime):
    dtd = datetime.datetime.strftime(timestamp, strftime) # 01
    outputdict[dtd] = outputdict.get(dtd, 0) + 1

def show():
    file_all_time = open('show\\all-time.txt', 'w')
    file_all_name = open('show\\all-name.txt', 'w')
    file_all_subscribers = open('show\\all-subscribers.txt', 'w')
    file_dirty_time = open('show\\dirty-time.txt', 'w')
    file_dirty_name = open('show\\dirty-name.txt', 'w')
    file_dirty_subscribers = open('show\\dirty-subscribers.txt', 'w')
    file_jumble_sfw = open('show\\jumble.txt', 'w')
    file_jumble_nsfw = open('show\\jumble-nsfw.txt', 'w')
    file_duplicates = open('show\\duplicates.txt', 'w')
    file_missing = open('show\\missing.txt', 'w')
    file_stats = open('show\\statistics.txt', 'w')
    file_readme = open('README.md', 'r')

    cur.execute('SELECT COUNT(idint) FROM subreddits WHERE created != 0')
    itemcount_valid = cur.fetchone()[0]
    itemcount_nsfw = 0
    print(itemcount_valid, 'subreddits')

    print('Writing time files.')
    cur.execute('SELECT * FROM subreddits WHERE created !=0 ORDER BY created ASC')
    for item in fetchgenerator(cur):
        itemf = memberformat(item)
        print(itemf, file=file_all_time)
        if int(item[SQL_NSFW]) == 1:
            print(itemf, file=file_dirty_time)
            itemcount_nsfw += 1
    file_all_time.close()
    file_dirty_time.close()

    print('Writing name files and duplicates.')
    previousitem = None
    inprogress = False
    cur.execute('SELECT * FROM subreddits WHERE created != 0 ORDER BY LOWER(name) ASC')
    for item in fetchgenerator(cur):
        if previousitem is not None and item[SQL_NAME] == previousitem[SQL_NAME]:
            print(memberformat(previousitem), file=file_duplicates)
            inprogress = True
        elif inprogress:
            print(memberformat(previousitem), file=file_duplicates)
            inprogress = False
        previousitem = item

        itemf = memberformat(item)
        print(itemf, file=file_all_name)
        if int(item[SQL_NSFW]) == 1:
            print(itemf, file=file_dirty_name)
    file_duplicates.close()
    file_all_name.close()
    file_dirty_name.close()

    print('Writing subscriber files.')
    rank_all = 1
    rank_nsfw = 1
    cur.execute('SELECT * FROM subreddits WHERE created != 0 ORDER BY subscribers DESC')
    for item in fetchgenerator(cur):
        if rank_all <= 20000:
            rankstr = commapadding(rank_all, ' ', 9)
            rank_all += 1
        else:
            rankstr = ''
        itemf = memberformat(item)
        print(itemf+rankstr, file=file_all_subscribers)
        if int(item[SQL_NSFW]) == 1:
            if rank_nsfw <= 20000:
                rankstr = commapadding(rank_nsfw, ' ', 9)
                rank_nsfw += 1
            else:
                rankstr = ''
            print(itemf+rankstr, file=file_dirty_subscribers)
    file_all_subscribers.close()
    file_dirty_subscribers.close()

    print('Writing jumble.')
    cur.execute('SELECT * FROM subreddits WHERE jumble == 1 ORDER BY subscribers DESC')
    for item in fetchgenerator(cur):
        itemf = memberformat(item)
        if int(item[SQL_NSFW]) == 0:
            print(itemf, file=file_jumble_sfw)
        else:
            print(itemf, file=file_jumble_nsfw)
    file_jumble_sfw.close()
    file_jumble_nsfw.close()

    print('Writing missing.')
    cur.execute('SELECT * FROM subreddits WHERE created == 0 ORDER BY idint ASC')
    for item in fetchgenerator(cur):
        print(item[SQL_IDSTR], file=file_missing)
    file_missing.close()


    print('Writing statistics.')
    headline = 'Collected {0:,} subreddits\n'.format(itemcount_valid)
    statisticoutput = headline + '\n\n'
    statisticoutput += ' SFW: {0:,}\n'.format(itemcount_valid - itemcount_nsfw)
    statisticoutput += 'NSFW: {0:,}\n\n\n'.format(itemcount_nsfw)

    cur.execute('SELECT * FROM subreddits WHERE created != 0 ORDER BY created DESC limit 20000')
    last20k = cur.fetchall()
    timediff = last20k[0][SQL_CREATED] - last20k[-1][SQL_CREATED]
    statisticoutput += '%.2f subs are created each hour\n' % (20000 / (timediff/3600))
    statisticoutput += '%.2f subs are created each day\n\n\n' % (20000 / (timediff/86400))


    ################################
    # Breakdown by time period
    # hour of day, day of week, day of month, month of year, month-year, year
    hoddict = {}
    dowdict = {}
    domdict = {}
    moydict = {}
    myrdict = {}
    yerdict = {}
    cur.execute('SELECT * FROM subreddits WHERE created != 0')
    print('    performing time breakdown')
    for item in fetchgenerator(cur):
        dt = datetime.datetime.utcfromtimestamp(item[SQL_CREATED])

        datetimedict(hoddict, dt, '%H') # 01
        datetimedict(dowdict, dt, '%A') # Monday
        datetimedict(domdict, dt, '%d') # 01
        datetimedict(moydict, dt, '%B') # January
        datetimedict(myrdict, dt, '%b%Y') # Jan2015
        datetimedict(yerdict, dt, '%Y') # 2015

    print('    forming columns')
    plotnum = 0
    modes = [None, 'day', None, 'month', None, 'monthyear']
    dicts = [hoddict, dowdict, domdict, moydict, yerdict, myrdict]
    for index in range(len(dicts)):
        d = dicts[index]
        dkeys_primary = list(d.keys())
        dkeys_primary.sort(key=d.get)
        dkeys_secondary = specialsort(dkeys_primary, modes[index])
        dvals = [d[x] for x in dkeys_secondary]

        for keyindex in range(len(dkeys_primary)):
            key = dkeys_primary[keyindex]
            val = d[key]
            val = '{0:,}'.format(val)
            spacer = 34 - (len(key) + len(val))
            spacer = '.' * spacer
            statisticoutput += key + spacer + val
            statisticoutput += ' ' * 8

            key = dkeys_secondary[keyindex]
            val = d[key]
            val = '{0:,}'.format(val)
            spacer = 34 - (len(key) + len(val))
            spacer = '.' * spacer
            statisticoutput += key + spacer + val
            statisticoutput +=  '\n'
        statisticoutput += '\n'

        plotbars(str(plotnum), [dkeys_secondary, dvals],
                 colormid='#43443a', forcezero=True)
        plotnum += 1
        if d is myrdict:
            plotbars(str(plotnum), [dkeys_secondary[-15:], dvals[-15:]],
                     colorbg="#272822", colorfg="#000",
                     colormid="#43443a", forcezero=True)
            plotnum += 1
    #
    # Breakdown by time period
    ################################
    print(statisticoutput, file=file_stats)
    file_stats.close()

    print('Updating Readme')
    readmelines = file_readme.readlines()
    file_readme.close()
    readmelines[3] = '#####' + headline
    readmelines[5] = '#####[Today\'s jumble](http://reddit.com/r/%s)\n' % jumble(doreturn=True)[0]
    file_readme = open('README.md', 'w')
    file_readme.write(''.join(readmelines))
    file_readme.close()

    time.sleep(2)
    x = subprocess.call('PNGCREATOR.bat', shell=True, cwd='spooky')
    print()

def memberformat(member, spacerchar='.'):
    idstr = commapadding(member[SQL_IDSTR], ' ', 5, forcestring=True)
    human = member[SQL_HUMAN]
    nsfw = member[SQL_NSFW]
    name = member[SQL_NAME]
    subscribers = '{0:,}'.format(member[SQL_SUBSCRIBERS])
    spacer = 35 - (len(name) + len(subscribers))
    spacer = spacerchar * spacer
    member = MEMBERFORMAT
    member = member.replace('_idstr_', idstr)
    member = member.replace('_human_', human)
    member = member.replace('_nsfw_', str(nsfw))
    member = member.replace('_name_', name)
    member = member.replace('_spacer_', spacer)
    member = member.replace('_subscribers_', subscribers)
    return member

def commapadding(s, spacer, spaced, left=True, forcestring=False):
    '''
    Given a number 's', make it comma-delimted and then
    pad it on the left or right using character 'spacer'
    so the whole string is of length 'spaced'

    Providing a non-numerical string will skip straight
    to padding
    '''
    if not forcestring:
        try:
            s = int(s)
            s = '{0:,}'.format(s)
        except:
            pass

    spacer = spacer * (spaced - len(s))
    if left:
        return spacer + s
    return s + spacer

def dictadding(targetdict, item):
    if item not in targetdict:
        targetdict[item] = 1
    else:
        targetdict[item] = targetdict[item] + 1
    return targetdict

def specialsort(inlist, mode=None):
    if mode == 'month':
        return ['January', 'February', 'March', \
                'April', 'May', 'June', 'July', \
                'August', 'September', 'October', \
                'November', 'December']
    if mode == 'day':
        return ['Sunday', 'Monday', 'Tuesday', \
                'Wednesday', 'Thursday', 'Friday', \
                'Saturday']
    if mode == 'monthyear':
        td = {}
        for item in inlist:
            nitem = item
            nitem = item.replace(item[:3], monthnumbers[item[:3]])
            nitem = nitem[3:] + nitem[:3]
            td[item] = nitem
        tdkeys = list(td.keys())
        #print(td)
        tdkeys.sort(key=td.get)
        #print(tdkeys)
        return tdkeys
    if mode is None:
        return sorted(inlist)


def shown(startinglist, header, fileobj, nsfwmode=2):
    """
    Creating Show files with filters
    *lst startinglist= the unfiltered list
    *str header= the header at the top of the file
    *obj fileobj= the file object to write to
    *int nsfwmode=
      0 - Clean only
      1 - Dirty only
      2 - All
    """

    nsfwyes = []
    nsfwno = []
    nsfwq = []
    for item in startinglist:
        if item[3] == '1':
            nsfwyes.append(item)
        elif item[3] == '?':
            nsfwq.append(item)
        else:
            nsfwno.append(item)
    print(header, file=fileobj)
    if nsfwmode == 0 or nsfwmode == 2:
        for member in nsfwno:
            print(memberformat(member), file=fileobj)
        print('\n' + ('#'*64 + '\n')*5, file=fileobj)

    if nsfwmode == 1 or nsfwmode == 2:
        for member in nsfwyes:
            print(memberformat(member), file=fileobj)
        print('\n' + ('#'*64 + '\n')*5, file=fileobj)

    if nsfwmode == 2:
        for member in nsfwq:
            print(memberformat(member), file=fileobj)


def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int)):
        raise TypeError('number must be an integer')
    base36 = ''
    sign = ''
    if number < 0:
        sign = '-'
        number = -number
    if 0 <= number < len(alphabet):
        return sign + alphabet[number]
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
    return sign + base36

def base36decode(number):
    return int(number, 36)

def b36(i):
    if type(i) == int:
        return base36encode(i)
    if type(i) == str:
        return base36decode(i)

def search(query="", casesense=False, filterout=[], subscribers=0, nsfwmode=2, doreturn=False, sort=None):
    """
    Search for a subreddit by name
    *str query = The search query
        "query"    = results where "query" is in the name
        "*query"   = results where "query" is at the end of the name
        "query*"   = results where "query" is at the beginning of the name
        "*query*" = results where "query" is in the middle of the name
    bool casesense = is the search case sensitive
    list filterout = [list, of, words] to omit from search. Follows casesense
    int subscribers = minimum number of subscribers
    int nsfwmode =
      0 - Clean only
      1 - Dirty only
      2 - All
    int sort = The integer representing the sql column to sort by. Defaults
               to no sort.
    """
    querys = ''.join([c for c in query if c in GOODCHARS])
    queryx = '%%%s%%' % querys
    if '!' in query:
        cur.execute('SELECT * FROM subreddits WHERE name LIKE ?', [querys])
        return cur.fetchone()
    if nsfwmode in [0,1]:
        cur.execute('SELECT * FROM subreddits WHERE name LIKE ? AND subscribers > ? AND nsfw=?', [queryx, subscribers, nsfwmode])
    else:
        cur.execute('SELECT * FROM subreddits WHERE name LIKE ? AND subscribers > ?', [queryx, subscribers])

    results = []
    if casesense is False:
        querys = querys.lower()
        filterout = [x.lower() for x in filterout]

    if '*' in query:
        positional = True
        front = query[-1] == '*'
        back = query[0] == '*'
        if front and back:
            mid = True
            front = False
            back = False
        else:
            mid = False
    else:
        positional = False

    lenq = len(querys)
    for item in fetchgenerator(cur):
        name = item[SQL_NAME]
        if casesense is False:
            name = name.lower()
        if querys not in name:
            #print('%s not in %s' % (querys, name))
            continue
        if (positional and front) and (name[:lenq] != querys):
            #print('%s not front %s (%s)' % (querys, name, name[:lenq]))
            continue
        if (positional and back) and (name[-lenq:] != querys):
            #print('%s not back %s (%s)' % (querys, name, name[-lenq:]))
            continue
        if (positional and mid) and (querys not in name[1:-1]):
            #print('%s not mid %s (%s)' % (querys, name, name[1:-1]))
            continue
        if any(filters in name for filters in filterout):
            #print('%s not filter %s' % (querys, name))
            continue
        results.append(item)

    if sort is not None:
        results.sort(key=lambda x: x[sort], reverse=True)
    if doreturn is True:
        return results
    else:
        for item in results:
            print(item)

def cls():
    os.system('cls')

def findwrong():
    cur.execute('SELECT * FROM subreddits WHERE NAME!=?', ['?'])
    fetch = cur.fetchall()
    fetch.sort(key=lambda x: x[SQL_IDINT])
    #sorted by ID
    fetch = fetch[25:]
    
    pos = 0
    l = []

    while pos < len(fetch)-5:
        if fetch[pos][1] > fetch[pos+1][1]:
            l.append(str(fetch[pos-1]))
            l.append(str(fetch[pos]))
            l.append(str(fetch[pos+1]) + "\n")
        pos += 1

    for x in l:
        print(x)

def processjumble(count, nsfw=False):
    for x in range(count):
        sub = r.get_random_subreddit(nsfw=nsfw)
        process(sub, isjumbled=True, doupdates=True)
        sql.commit()


def jumble(count=20, doreturn=False, nsfw=False):
    nsfw = 1 if nsfw else 0
    cur.execute('SELECT * FROM subreddits WHERE jumble=1 AND nsfw=? ORDER BY RANDOM() LIMIT ?', [nsfw, count])
    fetch = cur.fetchall()
    random.shuffle(fetch)
    fetch = fetch[:count]
    fetch = [f[:-1] for f in fetch]
    fetchstr = [i[SQL_NAME] for i in fetch]
    fetchstr = '+'.join(fetchstr)
    output = [fetchstr, fetch]
    if doreturn:
        return output
    print(output[0])
    for x in output[1]:
        print(str(x).replace("'", ''))

def modsfromid(subid):
    if 't5_' not in subid:
        subid = 't5_' + subid
    sub = r.get_info(thing_id=subid)
    mods = list(sub.get_moderators())
    for m in mods:
        print(m)
    return mods

def modernize():
    cur.execute('SELECT * FROM subreddits ORDER BY created DESC LIMIT 1')
    finalitem = cur.fetchone()
    print('Current final item:')
    print(finalitem[SQL_IDSTR], finalitem[SQL_HUMAN], finalitem[SQL_NAME])
    finalid = finalitem[SQL_IDINT]

    print('Newest item:')
    newestid = get_newest_sub()
    print(newestid)
    newestid = b36(newestid)
    

    modernlist = []
    for x in range(finalid, newestid):
        modernlist.append(b36(x).lower())
    processmega(modernlist)

def rounded(x, rounding=100):
    return int(round(x/rounding)) * rounding

def plotbars(title, inputdata, colorbg="#fff", colorfg="#000", colormid="#888", forcezero=False):
    """Create postscript vectors of data

    title = Name of the file without extension

    inputdata = A list of two lists. First list has the x axis labels, second list
    has the y axis data. x label 14 coresponds to y datum 14, etc.
    """
    print('    Printing', title)
    t=tkinter.Tk()

    canvas = tkinter.Canvas(t, width=3840, height=2160, bg=colorbg)
    canvas.pack()
    canvas.create_line(430, 250, 430,1755, width=10, fill=colorfg)
    #Y axis
    canvas.create_line(430,1750, 3590,1750, width=10, fill=colorfg)
    #X axis

    dkeys = inputdata[0]
    dvals = inputdata[1]
    entrycount = len(dkeys)
    availablespace = 3140
    availableheight= 1490
    entrywidth = availablespace / entrycount
    #print(dkeys, dvals, "Width:", entrywidth)

    smallest = min(dvals)
    bottom = int(smallest*0.75) - 5
    bottom = 0 if bottom < 8 else rounded(bottom, 10)
    if forcezero:
        bottom = 0
    largest = max(dvals)
    top = int(largest + (largest/5))
    top = rounded(top, 10)
    print(bottom,top)
    span = top-bottom
    perpixel = span/availableheight

    curx = 445
    cury = 1735

    labelx = 420
    labely = 255
    #canvas.create_text(labelx, labely, text=str(top), font=("Consolas", 72), anchor="e")
    labelspan = 130#(1735-255)/10
    canvas.create_text(175, 100, text="Subreddits created", font=("Consolas", 72), anchor="w", fill=colorfg)
    for x in range(12):
        value = int(top -((labely - 245) * perpixel))
        value = rounded(value, 10)
        value = '{0:,}'.format(value)
        canvas.create_text(labelx, labely, text=value, font=("Consolas", 72), anchor="e", fill=colorfg)
        canvas.create_line(430, labely, 3590, labely, width=2, fill=colormid)
        labely += labelspan

    for entrypos in range(entrycount):
        entry = dkeys[entrypos]
        entryvalue = dvals[entrypos]
        entryx0 = curx + 10
        entryx1 = entryx0 + (entrywidth-10)
        curx += entrywidth

        entryy0 = cury
        entryy1 = entryvalue - bottom
        entryy1 = entryy1/perpixel
        #entryy1 -= bottom
        #entryy1 /= perpixel
        entryy1 = entryy0 - entryy1
        #print(perpixel, entryy1)
        #print(entry, entryx0,entryy0, entryx1, entryy1)
        canvas.create_rectangle(entryx0,entryy0, entryx1,entryy1, fill=colorfg, outline=colorfg)

        font0x = entryx0 + (entrywidth / 2)
        font0y = entryy1 - 5

        font1y = 1760

        entryvalue = round(entryvalue)
        fontsize0 = len(str(entryvalue)) 
        fontsize0 = round(entrywidth / fontsize0) + 3
        fontsize0 = 100 if fontsize0 > 100 else fontsize0
        fontsize1 = len(str(entry))
        fontsize1 = round(1.5* entrywidth / fontsize1) + 5
        fontsize1 = 60 if fontsize1 > 60 else fontsize1
        canvas.create_text(font0x, font0y, text=entryvalue, font=("Consolas", fontsize0), anchor="s", fill=colorfg)
        canvas.create_text(font0x, font1y, text=entry, font=("Consolas", fontsize1), anchor="n", fill=colorfg)
        canvas.update()
    print('    Done')
    canvas.postscript(file='spooky\\' +title+".ps", width=3840, height=2160)
    t.geometry("1x1+1+1")
    t.update()
    t.destroy()

def completesweep(shuffle=False, sleepy=0, query=None):
    if shuffle is True:
        cur2.execute('SELECT idstr FROM subreddits WHERE created > 0 ORDER BY RANDOM()')
    elif query is None:
        cur2.execute('SELECT idstr FROM subreddits WHERE created > 0')
    elif query == 'subscribers':
        cur2.execute('SELECT idstr FROM subreddits WHERE created > 0 ORDER BY subscribers DESC')
    elif query == 'restricted':
        cur2.execute('SELECT idstr FROM subreddits WHERE created > 0 AND subreddit_type != 0 ORDER BY subscribers DESC')
    else:
        cur2.execute(query)

    try:
        while True:
            hundred = [cur2.fetchone() for x in range(100)]
            while None in hundred:
                hundred.remove(None)
            if len(hundred) == 0:
                break
            # h[0] because the selection query calls for idstr
            # This is not a mistake
            hundred = [h[0] for h in hundred]
            processmega(hundred, nosave=True)
            time.sleep(sleepy)
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    sql.commit()

def get_newest_sub():
    brandnewest = list(r.get_new_subreddits(limit=1))[0]
    return brandnewest.id

def execit(*args, **kwargs):
    exec(*args, **kwargs)
