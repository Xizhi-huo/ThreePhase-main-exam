"""设置 / 修改 ThreePhase 考核系统的访问密码。

运行一次，按提示输入新密码，会把密码的 SHA-256 哈希写入 access_password.hash。
主程序代码无需改动、无需重新打包；分发时把 access_password.hash 与程序放在同一目录即可。

用法：
    python set_access_password.py
"""

from __future__ import annotations

import getpass
import hashlib
import sys
from pathlib import Path

HASH_FILE = Path(__file__).resolve().parent / "access_password.hash"


def main() -> int:
    pwd = getpass.getpass("设置新的访问密码: ")
    if not pwd:
        print("密码不能为空，已取消。")
        return 1
    if pwd != getpass.getpass("再次输入确认: "):
        print("两次输入不一致，已取消。")
        return 1

    digest = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
    HASH_FILE.write_text(
        "# ThreePhase 访问密码哈希，请用 set_access_password.py 修改，勿手改\n"
        f"{digest}\n",
        encoding="utf-8",
    )
    print(f"已写入 {HASH_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
