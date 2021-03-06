import bot
import datetime
import praw
import warnings
warnings.filterwarnings('ignore')
print('logging in')
r=bot.oG()

IGNORE_DELETED_AUTHORS = True
SAVE_TO_TXT = 'results_%Y%b%d.txt'

MINIMUM_AGE = 60 * 60 * 24
MAXIMUM_AGE = 7 * 60 * 60 * 24

now = datetime.datetime.now(datetime.timezone.utc)
nowstamp = now.timestamp()
outfile = now.strftime(SAVE_TO_TXT)

print('getting new')
subreddit = r.get_subreddit('excel')
new = subreddit.get_new(limit=1000)
results = []
old_in_a_row = 0
for submissionindex, submission in enumerate(new):
    print('Checked %d submissions\r' % (submissionindex), end='')
    age = nowstamp - submission.created_utc
    if age < MINIMUM_AGE:
        continue

    if age > MAXIMUM_AGE:
        old_in_a_row += 1
        if old_in_a_row >= 10:
            break
        continue
    old_in_a_row = 0

    if IGNORE_DELETED_AUTHORS and submission.author is None:
        continue

    if submission.link_flair_text not in ['unsolved', 'Waiting on OP']:
        continue

    # make sure to perform this part AS LATE AS POSSIBLE to avoid
    # api calls.
    submission.replace_more_comments(limit=None, threshold=1)
    total = praw.helpers.flatten_tree(submission.comments)
    submission.ctotal = total
    
    if submission.link_flair_text == 'unsolved' and len(total) != 0:
        continue

    if submission.link_flair_text == 'Waiting on OP' and len(total) != 1:
        continue

    results.append(submission)
print()
results.sort(key=lambda s: (s.created_utc, s.num_comments))
for (submissionindex, submission) in enumerate(results):
    author = '/u/'+submission.author.name if submission.author else '[deleted]'
    timeformat = datetime.datetime.utcfromtimestamp(submission.created_utc)
    timeformat = timeformat.strftime('%d %b %Y %H:%M:%S')

    formatted = '[%s](%s) | %s | %s | %d' % (submission.title, submission.short_link, author, timeformat, len(submission.ctotal))
    results[submissionindex] = formatted

table = 'title | author | time | comments\n'
table += ':- | :- | -: | -:\n'
table += '\n'.join(results)

outfile = open(outfile, 'w')
print(table, file=outfile)
outfile.close()
