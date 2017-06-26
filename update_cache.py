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

import pwd

#from pysqlite2 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite
from sqlite3 import dbapi2 as sqlite  # https://github.com/ghaering/pysqlite

config = load_config_file()
cache = sqlite.connect(config['cache'])
cur = cache.cursor()

# Update quotas for every account on the system.
for pwd_entry in pwd.getpwall():
    ai = AccountInfo(pwd_entry.pw_uid, cur, config)
    ai.refresh_from_system()
    ai.update()

cache.commit()
