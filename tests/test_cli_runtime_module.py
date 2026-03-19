import argparse
import unittest
from unittest import mock

import cli_runtime


class CliRuntimeModuleTests(unittest.TestCase):
    def _parser_with_result(self, result: int) -> mock.Mock:
        parser = mock.Mock(spec=argparse.ArgumentParser)
        parser.parse_args.return_value = argparse.Namespace(func=lambda _args: result)
        return parser

    def test_default_prog_returns_integrator(self) -> None:
        self.assertEqual(cli_runtime.default_prog("anything"), "integrator")

    def test_run_cli_builds_parser_and_dispatches(self) -> None:
        parser = self._parser_with_result(7)
        with mock.patch("cli_runtime.build_cli_parser", return_value=parser) as build_mock:
            code = cli_runtime.run_cli(["integrator", "doctor"])
        self.assertEqual(code, 7)
        self.assertEqual(build_mock.call_args.kwargs["prog"], "integrator")
        parser.parse_args.assert_called_once_with(["doctor"])
