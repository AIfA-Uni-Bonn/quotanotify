#!/usr/bin/env python3

# Copyright (c) 2015  Phil Gold <phil_g@pobox.com>
#
# changed by: Oliver Cordes 2017-08-22
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.


from config import *
from model import *


#import email.MIMEText
from email.mime.text import MIMEText
import smtplib
import syslog

import subprocess

import jinja2  # http://jinja.pocoo.org

import babel.dates    # nice tool ;-)

#from pysqlite2 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite
from sqlite3 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite

config = load_config_file()
cache = sqlite.connect(config['cache'])
cur = cache.cursor()

jj_env = jinja2.Environment(loader=jinja2.FileSystemLoader('/'))

jj_env.filters['timedelta'] = babel.dates.format_timedelta


def handle_state_change(ai):
    # Take all of the quota objects for the current account, throw out the ones
    # where there's no quota, and sort the rest by severity (worst first) and
    # then by anough other keys to guarantee a stable ordering.
    #quotas_to_sort = [(q.current_state.index * -1, q.last_notify_state, q.last_notify_date, q.filesystem, q.quota_type, q) for q in ai.iter_quotas if q.current_state != QuotaState.no_quota]
    quotas_to_sort = [(q.current_state * -1, q.last_notify_state, q.last_notify_date, q.filesystem, q.quota_type, q) for q in ai.iter_quotas if q.current_state != QuotaState.no_quota]
    quotas = [t[-1] for t in sorted(quotas_to_sort)]

    # See if they're over quota anywhere.
    over_quotas = [q for q in quotas if q.current_state != QuotaState.under_quota]
    # If they're over quota at all, we only care about the areas where they're
    # over.
    if len(over_quotas) > 0:
        quotas = over_quotas

    print( 'UID: ', ai.uid, '(%s)' % ai.realname )
    for i in ai.quotas:
       print( 'Quotas for: ', i )
       print( ' Blocks:' )
       q = ai.quotas[i][0]
       #print( '  Type  :', q.quota_type )
       print( '  Used              :',  q.used )
       print( '  Soft limit        :', q.soft_limit )
       print( '  Hard limit        :', q.hard_limit )
       print( '  current state     :', q.current_state, '(%s)' % sQuotaState[q.current_state] )
       print( '  Grace expires     :', q.grace_expires )
       print( '  last notify date  :', q.last_notify_date )
       print( '  last notify state :', q.last_notify_state, '(%s)' % sQuotaState[q.last_notify_state] )
 

       print( ' Inodes:' )
       q = ai.quotas[i][1]
       #print( '  Type  :', q.quota_type )
       print( '  Used              :',  q.used )
       print( '  Soft limit        :', q.soft_limit )
       print( '  Hard limit        :', q.hard_limit )
       print( '  current state     :', q.current_state, '(%s)' % sQuotaState[q.current_state] )
       print( '  Grace expires     :', q.grace_expires )
       print( '  last notify date  :', q.last_notify_date )
       print( '  last notify state :', q.last_notify_state, '(%s)' % sQuotaState[q.last_notify_state] )

#main 
ai = AccountInfo( int(sys.argv[1]), cur, config)
handle_state_change(ai)
