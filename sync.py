from bs4 import BeautifulSoup
import time, pygame
from os import getcwd
from banner_comment import *
import sqlite3 as lite
import urllib
import urllib.request
import sys
import os
from urllib.parse import urljoin # to support relative urls
import re                    # url checking
import signal                # for handling KeyboardInterrupts
import difflib               # for finding differences between files

#from crawler_config import * # for handling Cralwer configurations
default_config_list = ['http://google.com']

def create_config(config='website-list.txt') :
    yes = ('Y', 'y', 'Yes', 'yes')
    no = ('N', 'n', 'No', 'no')
    usr_inp = ''
    if os.path.isfile(config):
        while usr_inp not in yes and user_inp not in no:
            usr_inp = prompt('%d file found, Overwrite' % config, 2, ' [Y/N] ')
        if usr_inp in no :
            config = prompt('Please enter new config file path', 1)
    try:     
        fp = open(config, 'w')
    except IOError:  
        error('Failed to write config file', 3)
    for i in default_config_list:
        fp.write(i + '\n')
        
def read_config(config="website-list.txt", dr=os.getcwd()) :
    try:
        fp = open(dr + '/' + config, 'r')
        comment_prefixes = ('#', '//')
        url_prefixes     = ('http://', 'https://')
        lines            = fp.readlines()
        web_list         = []    
    
        for line in range(0, len(lines)):
            if lines[line].startswith(comment_prefixes) or len(lines[line]) < 5:
                pass
            elif not lines[line].startswith(url_prefixes):
                error('The configuration file, line: %d is not in correct format, Ignoring this line.' % line_no + 1, 1)
            else:        
                web_list.append(lines[line])
        
    except IOError:
        error('No config file found or config file not readable. Creating one for you', 2)
        create_config(cwd + '/' + config)
        return default_config_list
    return web_list


#from crawler_log import *
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

def log(msg):
    print (bcolors.OKGREEN + 'log: ' + msg + bcolors.ENDC)

#-- Error --
def warning(msg):
    print (bcolors.WARNING + 'Warning: ' + msg + bcolors.ENDC)

def error(msg):
    print (bcolors.WARNING + 'Error: '   + msg + bcolors.ENDC)

def fatal(msg):
    print (bcolors.FAIL    + 'Fatal: '   + msg + bcolors.ENDC)
    exit()

# @param msg      Error/Warning Message
# @param severity How severe the error is
# @return void
def error(msg, severity=1):
    if severity > 3 or severity < 1:
        severity = 3
    options = {
                1 : warning,
                2 : error,
                3 : fatal
              }
    options[severity](msg)

#-- Prompt --

def casual_prompt(msg, possible_ans=''):
    return raw_input(bcolors.WARNING + msg + possible_ans + bcolors.ENDC + ' : ')

def important_prompt(msg, possible_ans=''):
    return raw_input(bcolors.FAIL + msg + possible_ans + bcolors.ENDC + ' : ')

# @param  msg      Prompt Message
# @param  severity How important the question is
# @return user_input
def prompt(msg, severity=1, possible_ans=''):
    if severity > 2 or severity < 1:
        severity = 2
    options = {
                1 : casual_prompt,
                2 : important_prompt
              }
    return options[severity](msg, possible_ans)




#from crawler_db_handling import *
DB_NAME = 'web_monitor.db'

def db_connect():
    con = lite.connect(getcwd() + '/' + DB_NAME)
    c   = con.cursor()
    return c, con

def db_setup_everything(c, con):
    try:
        c.execute('SELECT * from cache')
    except lite.OperationalError:
        log("Creating cache")        
        c.execute("CREATE TABLE cache(url text, content text)")
    con.commit()

def db_get_data(pages, c):
    c.execute('SELECT * from cache')
    log("Loading cache")        
    
    #build up the lists
    while 1:
        try:    
            data = list(c.fetchone())
        except TypeError:
            break
        pages[data[0]] = data[1]


from time import time



def checkUrl(url) :
    # django regex for url validation

    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if re.search(regex, url) == None :
        return 0
    else :
        return 1

def handle_SIGINT(signal, frame) :
    save_all()
    print_result()
    error("Ctrl + C, Detected!\nExiting Now!", 3)

def print_result():
    for changes in web_diff:
        sys.stderr.write('\n' + changes + web_diff[changes])
def save_all():
    for i in pages:
            c.execute("SELECT * from cache where url=\'%s\'" % (i,))
            data = c.fetchone()
            if data != None:
                c.execute("UPDATE cache SET content=\'%s\' where url=\'%s\'" % (pages[i], i,))
            else:
                c.execute("INSERT INTO cache(url, content) values(\'%s\', \'%s\')" % (i, pages[i],))
    con.commit()

banner_comment("Web Scraper")


# Starting of Code
web_list = read_config()

# connect to sqlite database 
directory = os.getcwd() + '/cache'
data     = []
crawled  = []
tracked_pages = []
to_crawl = []
index    = {}
graph    = {}
content  = ''
pages    = {}
web_diff = {}
prefixes = ('http://', 'https://', 'ftp://') # prefixes to check whether the link is an absolute link
c, con = db_connect()
db_setup_everything(c, con)
db_get_data(pages, c)

try:
    os.stat(directory)
except:
    os.makedirs(directory)

#---- main -----
signal.signal(signal.SIGINT, handle_SIGINT)

for entry in pages:
    tracked_pages.append(entry)

for website in web_list:
    to_crawl.append(website.strip())
    for current_url in to_crawl :
        if checkUrl(current_url) == 0 :
            continue
        log("Crawling [%s]" % current_url)
        try :
            req = urllib.request.Request(current_url)
            req.add_header('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11')
            html_page = urllib.request.urlopen(req)
        except urllib.error.URLError as reason :
            error("URLError : %s" % (reason,), 2)
            continue
        except  ValueError :
            error("Invalid URL : %s" % current_url, 2)
            continue
        except KeyboardInterrupt :
            cleanup();
        source      = html_page.read()
        soup        = BeautifulSoup(source, "lxml")
        content     = soup.prettify()
        diff        = ''
        if current_url in tracked_pages:
            # See if there is any difference in the page
            text1 = content.split('\n')
            text1.pop() # remove last newline
            tp   = open(pages[current_url])
            text2 = tp.read().splitlines()
            diff_generator = difflib.unified_diff(text1, text2)
            for differences in diff_generator:
                diff += differences + '\n'
            if diff == '': # no difference == No point of creating another cache file
                continue
            web_diff[current_url] = '\n' + diff
            os.remove(pages[current_url])
        else: # new page added
            web_diff[current_url] = ' -- New Page Added\n'
        temp = directory + "/cache.%.7f.html" % time()
        fp   = open(temp, 'w')
        fp.write(content)
        fp.close()
        anchor_tags = soup('a', limit = 100) # find at max 100 anchor tags from a webpage
        for tag in anchor_tags :
            try:
                url = tag['href']
            except KeyError:
                continue
            if url.startswith('#') :             # Anchor Tags pointing to the same page
                continue
            if url.startswith(prefixes) == True: # We dont want to link to other sites
                continue
            else : # relative link, we'll get a ton of invalid links here , example href='javascript:' etc.
               url = urljoin(current_url, url);
               if checkUrl(current_url) == 0:
                    continue
            if url not in to_crawl and url not in crawled:
                to_crawl.append(url)
                try:
                    # @TODO: Add Graph table
                    graph[current_url].append(url)
                except KeyError:
                    graph[current_url] = [url]
        pages[current_url] = temp
        crawled.append(current_url)
save_all()
#print_result()








'''
#Alarm Notification #


# monitor url
url = 'https://github.com/nihalrai'
# interval of monitor
interval = 3
# alarm audio
alarm_file = 'door_bell.wav'
# repeat times of alarm audio
repeat_time = 3
# text before monitor target
target_flag = '<div id="searchResultCount">'
# length of target text
target_length = 2
# tolerance of target's change (only available when target are integer or float)
target_tolerance = 1


def play_alarm():
    pygame.mixer.init()
    pygame.mixer.music.load(alarm_file)
    pygame.mixer.music.play(repeat_time, 0.0)

def monitor_target(page):
    page = str(page)
    index = page.find(target_flag)
    if index != -1:
        target_pos = index + len(target_flag)
        return page[target_pos:target_pos + target_length]

def isnumber(string):
    if string == None:
        return False
    if int(string).isdigit():
        return True
    else:
        try:
            float(string)
            return True
        except ValueError:
            return False

def equal(origin_value, new_value):
    if isnumber(origin_value) and isnumber(new_value):
        if abs(float(origin_value) - float(new_value)) <= target_tolerance:
            return True
        else:
            return False
    else:
        return origin_value == new_value

def monitor():
    print ('Load url...')
    base_page = urllib.request.urlopen(url).read()

    print ('Finding target...')
    origin_value = monitor_target(base_page)

    print ('Start monitor...')
    while True:
        new_page = urllib.request.urlopen(url).read()
        new_value = monitor_target(new_page)
        if equal(origin_value, new_value):
            print ('Nothing changed -' + time.strftime('%H:%M:%S'))
            time.sleep(interval)
        else:
            print ('Target changed! -' + time.strftime('%H:%M:%S'))
            print (origin_value + ' -> ' + new_value)
            play_alarm()
            if str(input('Keep on monitoring? y/n: ')) == 'y':
                origin_value = new_value
            else:
                exit(0)


if __name__ == "__main__":
    monitor()

'''


# EMAIL part:

'''
import os
import time
from datetime import datetime
from exchangelib import DELEGATE, Account, ServiceAccount, Configuration, NTLM
from plyer import notification
from dotenv import load_dotenv
import pygame

# load credentials
load_dotenv(".credentials")

password = os.environ.get("EXCHANGE_PASSWORD")
username = os.environ.get("EXCHANGE_USERNAME")
outgoing_email_address = os.environ.get("EXCHANGE_OUTGOING_ADDRESS")
soundfile = os.environ.get("NOTIFICATION_SOUND")
exchange_server = os.environ.get("EXCHANGE_SERVER")

if soundfile != "":
    # load a sound file
    pygame.mixer.pre_init()
else:
    print("Skipping loading of soundfile")

print("Initiating connection to exchange...")
# If you want to enable the fault tolerance, create credentials as a service account instead:
credentials = ServiceAccount(username=username, password=password)

# Set up a target account and do an autodiscover lookup to find the target EWS endpoint:
account = Account(primary_smtp_address=outgoing_email_address, credentials=credentials,
                  autodiscover=True, access_type=DELEGATE)

config = Configuration(server=exchange_server, credentials=credentials, auth_type=NTLM)

last_number_of_emails = account.inbox.unread_count

print("Waiting for emails... Press CTRL+C to stop")

try:
    while True:
        # Update the counters
        account.inbox.refresh()
        cur_number_of_emails = account.inbox.unread_count

        if cur_number_of_emails > last_number_of_emails:
            # we got a new mail, get the last view messages
            diff = cur_number_of_emails - last_number_of_emails
            bodytext = ""
            for item in account.inbox.all().order_by('-datetime_received')[:diff]:
                bodytext += "{folder}: {name} ({email}): {subject}\n".format(
                    name=item.author.name, email=item.author.email_address, subject=item.subject, folder=item.folder.name
                )

            print("{dt}: {n} new emails".format(dt=datetime.now(), n=diff))

            # play a sound
            if soundfile != "":
                pygame.mixer.init()
                pygame.mixer.music.load(soundfile)  # can be any other format
                pygame.mixer.music.play()
            # show notification
            notification.notify(title="{n} new emails".format(n=diff), message=bodytext)
        else:
            if not pygame.mixer.get_busy():
                # after playback, pause the mixer
                pygame.mixer.quit()

        last_number_of_emails = cur_number_of_emails
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping.")
'''




