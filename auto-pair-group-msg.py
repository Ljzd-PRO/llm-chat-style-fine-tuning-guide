import argparse
import http.client
import json
from urllib.parse import urlparse

import time

USER_NAME = "JY"


def main():
    parser = argparse.ArgumentParser(description='处理聊天记录并生成对话对')
    parser.add_argument('--input', required=True, help='输入的JSON文件路径')
    parser.add_argument('--output', required=True, help='输出的JSON文件路径')
    parser.add_argument('--user', required=True, help='目标用户ID')
    parser.add_argument('--model', default='llama2', help='Ollama模型名称')
    parser.add_argument('--api', default='http://localhost:11434', help='Ollama API地址')
    args = parser.parse_args()

    # 解析API地址
    parsed_url = urlparse(args.api)
    api_host = parsed_url.hostname
    api_port = parsed_url.port or 11434

    # 读取原始数据
    with open(args.input, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    # 预处理有效目标消息
    valid_targets = []
    for i, msg in enumerate(messages):
        if msg['user_id'] == args.user:
            # 检查前一条消息是否重复
            if i > 0 and messages[i - 1]['content'] == msg['content']:
                continue

            # 收集上下文
            start = max(0, i - 15)
            preceding = messages[start:i]

            # 截断到最近的目标消息
            last_target = None
            for j in reversed(range(len(preceding))):
                if preceding[j]['user_id'] == args.user:
                    last_target = j
                    break
            if last_target is not None:
                preceding = preceding[last_target + 1:]

            valid_targets.append({
                'context': preceding,
                'content': msg['content']
            })

    # 初始化处理状态
    dialogue_pairs = []
    not_found_list = []
    discard_count = 0
    failed_count = 0
    total = len(valid_targets)
    processed = 0
    start_time = time.time()

    # 处理每个目标消息
    for target in valid_targets:
        processed += 1
        context = target['context']
        content = target['content']

        input_list = [f"[{idx}] - {msg['content']}" for idx, msg in enumerate(context)]
        input_list.append(f"[目标] - {content}")

        # 初始化重试相关变量
        match = -1
        max_retries = 3
        not_found_times = 0
        max_retries_not_found = 1

        for attempt in range(max_retries):
            try:
                # 创建新的HTTP连接
                conn = http.client.HTTPConnection(api_host, port=api_port)
                headers = {"Content-Type": "application/json"}
                payload = {
                    "model": args.model,
                    "stream": False,
                    "options": {
                        "temperature": 0.5
                    },
                    "messages": [
                        {
                            "role": "system",
                            "content": """\
你是一个助手，要帮我进行数据分析，你会收到一个 群聊聊天记录列表 和位于最后的 额外指定的一条聊天记录。

你需要推测聊天话题和上下文语境，分析 指定的聊天记录 回复的是上面哪一条，然后返回序号
需符合以下要求：
- 被回复的内容和指定的聊天记录关联紧密，在语境上合理正确，前后连贯，话题相同
- 直接输出纯数字序号，不要输出额外的其他任何内容，不要解释原因
- 如果实在找不到（**一般都找得到**，请仔细分析），才返回 -1

案例一：

输入：

[1] - 你喜欢哪个品牌的泡面
[2] - 你电脑机箱是什么类型的
[3] - 康师傅
[目标] - 侧透机箱

输出：2

案例二：

输入：

[1] - 今晚吃什么
[2] - 牛肉面
[3] - 今天天气怎么样
[目标] - 好累啊下班了

输出：-1\
"""
                        },
                        {
                            "role": "user",
                            "content": "\n".join(input_list)
                        }
                    ]
                }
                # 发送请求
                conn.request("POST", "/api/chat", body=json.dumps(payload), headers=headers)
                response = conn.getresponse()

                # 检查HTTP状态码
                if response.status != 200:
                    raise Exception(f"API错误: {response.status} {response.reason}")

                # 解析响应数据
                response_data = json.loads(response.read().decode())
                response_content = response_data["message"]["content"]

                # 处理潜在的</think>标签
                if (think_index := response_content.find("</think>")) != -1:
                    response_content = response_content[think_index + len("</think>"):]

                # 提取序号
                match = int(response_content.strip())
                if match == -1:
                    if not_found_times >= max_retries_not_found:
                        break
                    else:
                        not_found_times += 1
                else:
                    break  # 成功则退出重试循环

            except Exception as e:
                print(f"处理失败（第{attempt + 1}次重试）: {str(e)}")
                if not attempt < max_retries - 1:
                    print("已达到最大重试次数，放弃处理该消息")
                    match = -1
                    failed_count += 1
            finally:
                if 'conn' in locals():
                    conn.close()  # 确保连接关闭

        # 处理匹配结果
        if 0 <= match < len(context):
            if context[match]['content'] == content:
                print(f"出现复读: {content[:50]}...")
                discard_count += 1
            else:
                dialogue_pairs.append([context[match]['content'], content])
        else:
            print(f"未匹配到上下文: {content[:50]}...")
            not_found_list.append(content)
            discard_count += 1

        # 实时保存结果
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([
                {
                    "instruction": "请你答复下面这位网络群聊成员发送的消息",
                    "input": input_text,
                    "output": output_text,
                    "system": f"你不是机器人，而是一个名字叫“{USER_NAME}”的网络群聊成员，他说话比较直接，喜欢用粗话。接下来你会收到其他群聊成员发送的消息，你要以他的身份答复。说话不要太正式，要简短些。"
                } for (input_text, output_text) in dialogue_pairs
            ], f, indent=2, ensure_ascii=False)
        with open("not_found_list.json", 'w', encoding='utf-8') as f:
            json.dump([
                {
                    "instruction": "请你答复下面这位网络群聊成员发送的消息",
                    "input": "",
                    "output": output_text,
                    "system": f"你不是机器人，而是一个名字叫“{USER_NAME}”的网络群聊成员，他说话比较直接，喜欢用粗话。接下来你会收到其他群聊成员发送的消息，你要以他的身份答复。说话不要太正式，要简短些。"
                } for output_text in not_found_list
            ], f, indent=2, ensure_ascii=False)

        # 计算进度
        elapsed = time.time() - start_time
        avg_time = elapsed / processed
        remain = total - processed
        print(f"进度: {processed}/{total} | 剩余时间: {avg_time * remain:.1f}s")

    print(f"处理完成，有效对话对: {len(dialogue_pairs)}，丢弃消息: {discard_count}，失败消息：{failed_count}")


if __name__ == '__main__':
    main()
