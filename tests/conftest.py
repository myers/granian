import asyncio
import os
import socket
from contextlib import asynccontextmanager, closing
from functools import partial
from pathlib import Path

import pytest


@asynccontextmanager
async def _server(interface, port, threading_mode, tls=False, tmp_path=None):
    certs_path = Path.cwd() / 'tests' / 'fixtures' / 'tls'
    tls_opts = (
        (f"--ssl-certificate {certs_path / 'cert.pem'} " f"--ssl-keyfile {certs_path / 'key.pem'} ") if tls else ''
    )
    env = os.environ.copy()
    if tmp_path:
        env['ROOT_PATH'] = str(tmp_path)
    proc = await asyncio.create_subprocess_shell(
        ''.join(
            [
                f'granian --interface {interface} --port {port} ',
                f'--threads 1 --threading-mode {threading_mode} ',
                tls_opts,
                '--opt ' if os.getenv('LOOP_OPT') else '',
                f'tests.apps.{interface}:app',
            ]
        ),
        env=env,
    )
    await asyncio.sleep(1)
    try:
        yield port
    finally:
        proc.terminate()
        await proc.wait()


@pytest.fixture(scope='function')
def server_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('localhost', 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


@pytest.fixture(scope='function')
def asgi_server(server_port):
    return partial(_server, 'asgi', server_port)


@pytest.fixture(scope='function')
def rsgi_server(server_port, tmp_path):
    return partial(_server, 'rsgi', server_port, tmp_path=tmp_path)


@pytest.fixture(scope='function')
def wsgi_server(server_port):
    return partial(_server, 'wsgi', server_port)


@pytest.fixture(scope='function')
def server(server_port, request):
    return partial(_server, request.param, server_port)


@pytest.fixture(scope='function')
def server_tls(server_port, request):
    return partial(_server, request.param, server_port, tls=True)
