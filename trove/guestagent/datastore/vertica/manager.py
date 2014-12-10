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
from trove.common import cfg
from trove.common import instance as rd_instance
from trove.guestagent import volume
from trove.guestagent import dbaas
from trove.guestagent.datastore.vertica.service import VerticaAppStatus
from trove.guestagent.datastore.vertica.service import VerticaApp
from trove.openstack.common import log as logging
from trove.openstack.common.gettextutils import _
from trove.openstack.common import periodic_task

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
MANAGER = 'vertica' if not CONF.datastore_manager else CONF.datastore_manager


class Manager(periodic_task.PeriodicTasks):

    def __init__(self):
        self.appStatus = VerticaAppStatus()
        self.app = VerticaApp(self.appStatus)

    @periodic_task.periodic_task(ticks_between_runs=3)
    def update_status(self, context):
        """Update the status of the Vertica service."""
        self.appStatus.update()

    def prepare(self, context, packages, databases, memory_mb, users,
                device_path=None, mount_point=None, backup_info=None,
                config_contents=None, root_password=None, overrides=None,
                cluster_config=None):
        """Makes ready DBAAS on a Guest container."""
        try:
            LOG.info(_("Setting instance status BUILDING."))
            if device_path:
                #stop and do not update database
                device = volume.VolumeDevice(device_path)
                # unmount if device is already mounted
                device.unmount_device(device_path)
                device.format()
                if os.path.exists(mount_point):
                    #rsync existing data
                    device.migrate_data(mount_point)
                    # mount the volume
                    device.mount(mount_point)
                    LOG.debug(_("Mounted the volume."))
            self.appStatus.begin_install()
            self.app.install_if_needed(packages)
            self.app.install_vertica()
            self.app.create_db()
            self.app.complete_install_or_restart()
            LOG.info('"prepare" call has finished.')
        except Exception as e:
            LOG.error(e)
            self.appStatus.set_status(rd_instance.ServiceStatuses.FAILED)
            raise

    def restart(self, context):
        self.app.restart()

    def get_filesystem_stats(self, context, fs_path):
        """Gets the filesystem stats for the path given."""
        mount_point = CONF.get(MANAGER).mount_point
        return dbaas.get_filesystem_volume_stats(mount_point)

    def stop_db(self, context, do_not_start_on_reboot=False):
        self.app.stop_db(do_not_start_on_reboot=do_not_start_on_reboot)

    def mount_volume(self, context, device_path=None, mount_point=None):
        device = volume.VolumeDevice(device_path)
        device.mount(mount_point, write_to_fstab=False)
        LOG.debug(_("Mounted the volume."))

    def unmount_volume(self, context, device_path=None, mount_point=None):
        device = volume.VolumeDevice(device_path)
        device.unmount(mount_point)
        LOG.debug(_("Unmounted the volume."))

    def resize_fs(self, context, device_path=None, mount_point=None):
        device = volume.VolumeDevice(device_path)
        device.resize_fs(mount_point)
        LOG.debug(_("Resized the filesystem"))
