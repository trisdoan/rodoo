import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from rodoo.runner import Runner
from rodoo.exceptions import UserError


class TestRunnerInit:
    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_runner_init_basic(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test Runner __post_init__ with basic parameters."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = False
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")

        assert runner.modules == ["base"]
        assert runner.version == 16.0
        assert runner.python_version == "3.10"
        assert runner.db == "v16_base"
        assert runner.venv == "odoo-16.0-py3.10"

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_runner_init_existing_venv(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_glob,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test Runner __post_init__ with existing venv detection."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True
        mock_get_paths.return_value = []

        # Mock existing venvs
        mock_venv_path = MagicMock()
        mock_venv_path.name = "odoo-16.0-py3.10"
        mock_glob.return_value = [mock_venv_path]

        with patch("rodoo.output.Output.info") as mock_info:
            runner = Runner(
                modules=["base"],
                version=16.0,
                python_version=None,  # Should detect from existing venv
            )

            assert runner.python_version == "3.10"
            mock_info.assert_called_once()


class TestRunnerSetupOdooSource:
    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.subprocess.run")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_setup_odoo_source_new(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_sanity,
        mock_run,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _setup_odoo_source for new repository."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = False
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")

        with patch.object(runner, "_create_progress"):
            # Reset call count to ignore calls during initialization
            mock_run.reset_mock()
            runner._setup_odoo_source()

            # Should call git worktree add
            assert any(
                "worktree" in str(call) and "add" in str(call)
                for call in mock_run.call_args_list
            )

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_setup_odoo_source_existing(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_sanity,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _setup_odoo_source when source already exists."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")

        # Should not do anything if source exists
        runner._setup_odoo_source()


class TestRunnerEnsureBareRepo:
    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_ensure_bare_repo_new(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_run,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _ensure_bare_repo for new bare repository."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = False
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        runner._ensure_bare_repo()

        # Should call git clone --bare
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == [
            "git",
            "clone",
            "--bare",
            "git@github.com:odoo/odoo.git",
            str(runner.app_dir / "odoo.git"),
        ]

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_ensure_bare_repo_existing(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _ensure_bare_repo when repository already exists."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        runner._ensure_bare_repo()

        # Should not call subprocess.run


class TestRunnerIsEnvReady:
    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    @patch("json.loads")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_is_env_ready_venv_not_exists(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_json_loads,
        mock_run,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _is_env_ready when venv doesn't exist."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = False
        mock_get_paths.return_value = []

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        result = runner._is_env_ready()

        assert result is False

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    @patch("json.loads")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_is_env_ready_venv_exists_odoo_installed(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_json_loads,
        mock_run,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _is_env_ready when venv exists and odoo is installed."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True
        mock_get_paths.return_value = []

        mock_run.return_value = MagicMock(returncode=0, stdout='[{"name": "odoo"}]')
        mock_json_loads.return_value = [{"name": "odoo"}]

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        result = runner._is_env_ready()

        assert result is True

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._get_module_paths")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_is_env_ready_venv_exists_odoo_not_installed(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_get_paths,
        mock_setup_source,
        mock_sanity,
        mock_run,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _is_env_ready when venv exists but odoo is not installed."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True
        mock_get_paths.return_value = []

        mock_run.return_value = MagicMock(returncode=0, stdout='[{"name": "pip"}]')

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        result = runner._is_env_ready()

        assert result is False


class TestRunnerSanityCheck:
    def test_sanity_check_missing_python_version(self):
        """Test _sanity_check with missing python version."""
        # Create a minimal runner instance with mocked dependencies
        with (
            patch("rodoo.runner.Runner._setup_odoo_source"),
            patch("rodoo.runner.Runner._is_env_ready"),
            patch("rodoo.runner.Runner._install_system_packages"),
            patch("rodoo.runner.Runner._setup_python_env"),
            patch("rodoo.runner.Runner._install_extra_python_packages"),
            patch("rodoo.runner.Runner._prepare_odoo_cli_params"),
        ):
            runner = Runner.__new__(Runner)
            runner.modules = ["base"]
            runner.version = 16.0
            runner.python_version = "3.10"
            runner.modules_paths = []  # Empty to skip module checking

            # Set python_version to None to test the check
            runner.python_version = None

            with pytest.raises(UserError, match="Python version is required"):
                runner._sanity_check()

    def test_sanity_check_no_modules(self):
        """Test _sanity_check with no modules."""
        # Create a minimal runner instance with mocked dependencies
        with (
            patch("rodoo.runner.Runner._setup_odoo_source"),
            patch("rodoo.runner.Runner._is_env_ready"),
            patch("rodoo.runner.Runner._install_system_packages"),
            patch("rodoo.runner.Runner._setup_python_env"),
            patch("rodoo.runner.Runner._install_extra_python_packages"),
            patch("rodoo.runner.Runner._prepare_odoo_cli_params"),
        ):
            runner = Runner.__new__(Runner)
            runner.modules = []
            runner.version = 16.0
            runner.python_version = "3.10"
            runner.modules_paths = []  # Empty to skip module checking

            with pytest.raises(UserError, match="No module passed"):
                runner._sanity_check()

    def test_sanity_check_missing_module(self):
        """Test _sanity_check with missing module dependency."""
        # Create a minimal runner instance with mocked dependencies
        with (
            patch("rodoo.runner.Runner._setup_odoo_source"),
            patch("rodoo.runner.Runner._is_env_ready"),
            patch("rodoo.runner.Runner._install_system_packages"),
            patch("rodoo.runner.Runner._setup_python_env"),
            patch("rodoo.runner.Runner._install_extra_python_packages"),
            patch("rodoo.runner.Runner._prepare_odoo_cli_params"),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir"),
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open"),
            patch("ast.literal_eval", return_value={"depends": ["base"]}),
        ):
            runner = Runner.__new__(Runner)
            runner.modules = ["sale"]
            runner.version = 16.0
            runner.python_version = "3.10"

            # Mock modules_paths with a fake path that has no "base" module
            mock_path = MagicMock()
            mock_path.is_dir.return_value = True
            mock_path.iterdir.return_value = []  # No modules found
            runner.modules_paths = [mock_path]

            with pytest.raises(UserError, match="not found"):
                runner._sanity_check()


class TestRunnerGetModulePaths:
    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_get_module_paths_basic(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_setup_source,
        mock_sanity,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _get_module_paths with basic setup."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True

        runner = Runner(modules=["base"], version=16.0, python_version="3.10")
        paths = runner._get_module_paths()

        expected_paths = [
            runner.odoo_src_path / "addons",
            runner.odoo_src_path / "odoo" / "addons",
        ]
        assert len(paths) == 2
        assert str(paths[0]) == str(expected_paths[0])
        assert str(paths[1]) == str(expected_paths[1])

    @patch("platformdirs.user_config_path")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("rodoo.runner.Runner._sanity_check")
    @patch("rodoo.runner.Runner._setup_odoo_source")
    @patch("rodoo.runner.Runner._is_env_ready")
    @patch("rodoo.runner.Runner._install_system_packages")
    @patch("rodoo.runner.Runner._setup_python_env")
    @patch("rodoo.runner.Runner._install_extra_python_packages")
    @patch("rodoo.runner.Runner._prepare_odoo_cli_params")
    def test_get_module_paths_with_enterprise(
        self,
        mock_prepare_cli,
        mock_install_extra,
        mock_setup_python,
        mock_install_system,
        mock_is_env_ready,
        mock_setup_source,
        mock_sanity,
        mock_exists,
        mock_mkdir,
        mock_config_path,
    ):
        """Test _get_module_paths with enterprise enabled."""
        mock_config_path.return_value = Path("/fake/config")
        mock_exists.return_value = True

        runner = Runner(
            modules=["base"], version=16.0, python_version="3.10", enterprise=True
        )
        paths = runner._get_module_paths()

        assert len(paths) == 3
        assert str(paths[2]) == str(runner.enterprise_src_path)


class TestRunnerPrepareOdooCliParams:
    def test_prepare_odoo_cli_params_basic(self):
        """Test _prepare_odoo_cli_params with basic parameters."""
        # Create a minimal runner instance
        with (
            patch("rodoo.runner.Runner._setup_odoo_source"),
            patch("rodoo.runner.Runner._is_env_ready"),
            patch("rodoo.runner.Runner._install_system_packages"),
            patch("rodoo.runner.Runner._setup_python_env"),
            patch("rodoo.runner.Runner._install_extra_python_packages"),
            patch("rodoo.runner.Runner._sanity_check"),
            patch("rodoo.runner.Runner._get_module_paths", return_value=[]),
        ):
            runner = Runner.__new__(Runner)
            runner.modules = ["base", "sale"]
            runner.version = 16.0
            runner.python_version = "3.10"
            runner.db = "test_db"
            runner.force_install = True
            runner.force_update = False
            runner.extra_params = "--debug"
            runner.load = None
            runner.modules_paths = []
            runner.db_host = None
            runner.db_user = None
            runner.db_password = None
            runner.workers = 0
            runner.max_cron_threads = 0
            runner.limit_time_cpu = 3600
            runner.limit_time_real = 3600
            runner.http_interface = "localhost"

            params = runner._prepare_odoo_cli_params()

            assert "-d" in params
            assert "test_db" in params
            assert "--addons-path" in params
            assert "-i" in params
            assert "base,sale" in params
            assert "--debug" in params

    def test_prepare_odoo_cli_params_with_load(self):
        """Test _prepare_odoo_cli_params with load parameter."""
        # Create a minimal runner instance
        with (
            patch("rodoo.runner.Runner._setup_odoo_source"),
            patch("rodoo.runner.Runner._is_env_ready"),
            patch("rodoo.runner.Runner._install_system_packages"),
            patch("rodoo.runner.Runner._setup_python_env"),
            patch("rodoo.runner.Runner._install_extra_python_packages"),
            patch("rodoo.runner.Runner._sanity_check"),
            patch("rodoo.runner.Runner._get_module_paths", return_value=[]),
        ):
            runner = Runner.__new__(Runner)
            runner.modules = ["base"]
            runner.version = 16.0
            runner.python_version = "3.10"
            runner.load = ["base", "web"]
            runner.modules_paths = []
            runner.db = "test_db"
            runner.force_install = False
            runner.force_update = False
            runner.extra_params = None
            runner.db_host = None
            runner.db_user = None
            runner.db_password = None
            runner.workers = 0
            runner.max_cron_threads = 0
            runner.limit_time_cpu = 3600
            runner.limit_time_real = 3600
            runner.http_interface = "localhost"

            params = runner._prepare_odoo_cli_params()

            assert "--load" in params
            load_index = params.index("--load")
            assert params[load_index + 1] == "base,web"
