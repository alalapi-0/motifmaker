#!/usr/bin/env python3
"""Interactive helper to inspect and optionally destroy VPS instances.

The script shells out to a provider CLI that must return JSON when listing
instances. By default we assume the DigitalOcean `doctl` tool is available.
Configure the following environment variables to adjust the commands:

- `MOTIFMAKER_VPS_LIST_CMD`: shell command that outputs JSON describing the
  instances you want to manage. Defaults to
  `"doctl compute droplet list --output json"`.
- `MOTIFMAKER_VPS_DESTROY_CMD`: shell command template used to destroy a single
  instance. The template can reference `{id}` and `{name}` placeholders and
  defaults to `"doctl compute droplet delete {id} --force"`.

The JSON is expected to be a list of objects. The script looks for common
identifier fields such as `id`, `ID`, `name`, and `Name`. If your CLI produces a
different structure you can pre-process it before passing to this script.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


DEFAULT_LIST_CMD = "doctl compute droplet list --output json"
DEFAULT_DESTROY_CMD = "doctl compute droplet delete {id} --force"


def _run_command(command: str) -> subprocess.CompletedProcess[str]:
    """Run *command* through the shell and return the completed process."""
    return subprocess.run(
        command,
        shell=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _normalise_field(record: Dict[str, Any], *names: str) -> Optional[Any]:
    for name in names:
        if name in record:
            return record[name]
    return None


def _format_instance(record: Dict[str, Any]) -> str:
    identifier = _normalise_field(record, "id", "ID", "droplet_id", "instance_id")
    name = _normalise_field(record, "name", "Name", "droplet_name", "instance_name")
    status = _normalise_field(record, "status", "Status", "state")
    region = _normalise_field(record, "region", "Region")
    details = []
    if name is not None:
        details.append(f"名称: {name}")
    if identifier is not None:
        details.append(f"ID: {identifier}")
    if status is not None:
        details.append(f"状态: {status}")
    if region is not None:
        details.append(f"区域: {region}")
    return "，".join(details) or json.dumps(record, ensure_ascii=False)


def _load_instances(raw_output: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as exc:  # pragma: no cover - interactive helper
        print("[错误] 解析实例列表失败：", exc)
        print("[提示] 运行的命令应返回 JSON。可以通过 MOTIFMAKER_VPS_LIST_CMD 环境变量重写。")
        print("\n原始输出如下：\n")
        print(raw_output)
        sys.exit(1)

    if isinstance(data, dict):
        # 某些 CLI 会返回形如 {"droplets": [...]} 的结构。
        for value in data.values():
            if isinstance(value, list):
                data = value
                break

    if not isinstance(data, list):
        print("[错误] 列表命令未返回数组结构，请检查命令或提供额外预处理。")
        sys.exit(1)

    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            cleaned.append(item)
    return cleaned


def _prompt_destroy(instances: List[Dict[str, Any]], destroy_template: str) -> None:
    try:
        choice = input("是否需要销毁某个实例？输入序号或直接回车跳过：").strip()
    except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive helper
        print("\n[信息] 已取消销毁操作。")
        return

    if not choice:
        print("[信息] 未执行销毁操作。")
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(instances)):
        print("[警告] 输入无效，未执行任何操作。")
        return

    index = int(choice) - 1
    record = instances[index]
    identifier = _normalise_field(
        record, "id", "ID", "droplet_id", "instance_id"
    )
    name = _normalise_field(
        record, "name", "Name", "droplet_name", "instance_name"
    )
    if identifier is None:
        print("[错误] 选定的记录缺少可识别的 ID，无法执行销毁。")
        return

    cmd = destroy_template.format(id=identifier, name=name or "")
    print(f"[信息] 正在执行销毁命令：{cmd}")
    result = _run_command(cmd)
    if result.returncode != 0:
        print("[错误] 销毁命令执行失败：")
        print(result.stderr or result.stdout)
        sys.exit(result.returncode)
    print("[完成] 销毁命令执行成功。请稍后在云控制台确认状态。")


def main() -> None:  # pragma: no cover - 交互式脚本不纳入自动化测试
    list_cmd = os.environ.get("MOTIFMAKER_VPS_LIST_CMD", DEFAULT_LIST_CMD)
    destroy_cmd = os.environ.get("MOTIFMAKER_VPS_DESTROY_CMD", DEFAULT_DESTROY_CMD)

    print("[信息] 正在检查当前账户下的 VPS 实例……")
    print(f"[调试] 使用的列出命令：{list_cmd}")
    result = _run_command(list_cmd)
    if result.returncode != 0:
        print("[错误] 列出实例的命令执行失败。")
        print(result.stderr or result.stdout)
        print("[提示] 可以通过设置 MOTIFMAKER_VPS_LIST_CMD 来适配不同云厂商。")
        sys.exit(result.returncode)

    raw_output = result.stdout.strip()
    if not raw_output:
        print("[信息] 命令未返回任何内容。确认命令是否正确或账户下没有实例。")
        return

    instances = _load_instances(raw_output)
    if not instances:
        print("[信息] 当前账户下没有检测到 VPS 实例。")
        return

    print("[信息] 检测到以下实例：")
    for idx, record in enumerate(instances, start=1):
        summary = _format_instance(record)
        print(f"  {idx}. {summary}")

    _prompt_destroy(instances, destroy_cmd)


if __name__ == "__main__":
    main()
