import os
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from core_utils import version_key, parse_targets  # noqa: E402
from filter_core import (  # noqa: E402
    create_reproducible_targz,
    filter_boards_txt,
    rename_packager,
    validate_targets,
)

SAMPLE_BOARDS_TXT = """\
# Comment line
menu.cpu=Processor
version=1.0

uno.name=Arduino Uno
uno.build.mcu=atmega328p
mega.name=Arduino Mega
mega.build.mcu=atmega2560
nano.name=Arduino Nano
nano.menu.cpu.atmega328=ATmega328P
""".splitlines(keepends=True)


def test_filter_keeps_targets_only():
    filtered, names, seen = filter_boards_txt(SAMPLE_BOARDS_TXT, {"uno"})
    text = "".join(filtered)
    assert "uno.name=Arduino Uno" in text
    assert "mega.name" not in text
    assert "nano.menu" not in text
    assert names == {"Arduino Uno"}
    assert seen == {"uno", "mega", "nano"}


def test_filter_preserves_comments_menus_globals():
    filtered, _, _ = filter_boards_txt(SAMPLE_BOARDS_TXT, {"uno"})
    text = "".join(filtered)
    assert "# Comment line" in text
    assert "menu.cpu=Processor" in text
    assert "version=1.0" in text  # 大域プロパティを誤削除しない


def test_filter_empty_targets_is_mirror():
    filtered, _, _ = filter_boards_txt(SAMPLE_BOARDS_TXT, set())
    assert filtered == SAMPLE_BOARDS_TXT


def test_validate_targets_fails_on_typo():
    _, _, seen = filter_boards_txt(SAMPLE_BOARDS_TXT, {"unoo"})
    with pytest.raises(SystemExit):
        validate_targets({"unoo"}, seen, "test")


def test_version_key_prerelease_older_than_release():
    assert version_key("3.0.0-rc1") < version_key("3.0.0")
    assert version_key("3.0.0") < version_key("3.0.1")
    # 旧実装で TypeError になっていた組み合わせが落ちないこと
    version_key("3.0.0-rc1")
    version_key("3.0.0-2")


def test_parse_targets():
    assert parse_targets("a, b ,c") == {"a", "b", "c"}
    assert parse_targets("") == set()


def test_rename_packager_updates_tool_deps():
    data = {"packages": [{
        "name": "esp32",
        "platforms": [{
            "toolsDependencies": [
                {"packager": "esp32", "name": "xtensa-gcc"},
                {"packager": "arduino", "name": "ctags"},
            ],
        }],
    }]}
    old, new = rename_packager(data, "trimmed")
    assert (old, new) == ("esp32", "esp32-trimmed")
    deps = data["packages"][0]["platforms"][0]["toolsDependencies"]
    assert deps[0]["packager"] == "esp32-trimmed"
    assert deps[1]["packager"] == "arduino"  # 外部参照は変更しない


def test_reproducible_targz_is_deterministic(tmp_path):
    src = tmp_path / "core"
    (src / "sub").mkdir(parents=True)
    (src / "boards.txt").write_text("uno.name=Uno\n")
    (src / "sub" / "a.txt").write_text("hello\n")
    script = src / "run.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)

    out1 = tmp_path / "a.tar.gz"
    out2 = tmp_path / "b.tar.gz"
    create_reproducible_targz(str(src), str(out1), "core")
    create_reproducible_targz(str(src), str(out2), "core")
    assert out1.read_bytes() == out2.read_bytes()

    with tarfile.open(out1) as tar:
        member = tar.getmember("core/run.sh")
        assert member.mode & 0o111  # 実行権限が保持される
        assert {m.name for m in tar.getmembers()} == {
            "core", "core/boards.txt", "core/run.sh", "core/sub", "core/sub/a.txt",
        }
