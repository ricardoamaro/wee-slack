from __future__ import annotations

from typing import Dict, Generic, List, Optional

from slack_api.slack_error import SlackErrorResponse
from typing_extensions import Literal, NotRequired, TypedDict, TypeVar, final

T = TypeVar("T")

@final
class SlackProfileField(TypedDict):
    value: str
    alt: str

@final
class SlackProfileStatusEmojiDisplayInfo(TypedDict):
    emoji_name: str
    display_url: str
    unicode: str

class SlackProfileCommon(TypedDict):
    title: NotRequired[Optional[str]]
    phone: NotRequired[Optional[str]]
    skype: NotRequired[Optional[str]]
    first_name: NotRequired[Optional[str]]
    last_name: NotRequired[Optional[str]]
    real_name: NotRequired[Optional[str]]
    real_name_normalized: NotRequired[Optional[str]]
    display_name: NotRequired[Optional[str]]
    display_name_normalized: NotRequired[Optional[str]]
    fields: NotRequired[Optional[Dict[str, SlackProfileField]]]
    status_text: NotRequired[Optional[str]]
    status_emoji: NotRequired[Optional[str]]
    status_emoji_display_info: NotRequired[
        Optional[List[SlackProfileStatusEmojiDisplayInfo]]
    ]
    status_expiration: NotRequired[Optional[int]]
    avatar_hash: NotRequired[Optional[str]]
    image_original: NotRequired[str]
    is_custom_image: NotRequired[Optional[bool]]
    huddle_state: NotRequired[Optional[str]]
    huddle_state_expiration_ts: NotRequired[Optional[int]]
    image_24: str
    image_32: str
    image_48: str
    image_72: str
    image_192: str
    image_512: str
    image_1024: NotRequired[str]
    status_text_canonical: NotRequired[Optional[str]]
    team: str

@final
class SlackProfilePerson(SlackProfileCommon):
    email: NotRequired[Optional[str]]

@final
class SlackProfileBot(SlackProfileCommon):
    api_app_id: NotRequired[Optional[str]]
    always_active: NotRequired[Optional[bool]]
    bot_id: NotRequired[Optional[str]]
    image_1024: str

SlackProfile = SlackProfilePerson | SlackProfileBot

@final
class SlackEnterpriseUser(TypedDict):
    id: str
    enterprise_id: str
    enterprise_name: str
    is_admin: bool
    is_owner: bool
    is_primary_owner: bool
    teams: List[str]

class SlackUserInfoCommon(TypedDict):
    id: str
    team_id: NotRequired[str]
    name: str
    deleted: NotRequired[bool]
    color: str
    real_name: NotRequired[str]
    tz: NotRequired[str]
    tz_label: NotRequired[str]
    tz_offset: NotRequired[int]
    is_admin: NotRequired[bool]
    is_owner: NotRequired[bool]
    is_primary_owner: NotRequired[bool]
    is_restricted: NotRequired[bool]
    is_ultra_restricted: NotRequired[bool]
    is_app_user: bool
    updated: int
    is_email_confirmed: NotRequired[bool]
    who_can_share_contact_card: str
    enterprise_user: NotRequired[SlackEnterpriseUser]
    enterprise_id: NotRequired[str]
    presence: NotRequired[Literal["active"]]

@final
class SlackUserInfoPerson(SlackUserInfoCommon):
    profile: SlackProfilePerson
    is_bot: Literal[False]
    is_stranger: NotRequired[bool]
    has_2fa: bool

@final
class SlackUserInfoBot(SlackUserInfoCommon):
    profile: SlackProfileBot
    is_bot: Literal[True]
    is_workflow_bot: NotRequired[bool]

SlackUserInfo = SlackUserInfoPerson | SlackUserInfoBot

@final
class SlackUserInfoSuccessResponse(TypedDict, Generic[T]):
    ok: Literal[True]
    user: T

SlackUserInfoPersonResponse = (
    SlackUserInfoSuccessResponse[SlackUserInfoPerson] | SlackErrorResponse
)
SlackUserInfoBotResponse = (
    SlackUserInfoSuccessResponse[SlackUserInfoBot] | SlackErrorResponse
)
SlackUserInfoResponse = SlackUserInfoSuccessResponse[SlackUserInfo] | SlackErrorResponse

@final
class SlackUsersInfoSuccessResponse(TypedDict, Generic[T]):
    ok: Literal[True]
    users: List[T]

SlackUsersInfoPersonResponse = (
    SlackUsersInfoSuccessResponse[SlackUserInfoPerson] | SlackErrorResponse
)
SlackUsersInfoBotResponse = (
    SlackUsersInfoSuccessResponse[SlackUserInfoBot] | SlackErrorResponse
)
SlackUsersInfoResponse = (
    SlackUsersInfoSuccessResponse[SlackUserInfo] | SlackErrorResponse
)
