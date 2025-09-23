import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from rodoo.config import (
    ConfigFile,
    search_cwd,
    search_config,
    load_config,
    find_all_config_paths,
    load_and_merge_profiles,
    _sanity_check,
    create_profile,
    FILENAMES,
)
from rodoo.utils.exceptions import ConfigurationError


class TestConfigFile:
    def test_init_with_existing_file(self):
        """Test ConfigFile initialization with existing file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[profile.test]
modules = ["base"]
version = 16.0
"""
            )
            temp_path = Path(f.name)

        try:
            config_file = ConfigFile(temp_path)
            assert "profile" in config_file.configs
            assert "test" in config_file.configs["profile"]
        finally:
            temp_path.unlink()

    def test_init_with_nonexistent_file(self):
        """Test ConfigFile initialization with nonexistent file."""
        temp_path = Path("/nonexistent/file.toml")
        config_file = ConfigFile(temp_path)
        assert config_file.configs == {}

    def test_update_profile(self):
        """Test updating a profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test.toml"
            config_file = ConfigFile(config_path)

            new_profile = {
                "modules": ["base", "sale"],
                "version": 16.0,
                "python_version": "3.10",
            }

            config_file.update("test_profile", new_profile)
            assert config_file.configs["profile"]["test_profile"] == new_profile

    def test_write_config(self):
        """Test writing config to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test.toml"
            config_file = ConfigFile(config_path)

            config_file.configs = {
                "profile": {"test": {"modules": ["base"], "version": 16.0}}
            }

            config_file.write()
            assert config_path.exists()

            # Verify content
            content = config_path.read_text()
            assert "[profile.test]" in content
            assert 'modules = ["base"]' in content


class TestSearchFunctions:
    @patch("pathlib.Path.cwd")
    def test_search_cwd_found(self, mock_cwd):
        """Test search_cwd when config file is found."""
        mock_cwd.return_value = Path("/fake/cwd")
        with patch.object(Path, "exists", return_value=True):
            result = search_cwd()
            assert result == Path("/fake/cwd") / FILENAMES[0]

    @patch("pathlib.Path.cwd")
    def test_search_cwd_not_found(self, mock_cwd):
        """Test search_cwd when no config file is found."""
        mock_cwd.return_value = Path("/fake/cwd")
        with patch.object(Path, "exists", return_value=False):
            result = search_cwd()
            assert result is None

    def test_search_config_found(self):
        """Test search_config when config file is found."""
        with patch("rodoo.config.user_config_path", return_value=Path("/fake/config")):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(Path, "is_file", return_value=True):
                    with patch("rodoo.config.FILENAMES", [".rodoo.toml"]):
                        result = search_config()
                        assert result == Path("/fake/config") / ".rodoo.toml"

    @patch("platformdirs.user_config_path")
    def test_search_config_no_dir(self, mock_config_path):
        """Test search_config when config directory doesn't exist."""
        mock_config_path.return_value = Path("/fake/config")
        with patch.object(Path, "is_dir", return_value=False):
            result = search_config()
            assert result is None


class TestLoadConfig:
    def test_load_config_with_path(self):
        """Test load_config with specific path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[profile.test]
modules = ["base"]
version = 16.0
"""
            )
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert "profile" in config
            assert "test" in config["profile"]
        finally:
            temp_path.unlink()

    def test_load_config_without_path(self):
        """Test load_config without path (searches automatically)."""
        with patch("rodoo.config.search_cwd", return_value=None):
            with patch("rodoo.config.search_config", return_value=None):
                config = load_config(None)
                assert config == {}


class TestFindAllConfigPaths:
    @patch("pathlib.Path.cwd")
    @patch("platformdirs.user_config_path")
    def test_find_all_config_paths(self, mock_config_path, mock_cwd):
        """Test find_all_config_paths."""
        mock_cwd.return_value = Path("/fake/cwd")
        mock_config_path.return_value = Path("/fake/user_config")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(Path, "is_file", return_value=True):
                    paths = find_all_config_paths()
                    assert len(paths) == 4  # 2 in cwd, 2 in user config


class TestLoadAndMergeProfiles:
    def test_load_and_merge_profiles(self):
        """Test load_and_merge_profiles."""
        with patch("rodoo.config.find_all_config_paths", return_value=[]):
            profiles, sources = load_and_merge_profiles()
            assert profiles == {}
            assert sources == {}


class TestSanityCheck:
    def test_sanity_check_valid_config(self):
        """Test _sanity_check with valid config."""
        config = {"profile": {"test": {"modules": ["base"], "version": 16.0}}}
        # Should not raise
        _sanity_check(config)

    def test_sanity_check_invalid_config_type(self):
        """Test _sanity_check with invalid config type."""
        with pytest.raises(
            ConfigurationError, match="Configuration must be a dictionary"
        ):
            _sanity_check("invalid")

    def test_sanity_check_invalid_profile_type(self):
        """Test _sanity_check with invalid profile type."""
        config = {"profile": "invalid"}
        with pytest.raises(ConfigurationError, match="Profiles must be a dictionary"):
            _sanity_check(config)

    def test_sanity_check_invalid_version_type(self):
        """Test _sanity_check with invalid version type."""
        config = {
            "profile": {
                "test": {
                    "version": "16.0"  # Should be number
                }
            }
        }
        with pytest.raises(
            ConfigurationError, match="Version in profile 'test' must be a number"
        ):
            _sanity_check(config)


class TestCreateProfile:
    @patch("rodoo.config.typer.prompt")
    @patch("rodoo.config.typer.confirm")
    @patch("rodoo.config.ConfigFile")
    def test_create_profile_basic(
        self, mock_config_file_class, mock_confirm, mock_prompt
    ):
        """Test create_profile with basic inputs."""
        # Mock user inputs
        mock_prompt.side_effect = [
            "test_profile",  # profile name
            "base,sale",  # modules
            "16.0",  # version
            "3.10",  # python version
            "",  # db name (empty)
            "",  # paths (empty)
            "",  # extra_params
            "",  # python_packages
        ]
        mock_confirm.side_effect = [
            False,  # enterprise
            False,  # force_install
            False,  # force_update
            False,  # save_in_cwd
        ]

        # Mock ConfigFile
        mock_config_file = MagicMock()
        mock_config_file_class.return_value = mock_config_file

        profile_name, profile, config_path = create_profile()

        assert profile_name == "test_profile"
        assert profile["modules"] == ["base", "sale"]
        assert profile["version"] == 16.0
        assert profile["python_version"] == "3.10"
