# from typing import Optional, List
from cryptography.fernet import Fernet
from dataclasses import dataclass, asdict


@dataclass
class JSONSerializable:
    def to_dict(self):
        return asdict(self)


@dataclass
class ConnectedNode(JSONSerializable):
    address: str
    symmetric_key: str
    symmetric_key_uuid: str
    fernet: Fernet


@dataclass
class NodeData(JSONSerializable):
    hotkey: str
    worker_id: str
    uid: int
    boot_time: int
    last_operation_time: int
    current_time: int
    twitter_auth_errors: int
    twitter_errors: int
    twitter_ratelimit_errors: int
    twitter_returned_other: int
    twitter_returned_profiles: int
    twitter_returned_tweets: int
    twitter_scrapes: int
    web_errors: int
    web_success: int
    timestamp: int
