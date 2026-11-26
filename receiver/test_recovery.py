import unittest
from unittest.mock import patch

import service


class RecoveryTests(unittest.TestCase):
    def test_transient_duplicate_and_other_stream_do_not_reset(self):
        events = {}
        with patch.dict(service.recovery_after, clear=True), patch.object(service, 'restart') as restart:
            for stream, clock in [('mainStream', 1000), ('mainStream', 1001), ('subStream', 1020), ('mainStream', 1181)]:
                service.media_fault('cam', stream, events, clock)
            restart.assert_not_called()

    def test_two_failures_restart_one_camera_with_worker_independent_cooldown(self):
        with patch.dict(service.recovery_after, clear=True), patch.object(service, 'restart') as restart:
            events = {}
            for clock in [1000, 1030]:
                service.media_fault('abc', 'mainStream', events, clock)
            for clock in [1080, 1110]:
                service.media_fault('abc', 'mainStream', {}, clock)
            restart.assert_called_once_with('abc')
            self.assertNotIn('other', service.recovery_after)
