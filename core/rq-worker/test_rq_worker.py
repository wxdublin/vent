import os
import pytest

import file_watch

def test_settings():
    os.environ['REMOTE_REDIS_HOST'] = "test"
    os.environ['REMOTE_REDIS_PORT'] = "test"
    import settings

def test_pcap_queue():
    file_watch.pcap_queue("/tmp")
    file_watch.pcap_queue("/dev/null")


def test_template_queue():
    file_watch.template_queue("/dev/null")
    file_watch.template_queue("/core.template")
    file_watch.template_queue("/collectors.template")
    file_watch.template_queue("/visualization.template")
