# -*- coding: utf-8 -*-

import mock
import pytest

from pushjack import (
    APNSClient,
    APNSError,
    APNSDataOverflow,
    APNSConfig,
    create_apns_config,
    create_apns_sandbox_config
)
from pushjack.utils import json_dumps

from .fixtures import apns, apns_sock, parametrize


test_token = '1' * 64


@parametrize('token,alert,extra,expected', [
    (test_token,
     'Hello world',
     {'badge': 1,
      'sound': 'chime',
      'category': 'Pushjack',
      'content_available': True,
      'extra': {'custom_data': 12345},
      'expiration': 3},
     (json_dumps({'aps': {'alert': 'Hello world',
                          'badge': 1,
                          'sound': 'chime',
                          'category': 'Pushjack',
                          'content-available': 1},
                  'custom_data': 12345}),
      0, 3, 10)),
    (test_token,
     None,
     {'loc_key': 'lk',
      'action_loc_key': 'alk',
      'loc_args': 'la',
      'expiration': 3},
     (json_dumps({'aps': {'alert': {'action-loc-key': 'alk',
                                    'loc-args': 'la',
                                    'loc-key': 'lk'}}}),
      0, 3, 10)),
    (test_token,
     'Hello world',
     {'loc_key': 'lk',
      'action_loc_key': 'alk',
      'loc_args': 'la',
      'expiration': 3},
     (json_dumps({'aps': {'alert': {'body': 'Hello world',
                                    'action-loc-key': 'alk',
                                    'loc-args': 'la',
                                    'loc-key': 'lk'}}}),
      0, 3, 10)),
])
def test_apns_send(apns, apns_sock, token, alert, extra, expected):
    with mock.patch('pushjack.apns.pack_frame') as patched:
        apns.send(test_token, alert, sock=apns_sock, **extra)
        patched.assert_called_once_with(test_token, *expected)


@parametrize('token', [
    '1' * 64,
    'abcdef0123456789' * 4,
])
def test_valid_token(apns, token, apns_sock):
    apns.send(token, None, sock=apns_sock)
    assert apns_sock.write.called


@parametrize('token', [
    '1',
    'x' * 64,
])
def test_invalid_token(apns, token, apns_sock):
    with pytest.raises(APNSError) as exc_info:
        apns.send(token, None, sock=apns_sock)

    assert 'Invalid token format' in str(exc_info.value)


def test_apns_use_extra(apns, apns_sock):
    with mock.patch('pushjack.apns.pack_frame') as patched:
        apns.send(test_token,
                  'sample',
                  extra={'foo': 'bar'},
                  identifier=10,
                  expiration=30,
                  priority=10,
                  sock=apns_sock)

        expected_payload = b'{"aps":{"alert":"sample"},"foo":"bar"}'
        patched.assert_called_once_with(test_token,
                                        expected_payload,
                                        10,
                                        30,
                                        10)


def test_apns_socket_write(apns, apns_sock):
    apns.send(test_token,
              'sample',
              extra={'foo': 'bar'},
              identifier=10,
              expiration=30,
              priority=10,
              sock=apns_sock)

    expected = mock.call.write(
        b'\x02\x00\x00\x00^\x01\x00 \x11\x11\x11\x11\x11'
        b'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
        b'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
        b'\x11\x11\x11\x11\x11\x02\x00&'
        b'{"aps":{"alert":"sample"},"foo":"bar"}'
        b'\x03\x00\x04\x00\x00\x00\n\x04\x00\x04\x00\x00'
        b'\x00\x1e\x05\x00\x01\n')

    assert expected in apns_sock.mock_calls


def test_apns_oversized_payload(apns, apns_sock):
    with mock.patch('pushjack.apns.pack_frame') as patched:
        with pytest.raises(APNSDataOverflow):
            apns.send(test_token, '_' * 2049, sock=apns_sock)

        assert not patched.called


def test_apns_settings():
    settings = create_apns_config()
    assert isinstance(settings, dict)
    assert isinstance(settings, APNSConfig)
    assert settings['APNS_HOST'] == 'gateway.push.apple.com'
    assert settings['APNS_PORT'] == 2195
    assert settings['APNS_FEEDBACK_HOST'] == 'feedback.push.apple.com'
    assert settings['APNS_FEEDBACK_PORT'] == 2196
    assert settings['APNS_CERTIFICATE'] == None
    assert settings['APNS_ERROR_TIMEOUT'] == 0.5
    assert settings['APNS_DEFAULT_EXPIRATION_OFFSET'] == 60 * 60 * 24 * 30
    assert settings['APNS_MAX_NOTIFICATION_SIZE'] == 2048


def test_apns_sandbox_settings():
    settings = create_apns_sandbox_config()
    assert isinstance(settings, dict)
    assert isinstance(settings, APNSConfig)
    assert settings['APNS_HOST'] == 'gateway.sandbox.push.apple.com'
    assert settings['APNS_PORT'] == 2195
    assert settings['APNS_FEEDBACK_HOST'] == 'feedback.sandbox.push.apple.com'
    assert settings['APNS_FEEDBACK_PORT'] == 2196
    assert settings['APNS_CERTIFICATE'] == None
    assert settings['APNS_ERROR_TIMEOUT'] == 0.5
    assert settings['APNS_MAX_NOTIFICATION_SIZE'] == 2048