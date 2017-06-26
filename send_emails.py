#!/usr/bin/env python3

# Copyright (c) 2015  Phil Gold <phil_g@pobox.com>
#
# changed by: Oliver Cordes 2017-06-28
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

import jinja2  # http://jinja.pocoo.org

import babel.dates    # nice tool ;-)

#from pysqlite2 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite
from sqlite3 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite

config = load_config_file()
cache = sqlite.connect(config['cache'])
cur = cache.cursor()

jj_env = jinja2.Environment(loader=jinja2.FileSystemLoader('/'))

jj_env.filters['timedelta'] = babel.dates.format_timedelta

def send_email(to, subject, body):
    to_addr = '%s@%s' % (to, config['domain'])
    if '@' in config['from_address']:
        from_addr = config['from_address']
    else:
        from_addr = '%s@%s' % (config['from_address'], config['domain'])
    #msg = email.MIMEText.MIMEText(body)
    msg = MIMEText(body)
    msg['subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    if config['reply_to']:
        msg['Reply-To'] = config['reply_to']
    s = smtplib.SMTP(config['smtp_host'])
    s.sendmail(from_addr, to_addr, msg.as_string())
    s.quit()

def send_email_p(quotas):
    if len(quotas) == 0:
        return False

    # If any state has gotten worse, send an email.
    for q in quotas:
        if q.current_state > q.last_notify_state and \
                (q.current_state, q.last_notify_state) != (QuotaState.hard_limit, QuotaState.grace_expired):
            return True


    # important, in any case we use this variable, we have to
    # be sure, that at least one notification was sent ...
    last_notification = max([q.last_notify_date for q in quotas])
    if last_notification is not None:
      last_now = datetime.now() - last_notification
    else:
      last_now = 0

    # new check for reaching the hard limit and re-notifying after a 
    # certain period
 
    for q in quotas:
        if ( q.current_state == QuotaState.hard_limit ):
          return last_now >= timedelta(minutes=config['hard_limit_renotification'])
        if ( q.current_state == QuotaState.soft_limit ):
          return last_now >= timedelta(minutes=config['soft_limit_renotification'])
        if ( q.current_state == QuotaState.grace_urgend ):
          return last_now >= timedelta( minutes=config['grace_time_exp_period'] )
        if ( q.current_state == QuotaState.grace_expired ):
          return last_now >= timedelta(minutes=config['hard_limit_renotification'])

    # No state is worse than it was.

    # Only send an email if all states are under quota...
    for q in quotas:
        if q.current_state != QuotaState.under_quota:
            return False
    # ...and at least one old state was over quota somehow.
    for q in quotas:
        if q.last_notify_state != QuotaState.under_quota:
            # Only send email if notification hysteresis has passed.
            return (datetime.now() - last_notification) > timedelta(minutes=config['notification_hysteresis'])

    # At this point, we've covered all of the circumstances under which we'd
    # want to send an email, so the default is not to send one.
    return False

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

    if send_email_p(quotas):
        summary = ''
        details = []
        qtype = tuple(QuotaType._asdict().keys())
        qstate = tuple(QuotaState._asdict().keys())
        for q in quotas:
            if q.current_state == q.last_notify_state:
                #template_key = '%s_summary_old' % q.quota_type.key
                template_key = '%s_summary_old' % qtype[q.quota_type]
            else:
                #template_key = '%s_summary_new' % q.quota_type.key
                template_key = '%s_summary_new' % qtype[q.quota_type]
            template_str = config['templates'][qstate[q.current_state]][template_key]
            if template_str:
                #sum_text = jinja2.Template(template_str).render(account=ai, quota=q)
                sum_text = jj_env.from_string(template_str).render(account=ai, quota=q)
                if summary == '':
                    summary = sum_text
                else:
                    summary += '  Also, %s%s' % (sum_text[0].lower(), sum_text[1:])
            #details.append(jinja2.Template(config['templates'][qstate[q.current_state]]['%s_detail' % qtype[q.quota_type]]).render(account=ai, quota=q))
            details.append(jj_env.from_string(config['templates'][qstate[q.current_state]]['%s_detail' % qtype[q.quota_type]]).render(account=ai, quota=q))
        worst_state = qstate[quotas[0].current_state]
        # look for the quota record which has the lowest grace time to be used in the message
        template_quota = None
        for q in quotas:
          if template_quota is None:
            template_quota = q
          else:
            if template_quota.grace_expires_delta > q.grace_expires_delta:
              template_quota = q
        message = jj_env.get_template(config['templates'][worst_state]['main_file']).render(account=ai, summary=summary, details=details, quota=template_quota)
        if config['debug']:
            recipient = config['debug_mail_recipient']
        else:
            recipient = ai.username
        #send_email(recipient, jinja2.Template(config['templates'][worst_state]['subject']).render(account=ai), message)
        send_email(recipient, jj_env.from_string(config['templates'][worst_state]['subject']).render(account=ai), message)
        log_message = 'Sent email to %s: %s' % (ai.username, ', '.join(['%s %s %s %s/%s' % (q.filesystem, qtype[q.quota_type], qstate[q.current_state], q.used, q.soft_limit) for q in quotas]))
        if config['debug']:
            print( log_message )
        else:
            syslog.syslog(syslog.LOG_INFO | syslog.LOG_USER, log_message)
        ai.set_notify(quotas)

for ai in AccountInfo.all(cur, config):
    handle_state_change(ai)
cache.commit()
