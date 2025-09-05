import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.exceptions import Exit
from rodoo.utils.misc import (
    _parse_cli_params,
    _validate_required_cli_params,
    _handle_no_cli_params,
    _handle_cli_params_present,
    process_cli_args,
    _construct_runner,
)


class TestParseCliParams:
    def test_parse_cli_params_with_module(self):
        """Test _parse_cli_params with module parameter."""
        args = {"module": "base,sale", "version": 16.0, "profile": "test"}
        result = _parse_cli_params(args)
        assert result == {"modules": ["base", "sale"], "version": 16.0}

    def test_parse_cli_params_without_module(self):
        """Test _parse_cli_params without module parameter."""
        args = {"version": 16.0, "db": "test_db"}
        result = _parse_cli_params(args)
        assert result == {"version": 16.0, "db": "test_db"}

    def test_parse_cli_params_empty(self):
        """Test _parse_cli_params with empty args."""
        args = {}
        result = _parse_cli_params(args)
        assert result == {}


class TestValidateRequiredCliParams:
    def test_validate_required_params_valid(self):
        """Test _validate_required_cli_params with valid params."""
        cli_params = {"modules": ["base"], "version": 16.0}
        # Should not raise
        _validate_required_cli_params(cli_params)

    def test_validate_required_params_missing_modules(self):
        """Test _validate_required_cli_params missing modules."""
        cli_params = {"version": 16.0}
        with patch("rodoo.output.Output.error") as mock_error:
            with pytest.raises(Exit):
                _validate_required_cli_params(cli_params)
            mock_error.assert_called_once()

    def test_validate_required_params_missing_version(self):
        """Test _validate_required_cli_params missing version."""
        cli_params = {"modules": ["base"]}
        with patch("rodoo.output.Output.error") as mock_error:
            with pytest.raises(Exit):
                _validate_required_cli_params(cli_params)
            mock_error.assert_called_once()


class TestHandleNoCliParams:
    @patch("rodoo.cli.load_and_merge_profiles")
    @patch("rodoo.cli.Output.confirm")
    @patch("rodoo.cli.create_profile")
    def test_handle_no_cli_params_no_profiles_create_new(
        self, mock_create_profile, mock_confirm, mock_load_profiles
    ):
        """Test _handle_no_cli_params with no profiles, user chooses to create."""
        mock_load_profiles.return_value = ({}, {})
        mock_confirm.return_value = True
        mock_create_profile.return_value = (
            "test",
            {"modules": ["base"], "version": 16.0},
            Path("/fake"),
        )

        result = _handle_no_cli_params(None)
        assert result == {"modules": ["base"], "version": 16.0}

    @patch("rodoo.cli.load_and_merge_profiles")
    @patch("rodoo.cli.Output.confirm")
    def test_handle_no_cli_params_no_profiles_exit(
        self, mock_confirm, mock_load_profiles
    ):
        """Test _handle_no_cli_params with no profiles, user chooses to exit."""
        mock_load_profiles.return_value = ({}, {})
        mock_confirm.return_value = False

        with pytest.raises(Exit):
            _handle_no_cli_params(None)

    @patch("rodoo.cli.load_and_merge_profiles")
    @patch("rodoo.cli.typer.prompt")
    @patch("rodoo.cli.Output.confirm")
    def test_handle_no_cli_params_with_profiles(
        self, mock_confirm, mock_prompt, mock_load_profiles
    ):
        """Test _handle_no_cli_params with existing profiles."""
        profiles = {"test": {"modules": ["base"], "version": 16.0}}
        sources = {"test": Path("/fake/config")}
        mock_load_profiles.return_value = (profiles, sources)
        mock_prompt.return_value = "test"
        mock_confirm.return_value = True

        result = _handle_no_cli_params(None)
        assert result == profiles["test"]


class TestHandleCliParamsPresent:
    @patch("rodoo.config.load_and_merge_profiles")
    @patch("pathlib.Path.cwd")
    def test_handle_cli_params_present_no_profiles_in_cwd(
        self, mock_cwd, mock_load_profiles
    ):
        """Test _handle_cli_params_present when no profiles in current directory."""
        mock_load_profiles.return_value = ({}, {})
        mock_cwd.return_value = Path("/fake/cwd")

        cli_params = {"modules": ["base"], "version": 16.0}
        result = _handle_cli_params_present(None, cli_params)
        assert result == cli_params

    @patch("rodoo.cli.load_and_merge_profiles")
    @patch("pathlib.Path.cwd")
    @patch("rodoo.cli.Output.confirm")
    @patch("rodoo.cli.ConfigFile")
    @patch("rodoo.cli.typer.prompt")
    def test_handle_cli_params_present_update_profile(
        self,
        mock_prompt,
        mock_config_file_class,
        mock_confirm,
        mock_cwd,
        mock_load_profiles,
    ):
        """Test _handle_cli_params_present when updating existing profile."""
        profiles = {"test": {"modules": ["base"], "version": 15.0}}
        sources = {"test": Path("/fake/cwd/config.toml")}
        mock_load_profiles.return_value = (profiles, sources)
        mock_cwd.return_value = Path("/fake/cwd")
        mock_confirm.return_value = True
        mock_prompt.return_value = "test"

        mock_config_file = MagicMock()
        mock_config_file_class.return_value = mock_config_file
        mock_config_file.configs.get.return_value = {
            "test": {"modules": ["base"], "version": 15.0}
        }

        cli_params = {"modules": ["base", "sale"], "version": 16.0}
        result = _handle_cli_params_present("test", cli_params)

        # Should have updated the profile
        mock_config_file.update.assert_called_once()
        assert result == cli_params


class TestProcessCliArgs:
    def test_process_cli_args_no_params(self):
        """Test process_cli_args with no parameters."""
        with patch("rodoo.cli._handle_no_cli_params") as mock_handler:
            mock_handler.return_value = {"modules": ["base"], "version": 16.0}
            result = process_cli_args(None, {})
            assert result == {"modules": ["base"], "version": 16.0}

    def test_process_cli_args_with_params(self):
        """Test process_cli_args with parameters."""
        with patch("rodoo.cli._handle_cli_params_present") as mock_handler:
            mock_handler.return_value = {"modules": ["base"], "version": 16.0}
            result = process_cli_args(None, {"modules": ["base"], "version": 16.0})
            assert result == {"modules": ["base"], "version": 16.0}

    def test_process_cli_args_missing_required(self):
        """Test process_cli_args with missing required parameters."""
        with patch("rodoo.output.Output.error") as mock_error:
            with pytest.raises(Exit):
                process_cli_args(None, {"modules": ["base"]})
            mock_error.assert_called_once()


class TestConstructRunner:
    def test_construct_runner_basic(self):
        """Test _construct_runner with basic config."""
        config = {"modules": ["base"], "version": 16.0, "python_version": "3.10"}
        args = {}

        with patch("rodoo.cli.Runner") as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner

            _construct_runner(config, args)

            # Just check that Runner was called with the basic parameters
            call_args = mock_runner_class.call_args
            assert call_args[1]["modules"] == ["base"]
            assert call_args[1]["version"] == 16.0
            assert call_args[1]["python_version"] == "3.10"

    def test_construct_runner_with_module_in_args(self):
        """Test _construct_runner with module in args."""
        config = {"version": 16.0, "python_version": "3.10"}
        args = {"module": "base,sale"}

        with patch("rodoo.cli.Runner") as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner

            _construct_runner(config, args)

            # Should use modules from args
            call_args = mock_runner_class.call_args[1]
            assert call_args["modules"] == ["base", "sale"]
