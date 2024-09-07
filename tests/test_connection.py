"""Tests for the connection module."""

import asyncio
import gc
from unittest.mock import Mock, patch

import pytest
from asusrouter.connection import Connection, generate_credentials


@pytest.mark.asyncio
async def test_generate_credentials():
    username = "user"
    password = "pass"
    payload, headers = generate_credentials(username, password)
    assert payload == "login_authorization=dXNlcjpwYXNz"
    assert headers == {"user-agent": "asusrouter--DUTUtil-"}


class TestConnection:
    def _assert_connection(
        self,
        conn,
        hostname,
        username,
        password,
        port,
        use_ssl,
        session,
        dumpback,
        mock_new_session,
    ):
        assert conn._hostname == hostname
        assert conn._username == username
        assert conn._password == password
        assert conn._port == (port or (8443 if use_ssl else 80))
        assert conn._ssl == use_ssl
        assert conn._session == (session or mock_new_session.return_value)
        assert conn._dumpback == dumpback
        assert conn._token is None
        assert conn._header is None
        assert conn._connected is False
        assert isinstance(conn._connection_lock, asyncio.Lock)

    @pytest.mark.parametrize(
        "hostname, username, password, port, use_ssl, session, dumpback",
        [
            ("localhost", "user", "pass", None, False, None, None),
            ("localhost", "user", "pass", 8080, True, None, None),
            ("localhost", "user", "pass", 8080, False, Mock(), None),
            ("localhost", "user", "pass", 8080, True, Mock(), Mock()),
            ("", "user", "pass", 8080, True, Mock(), Mock()),
            ("localhost", "", "pass", 8080, True, None, None),
            ("localhost", "user", "pass", -1, True, None, None),
        ],
    )
    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_init(
        self,
        mock_new_session,
        hostname,
        username,
        password,
        port,
        use_ssl,
        session,
        dumpback,
    ):
        conn = Connection(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            dumpback=dumpback,
        )

        self._assert_connection(
            conn,
            hostname,
            username,
            password,
            port,
            use_ssl,
            session,
            dumpback,
            mock_new_session,
        )

    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_init_multiple_instances(self, mock_new_session):
        conn1 = Connection(
            hostname="localhost1",
            username="user1",
            password="pass1",
            port=8080,
            use_ssl=True,
        )
        conn2 = Connection(
            hostname="localhost2",
            username="user2",
            password="pass2",
            port=9090,
            use_ssl=False,
        )

        self._assert_connection(
            conn1,
            "localhost1",
            "user1",
            "pass1",
            8080,
            True,
            None,
            None,
            mock_new_session,
        )
        self._assert_connection(
            conn2,
            "localhost2",
            "user2",
            "pass2",
            9090,
            False,
            None,
            None,
            mock_new_session,
        )

        # Ensure that instances do not interfere with each other
        assert conn1._hostname != conn2._hostname
        assert conn1._username != conn2._username
        assert conn1._password != conn2._password
        assert conn1._port != conn2._port
        assert conn1._ssl != conn2._ssl

    @pytest.mark.parametrize(
        "manage_session, session_closed, running_loop, expected_close_call, expected_create_task, expected_run",
        [
            (
                True,
                False,
                True,
                True,
                True,
                False,
            ),  # Managed session, not closed, running loop
            (
                True,
                False,
                False,
                True,
                False,
                True,
            ),  # Managed session, not closed, no running loop
            (
                True,
                True,
                True,
                False,
                False,
                False,
            ),  # Managed session, already closed
            (False, False, True, False, False, False),  # Not managed session
        ],
    )
    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_del(
        self,
        mock_new_session,
        manage_session,
        session_closed,
        running_loop,
        expected_close_call,
        expected_create_task,
        expected_run,
    ):
        # Create a mock session
        mock_session = Mock()
        mock_session.closed = session_closed

        # Create an instance of Connection with the mock session
        conn = Connection(
            hostname="localhost",
            username="user",
            password="pass",
            session=mock_session,
        )
        conn._manage_session = manage_session

        # Mock the asyncio.get_running_loop to return a mock loop or raise RuntimeError
        if running_loop:
            mock_loop = Mock()
            get_running_loop_patch = patch(
                "asyncio.get_running_loop", return_value=mock_loop
            )
        else:
            get_running_loop_patch = patch(
                "asyncio.get_running_loop", side_effect=RuntimeError
            )

        with get_running_loop_patch as mock_get_running_loop:
            with patch("asyncio.run") as mock_run:
                # Delete the connection object to trigger __del__
                del conn

                # Force garbage collection
                gc.collect()

                # Verify that the session's close method was called if expected
                if expected_close_call:
                    mock_session.close.assert_called_once()
                else:
                    mock_session.close.assert_not_called()

                # Verify that create_task was called if expected
                if expected_create_task:
                    mock_get_running_loop.return_value.create_task.assert_called_once_with(
                        mock_session.close()
                    )
                else:
                    if running_loop:
                        mock_get_running_loop.return_value.create_task.assert_not_called()

                # Verify that asyncio.run was called if expected
                if expected_run:
                    mock_run.assert_called_once_with(mock_session.close())
                else:
                    mock_run.assert_not_called()
