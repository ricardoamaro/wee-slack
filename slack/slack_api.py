from __future__ import annotations

import json
from itertools import chain
from typing import TYPE_CHECKING, Iterable, Mapping, Optional, Sequence, Union
from urllib.parse import urlencode

from slack.error import SlackApiError
from slack.http import http_request
from slack.shared import shared
from slack.slack_message import SlackTs
from slack.task import gather
from slack.util import chunked

if TYPE_CHECKING:
    from slack_api.slack_bots_info import SlackBotInfoResponse, SlackBotsInfoResponse
    from slack_api.slack_common import SlackGenericResponse
    from slack_api.slack_conversations_history import SlackConversationsHistoryResponse
    from slack_api.slack_conversations_info import SlackConversationsInfoResponse
    from slack_api.slack_conversations_members import SlackConversationsMembersResponse
    from slack_api.slack_conversations_replies import SlackConversationsRepliesResponse
    from slack_api.slack_rtm_connect import SlackRtmConnectResponse
    from slack_api.slack_usergroups_info import SlackUsergroupsInfoResponse
    from slack_api.slack_users_conversations import SlackUsersConversationsResponse
    from slack_api.slack_users_info import SlackUserInfoResponse, SlackUsersInfoResponse
    from slack_api.slack_users_prefs import SlackUsersPrefsGetResponse
    from slack_edgeapi.slack_usergroups_info import SlackEdgeUsergroupsInfoResponse
    from slack_edgeapi.slack_users_search import SlackUsersSearchResponse
    from typing_extensions import Literal, assert_never

    from slack.slack_conversation import SlackConversation
    from slack.slack_workspace import SlackWorkspace

Params = Mapping[str, Union[str, int, bool]]
EdgeParams = Mapping[
    str, Union[str, int, bool, Sequence[str], Sequence[int], Sequence[bool]]
]


class SlackApiCommon:
    def __init__(self, workspace: SlackWorkspace):
        self.workspace = workspace

    def _get_request_options(self):
        return {
            "useragent": f"wee_slack {shared.SCRIPT_VERSION}",
            "httpheader": f"Authorization: Bearer {self.workspace.config.api_token.value}",
            "cookie": self.workspace.config.api_cookies.value,  # TODO: url_encode_if_not_encoded
        }


class SlackEdgeApi(SlackApiCommon):
    @property
    def is_available(self) -> bool:
        return self.workspace.token_type == "session"

    async def _fetch_edgeapi(self, method: str, params: EdgeParams = {}):
        enterprise_id_part = (
            f"{self.workspace.enterprise_id}/" if self.workspace.enterprise_id else ""
        )
        url = f"https://edgeapi.slack.com/cache/{enterprise_id_part}{self.workspace.id}/{method}"
        options = self._get_request_options()
        options["postfields"] = json.dumps(params)
        options["httpheader"] += "\nContent-Type: application/json"
        response = await http_request(
            url,
            options,
            self.workspace.config.network_timeout.value * 1000,
        )
        return json.loads(response)

    async def fetch_usergroups_info(self, usergroup_ids: Sequence[str]):
        method = "usergroups/info"
        params: EdgeParams = {"ids": usergroup_ids}
        response: SlackEdgeUsergroupsInfoResponse = await self._fetch_edgeapi(
            method, params
        )
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_users_search(self, query: str):
        method = "users/search"
        params: EdgeParams = {
            "include_profile_only_users": True,
            "query": query,
            "count": 25,
            "fuzz": 1,
            "uax29_tokenizer": False,
            "filter": "NOT deactivated",
        }
        response: SlackUsersSearchResponse = await self._fetch_edgeapi(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response


class SlackApi(SlackApiCommon):
    def __init__(self, workspace: SlackWorkspace):
        super().__init__(workspace)
        self.edgeapi = SlackEdgeApi(workspace)

    async def _fetch(self, method: str, params: Params = {}):
        url = f"https://api.slack.com/api/{method}"
        options = self._get_request_options()
        options["postfields"] = urlencode(params)
        response = await http_request(
            url,
            options,
            self.workspace.config.network_timeout.value * 1000,
        )
        return json.loads(response)

    async def _fetch_list(
        self,
        method: str,
        list_key: str,
        params: Params = {},
        limit: Optional[int] = None,
    ):
        cur_limit = 1000 if limit is None or limit > 1000 else limit
        response = await self._fetch(method, {**params, "limit": cur_limit})
        remaining = limit - cur_limit if limit is not None else None
        next_cursor = response.get("response_metadata", {}).get("next_cursor")
        if (remaining is None or remaining > 0) and next_cursor and response["ok"]:
            new_params = {**params, "cursor": next_cursor}
            next_pages = await self._fetch_list(method, list_key, new_params, remaining)
            response[list_key].extend(next_pages[list_key])
            return response
        return response

    async def fetch_rtm_connect(self):
        method = "rtm.connect"
        response: SlackRtmConnectResponse = await self._fetch(method)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response)
        return response

    async def fetch_users_get_prefs(self, prefs: Optional[str] = None):
        method = "users.prefs.get"
        params: Params = {"prefs": prefs} if prefs else {}
        response: SlackUsersPrefsGetResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response)
        return response

    async def fetch_conversations_history(self, conversation: SlackConversation):
        method = "conversations.history"
        params: Params = {"channel": conversation.id}
        response: SlackConversationsHistoryResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_conversations_history_after(
        self, conversation: SlackConversation, after: SlackTs
    ):
        method = "conversations.history"
        params: Params = {
            "channel": conversation.id,
            "oldest": after,
            "inclusive": False,
        }
        response: SlackConversationsHistoryResponse = await self._fetch_list(
            method, "messages", params
        )
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_conversations_replies(
        self, conversation: SlackConversation, parent_message_ts: SlackTs
    ):
        method = "conversations.replies"
        params: Params = {
            "channel": conversation.id,
            "ts": parent_message_ts,
        }
        response: SlackConversationsRepliesResponse = await self._fetch_list(
            method, "messages", params
        )
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_conversations_info(self, conversation_id: str):
        method = "conversations.info"
        params: Params = {"channel": conversation_id}
        response: SlackConversationsInfoResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_conversations_members(
        self,
        conversation: SlackConversation,
        limit: Optional[int] = None,
    ):
        method = "conversations.members"
        params: Params = {"channel": conversation.id}
        response: SlackConversationsMembersResponse = await self._fetch_list(
            method, "members", params, limit
        )
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_users_conversations(
        self,
        types: str,
        exclude_archived: bool = True,
        limit: Optional[int] = None,
    ):
        method = "users.conversations"
        params: Params = {
            "types": types,
            "exclude_archived": exclude_archived,
        }
        response: SlackUsersConversationsResponse = await self._fetch_list(
            method,
            "channels",
            params,
            limit,
        )
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_user_info(self, user_id: str):
        method = "users.info"
        params: Params = {"user": user_id}
        response: SlackUserInfoResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def _fetch_users_info_without_splitting(self, user_ids: Iterable[str]):
        method = "users.info"
        params: Params = {"users": ",".join(user_ids)}
        response: SlackUsersInfoResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_users_info(self, user_ids: Iterable[str]):
        responses = await gather(
            *(
                self._fetch_users_info_without_splitting(user_ids_batch)
                for user_ids_batch in chunked(user_ids, 1000)
            )
        )
        users = list(chain(*(response["users"] for response in responses)))
        response: SlackUsersInfoResponse = {"ok": True, "users": users}
        return response

    async def fetch_bot_info(self, bot_id: str):
        method = "bots.info"
        params: Params = {"bot": bot_id}
        response: SlackBotInfoResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_bots_info(self, bot_ids: Iterable[str]):
        method = "bots.info"
        params: Params = {"bots": ",".join(bot_ids)}
        response: SlackBotsInfoResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def fetch_usergroups_list(self):
        method = "usergroups.list"
        response: SlackUsergroupsInfoResponse = await self._fetch(method)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response)
        return response

    async def conversations_mark(self, conversation: SlackConversation, ts: SlackTs):
        method = "conversations.mark"
        params: Params = {"channel": conversation.id, "ts": ts}
        response: SlackGenericResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def subscriptions_thread_mark(
        self, conversation: SlackConversation, thread_ts: SlackTs, ts: SlackTs
    ):
        method = "subscriptions.thread.mark"
        params: Params = {
            "channel": conversation.id,
            "thread_ts": thread_ts,
            "ts": ts,
            "read": 1,
        }
        response: SlackGenericResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def chat_post_message(
        self,
        conversation: SlackConversation,
        text: str,
        thread_ts: Optional[SlackTs] = None,
    ):
        method = "chat.postMessage"
        params: Params = {
            "channel": conversation.id,
            "text": text,
            "as_user": True,
            "link_names": True,
        }
        if thread_ts is not None:
            params["thread_ts"] = thread_ts
        response: SlackGenericResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response

    async def reactions_change(
        self,
        conversation: SlackConversation,
        ts: SlackTs,
        name: str,
        change_type: Literal["+", "-"],
    ):
        method = (
            "reactions.add"
            if change_type == "+"
            else "reactions.remove"
            if change_type == "-"
            else assert_never(change_type)
        )
        params: Params = {
            "channel": conversation.id,
            "timestamp": ts,
            "name": name,
        }
        response: SlackGenericResponse = await self._fetch(method, params)
        if response["ok"] is False:
            raise SlackApiError(self.workspace, method, response, params)
        return response
