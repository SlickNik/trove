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

import testtools
import mock
import subprocess

from mock import MagicMock
from mock import Mock
from trove.common import utils
from trove.guestagent.datastore.vertica import service
from trove.guestagent.datastore.vertica.service import VerticaApp


class GuestAgentServiceTest(testtools.TestCase):
    def setUp(self):
        super(GuestAgentServiceTest, self).setUp()

    def tearDown(self):
        super(GuestAgentServiceTest, self).tearDown()

    @mock.patch.object(subprocess, 'call', Mock(return_value=0))
    def test_start_db(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App._get_database_password = MagicMock(return_value='text')
        App.start_db()
        self.assertTrue(App._get_database_password.called)
        self.assertEqual(subprocess.call.call_count, 1)

    @mock.patch.object(subprocess, 'call', Mock(return_value=0))
    def test_stop_db(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App._get_database_password = MagicMock(return_value='text')
        App.stop_db()
        self.assertTrue(App._get_database_password.called)
        self.assertEqual(subprocess.call.call_count, 1)

    @mock.patch.object(utils, 'execute', Mock(return_value=0))
    def test_prepare_for_install_vertica(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App.prepare_for_install_vertica()
        self.assertEqual(utils.execute.call_count, 1)

    @mock.patch.object(subprocess, 'call', Mock(return_value=0))
    def test_restart_db(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App._get_database_password = MagicMock(return_value='text')
        App.restart()
        self.assertTrue(App._get_database_password.called)
        self.assertEqual(subprocess.call.call_count, 2)

    @mock.patch.object(subprocess, 'check_call', Mock(return_value=0))
    def test_create_db(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App._get_database_password = MagicMock(return_value='text')
        App.create_db()
        self.assertTrue(App._get_database_password.called)
        self.assertEqual(subprocess.check_call.call_count, 1)

    @mock.patch.object(subprocess, 'check_call', Mock(return_value=0))
    def test_install_vertica(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App.write_config = MagicMock(return_value=None)
        App.install_vertica()
        self.assertEqual(subprocess.check_call.call_count, 1)
        self.assertTrue(App.write_config.called)

    @mock.patch.object(utils, 'execute_with_timeout', Mock(return_value=0))
    def test_generate_database_password(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App._generate_database_password()
        self.assertEqual(utils.execute_with_timeout.call_count, 1)

    @mock.patch.object(utils, 'execute_with_timeout', Mock(return_value=0))
    def test_write_config(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        App.write_config("sometext")
        self.assertEqual(utils.execute_with_timeout.call_count, 1)

    @mock.patch.object(utils, 'execute_with_timeout',
                       Mock(return_value=("password", 0)))
    def test_get_database_password(self):
        mock_status = MagicMock()
        App = VerticaApp(status=mock_status)
        passwd = App._get_database_password()
        self.assertEqual(utils.execute_with_timeout.call_count, 1)
        self.assertEqual(passwd, "password")

    def test_install_if_needed_package_not_installed(self):
        mock_status = MagicMock()
        service.packager = MagicMock()
        service.packager.pkg_is_installed = MagicMock(return_value=False)
        App = VerticaApp(status=mock_status)
        App.install_if_needed(['vertica'])
        self.assertTrue(service.packager.pkg_is_installed.called)
        self.assertTrue(service.packager.pkg_install.called)

    def test_install_if_needed_package_installed(self):
        mock_status = MagicMock()
        service.packager = MagicMock()
        service.packager.pkg_is_installed = MagicMock(return_value=True)
        App = VerticaApp(status=mock_status)
        App.install_if_needed(['vertica'])
        self.assertTrue(service.packager.pkg_is_installed.called)
        self.assertFalse(service.packager.pkg_install.called)
