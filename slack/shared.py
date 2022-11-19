from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

if TYPE_CHECKING:
    from slack.api import SlackWorkspace
    from slack.config import SlackConfig
    from slack.task import Task


class Shared:
    def __init__(self):
        self.SCRIPT_NAME = "slack"
        self.SCRIPT_VERSION = "3.0.0"

        self.weechat_version: int
        self.weechat_callbacks: Dict[str, Any]
        self.active_tasks: Dict[str, Task[Any]] = {}
        self.active_responses: Dict[str, Tuple[Any, ...]] = {}
        self.workspaces: Dict[str, SlackWorkspace] = {}
        self.config: SlackConfig


shared = Shared()
