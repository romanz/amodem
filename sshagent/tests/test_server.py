from .. import server


def test_socket():
    server.unix_domain_socket_server('name')
