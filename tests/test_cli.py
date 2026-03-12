"""Tests for CLI."""

from click.testing import CliRunner

from cloud_mapper.cli import main


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Discover AWS resources" in result.output

    def test_invalid_service(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--services", "nonexistent"])
        assert result.exit_code != 0

    def test_from_data_missing_file(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--from-data", "/nonexistent/file.json"])
        assert result.exit_code != 0
