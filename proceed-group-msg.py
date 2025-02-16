import ast
import csv
import json
import re

USER_ID = "123456789"
"""目标用户ID"""
CSV_PATH = r"C:\Users\mcdha\PyCharmProjects\qq_nt_decrpty\group_msg.csv"
"""聊天记录CSV路径"""


def process_chat_content(content_str, nickname_regex):
    """处理聊天内容：合并片段、删除@提及、清理空格"""
    try:
        # 解析原始内容列表并合并
        content_list = ast.literal_eval(content_str)
        merged_content = ', '.join(str(item) for item in content_list)

        # 删除@用户昵称
        cleaned_content = nickname_regex.sub('', merged_content)

        # 清理多余空格并返回
        return re.sub(r'\s+', ' ', cleaned_content).strip()
    except (SyntaxError, ValueError, TypeError):
        return ''


def main():
    # 读取CSV数据并收集所有昵称
    with open(CSV_PATH, 'r', encoding='gbk') as csvfile:
        rows = list(csv.reader(csvfile))

    # 构建昵称正则表达式
    nicknames = {row[2] for row in rows if row[2].strip()}
    sorted_nicknames = sorted(nicknames, key=len, reverse=True)
    nickname_regex = re.compile(
        r'@(' + '|'.join(re.escape(n) for n in sorted_nicknames) + r')(?=\W|$)',
        flags=re.UNICODE
    )

    output_data = []

    # 遍历所有记录
    for idx, row in enumerate(rows):
        user_id = row[3]
        if user_id == USER_ID:  # 处理模型回答
            # 处理当前回答内容
            assistant_content = process_chat_content(row[4], nickname_regex)

            # 收集前1条有效指令
            instructions = []
            pointer = idx - 1  # 从当前记录前一条开始
            while pointer >= 0 and len(instructions) < 1:
                if rows[pointer][3] != USER_ID:  # 排除其他模型消息
                    # 处理指令内容
                    processed = process_chat_content(rows[pointer][4], nickname_regex)
                    if processed:  # 跳过空内容
                        instructions.append(processed)
                pointer -= 1

            # 生成训练数据条目
            for instruction in instructions:
                output_data.append({
                    "instruction": instruction,
                    "input": "",
                    "output": assistant_content
                })

    # 输出JSON文件
    with open(r"proceed-group-msg.json", 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
