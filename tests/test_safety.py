from olive.safety import is_dangerous_command


def test_rm_rf_root_is_dangerous():
    assert is_dangerous_command("rm -rf /") is not None


def test_rm_rf_home_is_dangerous():
    assert is_dangerous_command("rm -rf ~") is not None


def test_rm_rf_wildcard_is_dangerous():
    assert is_dangerous_command("rm -rf *") is not None


def test_remove_item_recurse_force_drive_root_is_dangerous():
    assert is_dangerous_command("Remove-Item -Recurse -Force C:\\") is not None


def test_remove_item_force_recurse_reordered_is_dangerous():
    assert is_dangerous_command("Remove-Item -Force -Recurse C:\\") is not None


def test_del_drive_root_is_dangerous():
    assert is_dangerous_command("del /s /q C:\\") is not None


def test_format_drive_is_dangerous():
    assert is_dangerous_command("format C:") is not None


def test_mkfs_is_dangerous():
    assert is_dangerous_command("mkfs.ext4 /dev/sda1") is not None


def test_dd_to_dev_is_dangerous():
    assert is_dangerous_command("dd if=/dev/zero of=/dev/sda") is not None


def test_fork_bomb_is_dangerous():
    assert is_dangerous_command(":(){ :|:& };:") is not None


def test_normal_test_command_is_safe():
    assert is_dangerous_command("pytest") is None


def test_normal_python_invocation_is_safe():
    assert is_dangerous_command('"C:\\Python\\python.exe" calculator.py 3 5') is None


def test_npm_build_is_safe():
    assert is_dangerous_command("npm run build") is None


def test_rm_rf_of_a_specific_build_dir_is_safe():
    assert is_dangerous_command("rm -rf ./dist") is None
    assert is_dangerous_command("rm -rf build/") is None


def test_remove_item_on_a_specific_subfolder_is_safe():
    assert is_dangerous_command("Remove-Item -Recurse -Force .\\dist") is None


def test_git_clean_is_safe():
    assert is_dangerous_command("git clean -fdx") is None


def test_reason_mentions_the_command():
    reason = is_dangerous_command("rm -rf /")
    assert reason is not None
    assert "rm -rf /" in reason
