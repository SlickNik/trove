# All Rights Reserved.
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

import os
import subprocess

from trove.common import cfg
from trove.common import exception
from trove.common import utils as utils
from trove.common import instance as rd_instance
from trove.guestagent.datastore import service
from trove.guestagent import pkg
from trove.guestagent.datastore.vertica import system
from trove.openstack.common import log as logging
from trove.openstack.common.gettextutils import _

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
packager = pkg.Package()
DB_NAME = 'db_srvr'
DEB_FILE = '/vertica_7.1.1-0_amd64.deb'
LICENSE_FILE = 'CE'
MOUNT_POINT = '/var/lib/vertica'

INCLUDE_MARKER_OPERATORS = {
    True: ">=",
    False: ">"
}


def get_ip(adapter):
    import netifaces as ni
    ni.ifaddresses(adapter)
    return ni.ifaddresses(adapter)[2][0]['addr']


class VerticaAppStatus(service.BaseDbStatus):

    def _get_actual_db_status(self):
        """Get the status of dbaas and report it back."""
        try:
            out, err = utils.execute(
                "su",
                "-",
                "dbadmin",
                "-c",
                system.STATUS_ACTIVE_DB,
                run_as_root=True,
                root_helper="sudo")
            if out.strip() == DB_NAME:
                # UP status is confirmed
                LOG.info("Service Status is RUNNING.")
                return rd_instance.ServiceStatuses.RUNNING
            elif out.strip() == "":
                # nothing returned, means no db running lets verify
                out, err = utils.execute(
                    "su", "-",
                    "dbadmin",
                    "-c",
                    system.STATUS_DB_DOWN,
                    run_as_root=True,
                    root_helper="sudo")
                if out.strip() == DB_NAME:
                    # DOWN status is confirmed
                    LOG.info("Service Status is SHUTDOWN.")
                    return rd_instance.ServiceStatuses.SHUTDOWN
                else:
                    return rd_instance.ServiceStatuses.UNKNOWN
        except exception.ProcessExecutionError:
            LOG.error("Process execution ")
            return rd_instance.ServiceStatuses.FAILED


class VerticaApp(object):
    """Prepares DBaaS on a Guest container."""

    def __init__(self, status):
        """By default login with root no password for initial setup."""
        self.state_change_wait_time = CONF.state_change_wait_time
        self.status = status

    def stop_db(self, update_db=False, do_not_start_on_reboot=False):
        """Stop the database."""
        LOG.info(_("Stopping vertica..."))
        # using vertica admintools to stop db.
        DB_PASS = self._get_database_password()
        STOP_DB_COMMAND = ["sudo", "su", "-", "dbadmin", "-c",
                           (system.STOP_DB % (DB_NAME, DB_PASS))]
        subprocess.call(STOP_DB_COMMAND)
        if not self.status.wait_for_real_status_to_change_to(
                rd_instance.ServiceStatuses.SHUTDOWN,
                self.state_change_wait_time, update_db):
            LOG.error(_("Could not stop Vertica."))
            self.status.end_install_or_restart()
            raise RuntimeError("Could not stop Vertica!")

    def start_db(self, update_db=False):
        """Start the database."""
        LOG.info(_("Starting vertica..."))
        # using vertica admintools to start db.
        DB_PASS = self._get_database_password()
        START_DB_COMMAND = ["sudo", "su", "-", "dbadmin", "-c",
                            (system.START_DB % (DB_NAME, DB_PASS))]
        subprocess.call(START_DB_COMMAND)
        if not self.status.wait_for_real_status_to_change_to(
                rd_instance.ServiceStatuses.RUNNING,
                self.state_change_wait_time, update_db):
            LOG.error(_("Start up of Vertica failed."))
            self.status.end_install_or_restart()
            raise RuntimeError("Could not start Vertica!")

    def restart(self):
        """Restart the database."""
        try:
            self.status.begin_restart()
            self.stop_db()
            self.start_db()
        finally:
            self.status.end_install_or_restart()

    def create_db(self):
        """Prepare the guest machine with a vertica db creation."""
        LOG.info(_("Creating database on Vertica host"))
        try:
            # Create db after install
            DB_PASS = self._get_database_password()
            CREATE_DB_COMMAND = ["sudo", "su", "-", "dbadmin", "-c",
                                 (system.CREATE_DB % (get_ip('eth0'),
                                                      DB_NAME,
                                                      MOUNT_POINT,
                                                      MOUNT_POINT,
                                                      DB_PASS))]
            subprocess.check_call(CREATE_DB_COMMAND)
        except subprocess.CalledProcessError:
            LOG.error("vertica database create failed.")
        LOG.info(_("Vertica database create completed."))

    def install_vertica(self):
        """Prepare the guest machine with a vertica db creation."""
        LOG.info(_("Preparing Guest as Vertica Server"))
        try:
            # Create db after install
            INSTALL_VERTICA_CMD = ["sudo", "su", "-", "root", "-c",
                                   (system.INSTALL_VERTICA % (get_ip('eth0'),
                                                              MOUNT_POINT,
                                                              DEB_FILE,
                                                              LICENSE_FILE))]
            subprocess.check_call(INSTALL_VERTICA_CMD)
        except subprocess.CalledProcessError:
            LOG.error("install_vertica failed.")
        self._generate_database_password()
        LOG.info(_("install_vertica completed."))

    def complete_install_or_restart(self):
        self.status.end_install_or_restart()

    def _generate_database_password(self):
        """Generate and write the password to vertica.cnf file."""
        config_content = ("dbadmin_password = %s\n" %
                          utils.generate_random_password())
        self.write_config(config_content)

    def write_config(self, config_contents):
        """Write the configuration contents to vertica.cnf file."""
        LOG.debug('Defining temp config holder at %s.' %
                  system.VERTICA_TEMP_CONF)
        try:
            with open(system.VERTICA_TEMP_CONF, 'w+') as conf:
                conf.write(config_contents)
            LOG.info(_('Writing new config.'))
            utils.execute_with_timeout("mv", system.VERTICA_TEMP_CONF,
                                       system.VERTICA_CONF, run_as_root=True,
                                       root_helper="sudo")
        except Exception:
            os.unlink(system.VERTICA_TEMP_CONF)
            raise

    def _get_database_password(self):
        """Read the password from vertica.cnf file and return it."""
        pwd, err = utils.execute_with_timeout("awk", '{print $3}',
                                              system.VERTICA_CONF,
                                              run_as_root=True,
                                              root_helper="sudo")
        if err:
            LOG.error(err)
            raise RuntimeError("Problem reading vertica.cnf! : %s" % err)
        return pwd.strip()

    def install_if_needed(self, packages):
        """Install Vertica package if needed."""
        LOG.info(_('Preparing Guest as Vertica Server.'))
        if not packager.pkg_is_installed(packages):
            LOG.debug('Installing Vertica Package.')
            packager.pkg_install(packages, None, system.INSTALL_TIMEOUT)

    def prepare_for_install_vertica(self):
        """This method executes preparatory method before
        executing install_vertica"""
        utils.execute("VERT_DBA_USR=dbadmin", "VERT_DBA_HOME=/home/dbadmin",
                      "VERT_DBA_GRP=verticadba",
                      "/opt/vertica/oss/python/bin/python", "-m",
                      "vertica.local_coerce",
                      run_as_root=True, root_helper="sudo")
