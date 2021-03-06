#!/usr/bin/env python

# Copyright (c) 2015  Phil Gold <phil_g@pobox.com>
#
# changed: Oliver Cordes 2017-06-21
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.


import optparse
import os.path
import platform
import sys

import yaml  # http://pyyaml.org

DEFAULTS = {
    'cache': 'cache',
    'debug': False,
    'debug_mail_recipient': 'root',
    'domain': platform.node(),
    'from_address': 'root',
    'notification_hysteresis': 30,
    'hard_limit_renotification' : 1440,   # in minutes
    'soft_limit_renotification' : 1440,   # in minutes
    'grace_time_ext_warning' : 1440, # start of extensive warning in minutes
    'grace_time_exp_period'  : 60,   # warn every 60 minutes
    'reply_to': None,
    'smtp_host': 'localhost',
}

def find_config_file():
    for path in ['/etc/quotanotify/config.yaml', '/etc/quotanotify.yaml',
                 '/usr/local/etc/quotanotify/config.yaml',
                 '/usr/local/etc/quotanotify.yaml',
                 os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yaml')]:
        if os.path.isfile(path):
            return path
    return None

def canonify_path(path, base):
    if os.path.isabs(path):
        return path
    return os.path.realpath(os.path.join(base, path))

def load_config_file():
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config', default=find_config_file(),
                      help='Location of the configuration file.')
    (options, args) = parser.parse_args()
    try:
        config_file = open(options.config)
        try:
            config_dir = os.path.dirname(options.config)
            config = yaml.load(config_file, Loader=yaml.CLoader)
            # Fill in defaults.
            #for dkey, dvalue in DEFAULTS.iteritems():
            for dkey, dvalue in DEFAULTS.items():
                if dkey not in config:
                    config[dkey] = dvalue
            # Canonify path names.
            config['cache'] = canonify_path(config['cache'], config_dir)
            for template_name in config['templates']:
                config['templates'][template_name]['main_file'] = \
                    canonify_path(config['templates'][template_name]['main_file'],
                                  config_dir)
            return config
        finally:
            config_file.close()
    except IOError:
        print >>sys.stderr, 'Unable to open config file: %s' % options.config
        sys.exit(1)
