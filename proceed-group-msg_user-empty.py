import ast
import csv
import json
import re

USER_ID = "123456789"
"""目标用户ID"""
CSV_PATH = r"group_msg.csv"
"""聊天记录CSV路径"""


def process_chat_content(content_str, nickname_regex):
    """处理聊天内容：合并片段、删除@提及、清理空格"""
    try:
        # 解析原始内容列表
        content_list = ast.literal_eval(content_str)
        merged_content = ', '.join([str(item) for item in content_list])

        # 删除@用户昵称
        cleaned_content = nickname_regex.sub('', merged_content)

        # 清理多余空格
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
        return cleaned_content
    except (SyntaxError, ValueError, TypeError):
        return ''


def main():
    # 读取CSV数据并收集所有昵称
    with open(CSV_PATH, 'r', encoding='gbk') as csvfile:
        rows = list(csv.reader(csvfile))

    # 获取去重后的昵称集合
    nicknames = {row[2] for row in rows if row[2].strip()}

    # 构建正则表达式（按昵称长度降序排列）
    sorted_nicknames = sorted(nicknames, key=lambda x: len(x), reverse=True)
    escaped_nicknames = [re.escape(nick) for nick in sorted_nicknames]
    nickname_regex = re.compile(
        r'@(' + '|'.join(escaped_nicknames) + r')(?=\W|$)',
        flags=re.UNICODE
    )

    # 处理聊天记录
    output_data = []
    for row in rows:
        user_id = row[3]
        if user_id == USER_ID:  # 仅处理模型回答
            processed_content = process_chat_content(row[4], nickname_regex)

            output_data.append({
                "instruction": "",
                "input": "",
                "output": processed_content
            })

    # 输出JSON文件
    with open(r"proceed-group-msg_user-empty.json", 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
