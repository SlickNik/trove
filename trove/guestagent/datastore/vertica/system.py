#  All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from trove.common import cfg

CONF = cfg.CONF

CREATE_DB = (" /opt/vertica/bin/adminTools -t create_db -s"
             " %s -d %s -c %s -D %s -p '%s'")

INSTALL_VERTICA = ("/opt/vertica/sbin/install_vertica -s %s"
                   " -d %s -X -N -S default -r"
                   " %s -L %s  -Y --failure-threshold NONE")

STOP_DB = "/opt/vertica/bin/adminTools -t stop_db -F -d %s -p '%s'"
START_DB = "/opt/vertica/bin/adminTools -t start_db -d %s -p '%s'"
STATUS_ACTIVE_DB = "/opt/vertica/bin/adminTools -t show_active_db"
STATUS_DB_DOWN = "/opt/vertica/bin/adminTools -t db_status -s DOWN"
VERTICA_TEMP_CONF = "/tmp/vertica.tmp"
VERTICA_CONF = "/etc/vertica.cnf"
INSTALL_TIMEOUT = 1000
