import ast
import csv
import json
import re
from datetime import datetime

USER_ID = "123456789"
"""目标用户ID"""
CSV_PATH = r"group_msg.csv"
"""聊天记录CSV路径"""


def process_chat_content(content_str, nickname_regex):
    """处理聊天内容并提取被@的昵称"""
    try:
        # 解析并合并聊天片段
        content_list = ast.literal_eval(content_str)
        merged_content = ', '.join(str(item) for item in content_list)
    except (SyntaxError, ValueError, TypeError):
        return '', []

    # 提取被@的昵称（保留原始格式）
    raw_mentions = re.findall(r'@([^\s@]+)', merged_content)  # 原始提取逻辑
    mentioned_nicknames = list(set(raw_mentions))

    # 删除@提及并清理内容
    cleaned_content = nickname_regex.sub('', merged_content)
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()

    return cleaned_content, mentioned_nicknames


def main():
    # 读取原始数据
    with open(CSV_PATH, 'r', encoding='gbk') as csvfile:
        rows = list(csv.reader(csvfile))

    # 构建昵称正则表达式
    all_nicknames = {row[2].strip() for row in rows if row[2].strip()}
    sorted_nicknames = sorted(all_nicknames, key=lambda x: len(x), reverse=True)
    nickname_regex = re.compile(
        r'@(' + '|'.join(re.escape(n) for n in sorted_nicknames) + r')(?=\W|$)',
        flags=re.UNICODE
    )

    # 预处理：解析时间并排序
    parsed_rows = []
    for row in rows:
        try:
            dt = datetime.strptime(row[1], '%Y-%m-%dT%H:%M:%SZ')
            parsed_rows.append((dt, row))
        except ValueError:
            continue
    parsed_rows.sort(key=lambda x: x[0])  # 按时间升序排序

    # 主处理逻辑
    last_user_msg = {}  # 存储用户最后有效消息
    output_data = []

    for dt, row in parsed_rows:
        user_id = row[3]
        if user_id == USER_ID:  # 模型回答
            content_str = row[4]
            processed_content, mentions = process_chat_content(content_str, nickname_regex)

            if not mentions:  # 跳过无@提及的回答
                continue

            # 为每个被@用户生成训练样本
            for nickname in mentions:
                if nickname in last_user_msg:
                    output_data.append({
                        "instruction": last_user_msg[nickname],
                        "input": "",
                        "output": processed_content
                    })
        else:  # 普通用户消息
            nickname = row[2].strip()
            content_str = row[4]
            processed_content, _ = process_chat_content(content_str, nickname_regex)

            if nickname and processed_content:
                last_user_msg[nickname] = processed_content

    # 保存结果
    with open(r"proceed-group-msg_user-at.json", 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
