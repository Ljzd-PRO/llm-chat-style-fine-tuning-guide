import csv
import json
from collections.abc import Iterable
from typing import Literal

import message_pb2
from models import NTGroupMsgModel

GROUP_ID = 123456789
"""目标群聊ID"""

JSON_PATH = "group_msg_table.json"
"""原始数据路径"""

CSV_WRITE_FILE = "group_msg.csv"
"""解析后数据生成路径"""
JSON_WRITE_FILE = "group_msg.json"
"""解析后数据生成路径"""


def load_group_msg(group_msg: NTGroupMsgModel, mode: Literal["csv", "json"]):
    message = message_pb2.Message()
    message.ParseFromString(group_msg.message_from_base64 if mode == "json" else group_msg.message_from_unicode)
    print(
        f"{group_msg.time}, "
        f"{group_msg.user_id}, "
        f"{group_msg.group_id}, "
        f"{group_msg.name}, "
        f"{message}"
    )
    group_msg_dict = group_msg.model_dump(mode="json", exclude={"raw_message"})
    group_msg_dict["message"] = [msg.messageText for msg in filter(lambda x: x.messageText, message.messages)]
    return group_msg_dict if group_msg_dict["message"] else None


def load_from_json():
    with open(JSON_PATH, encoding="utf-8") as f:
        rows = json.load(f)
        rows_filter: Iterable[NTGroupMsgModel] = filter(
            lambda x: x.group_id == GROUP_ID and x.raw_message,
            map(NTGroupMsgModel.model_validate, rows)
        )
        group_msg_list = list(
            filter(
                lambda x: x,
                map(
                    lambda x: load_group_msg(x, "json"),
                    rows_filter
                )
            )
        )

    with open(JSON_WRITE_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(group_msg_list, indent=4, ensure_ascii=False))

    with open(CSV_WRITE_FILE, "w", newline="", encoding="utf-8") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(map(lambda x: x.values(), group_msg_list))


load_from_json()
