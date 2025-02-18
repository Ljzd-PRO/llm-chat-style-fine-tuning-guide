import argparse
import http.client
import json
from datetime import timedelta

import time

USER_NAME = "JY"


def format_time(seconds):
    """格式化时间显示"""
    return str(timedelta(seconds=int(seconds)))


def preview_results(results, preview_count=3, max_length=50):
    """生成结果预览"""
    preview = []
    for i, item in enumerate(results[:preview_count]):
        preview_item = {}
        for key in ['instruction', 'input', 'output']:
            if key in item:
                content = str(item[key])
                preview_item[key] = content[:max_length] + "..." if len(content) > max_length else content
        preview.append(f"条目 {i + 1}: {preview_item}")
    return "\n".join(preview)


def read_json(file_path):
    """读取JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path, data):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def send_to_ollama(model, data_chunk, max_retries=100):
    """发送请求到Ollama并进行自动重试"""
    for attempt in range(max_retries + 1):
        conn = None
        try:
            conn = http.client.HTTPConnection("127.0.0.1:11434")
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "stream": False,
                "options": {
                    "temperature": 1.5
                },
                "messages": [
                    {
                        "role": "system",
                        "content": """\
请帮我进行数据集的生成，你会收到 JSON 列表格式的聊天记录，是一个群成员在回复别人的消息。

你需要根据 该成员的回复语句，推测聊天话题和上下文语境，猜测 被该成员回复 的消息内容。
需符合以下要求：
- 日常聊天，不要过多使用敬语
- 被回复和回复语句紧密关联、符合逻辑、连贯，不要只是简单重复语句中的关键词，或仅仅只是换个句式
- 返回会话对组成的 JSON List 格式，数量要和输入的一致，被回复和回复语句一一对应

例如输入：
[
    "康帅博",
    "不如面条",
    "千层面好吃"
]

你需要猜测这些聊天记录分别是在回应什么话
A: ... B 回复道: 康帅博
A: ... B 回复道: 不如面条
A: ... B 回复道: 千层面好吃

反例输出：
[
    ["你认识康帅博吗", "康帅博"],
    ["面条好吃吗", "不如面条"],
    ["千层面是西餐中的经典", "千层面好吃"]
]

即：
A: 你认识康帅博吗 B 回复道: 康帅博
A: 面条好吃吗 B 回复道: 不如面条
A: 千层面是西餐中的经典 B 回复道: 千层面好吃
这只是简单重复关键词，或者仅仅换了句式，甚至不是被回复和回复的关系，前后毫无关系。

正确输出：
[
    ["你喜欢哪个品牌的泡面", "康帅博"],
    ["感觉水饺很好吃", "不如面条"],
    ["哪种面条好吃", "千层面好吃"]
]
\
"""
                    },
                    #                                         {
                    #                                             "role": "assistant",
                    #                                             "content": """\
                    # <think>
                    # 嗯，我现在需要帮用户生成一个数据集，根据给定的JSON列表中的聊天记录，为每个成员的消息生成对应的其他成员的前文。

                    # 接下来，我需要分析用户提供的例子，理解正确的处理方式。例如，当输入是["康帅博", "好饿啊该吃什么", "吆西，来吃kfc"]时，正确的输出是根据每个回复生成合理的前文，比如第一个回复“康帅博”对应的前文可能是询问品牌的问题，而不是直接提到康帅博。而第二个回复可能没有合适的前文，所以用null。第三个回复则是针对去吃的建议，前文可能是询问地点。

                    # 现在，我需要处理一个具体的输入例子，假设输入是三个消息。首先，针对每条消息，我需要推测可能的上下文。例如，第一条消息是“康帅博”，这可能是在回答关于泡面品牌的问题，所以前文可能是“你喜欢哪个品牌的泡面？”。而第二条“好饿啊该吃什么”可能是一个发起的话题，但如果没有更合适的上下文，可能使用null。第三条“吆西，来吃kfc”可能是回答去哪吃的问题，所以前文是“去哪里吃？”。

                    # 需要注意避免前文重复回复中的关键词，例如，不能直接问“你喜欢康帅博吗？”，而是更自然的问题。同时，确保每个前文和回复之间的逻辑连贯，符合日常对话的习惯。

                    # 在处理过程中，如果遇到某些回复确实无法推断出合适的上下文，就使用null。必须确保生成的列表数量与输入一致，不能多也不能少。最后，输出的格式应该是严格的JSON列表，
                    # </think>
                    # 好的，请发送你要处理的数据\
                    # """
                    #                                         },
                    {
                        "role": "user",
                        "content": json.dumps([row["output"] for row in data_chunk], ensure_ascii=False, indent=4)
                    }
                ]
            }
            conn.request("POST", "/api/chat", body=json.dumps(payload), headers=headers)
            response = conn.getresponse()

            if response.status != 200:
                raise Exception(f"API错误: {response.status} {response.reason}")

            response_data = json.loads(response.read().decode())
            content: str = response_data["message"]["content"]

            content = content.replace("```json", "").replace("```", "")
            if (think_index := content.find("</think>")) != -1:
                content = content[think_index + len("</think>"):]
            generated_content = json.loads(content)

            if not isinstance(generated_content, list) or len(generated_content) != len(data_chunk):
                raise ValueError("返回数据格式或长度不正确")

            generated_content = [
                {
                    "instruction": "请你答复下面这位网络群聊成员发送的消息",
                    "input": input_,
                    "output": output_row["output"],
                    "system": f"你不是机器人，而是一个名字叫“{USER_NAME}”的网络群聊成员，他说话比较直接，喜欢用粗话。接下来你会收到其他群聊成员发送的消息，你要以他的身份答复。说话不要太正式，要简短些。"
                } for output_row, (input_, _) in zip(data_chunk, filter(lambda x: bool(x[0]), generated_content))
            ]

            return generated_content

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(content)
            print(f"解析失败（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
            if attempt >= max_retries:
                raise Exception("达到最大重试次数，请检查生成内容格式")
        finally:
            if conn:
                conn.close()


def process_json_in_batches(model, json_data, process_indices, batch_size, start_batch, output_path, skip_existing):
    """分批处理数据并自动保存进度"""
    total_items = len(process_indices)
    total_batches = (total_items + batch_size - 1) // batch_size
    start_time = time.time()
    time_records = []

    for batch_num in range(start_batch, total_batches):
        batch_start_time = time.time()
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_items)
        batch_indices = process_indices[start_idx:end_idx]
        current_batch = [json_data[i] for i in batch_indices]

        # 进度显示
        elapsed = time.time() - start_time
        avg_time = sum(time_records) / len(time_records) if time_records else 0
        remaining = (total_batches - batch_num) * avg_time if avg_time > 0 else 0

        print(f"\n{'=' * 40}")
        print(f"处理进度: {batch_num + 1}/{total_batches} 批（共{total_items}条需处理）")
        print(f"已用时间: {format_time(elapsed)}")
        print(f"预计剩余: {format_time(remaining) if remaining > 0 else '计算中...'}")

        try:
            response = send_to_ollama(model, current_batch)

            print(f"\n当前批次结果预览：")
            print(preview_results(response))

            # 更新原数据
            for idx, resp_item in zip(batch_indices, response):
                json_data[idx] = resp_item

            save_json(output_path, json_data)

            batch_time = time.time() - batch_start_time
            time_records.append(batch_time)
            print(f"本批处理时间: {batch_time:.1f}秒")

        except Exception as e:
            save_json(output_path, json_data)
            print(f"\n错误：处理批次 {batch_num + 1} 时失败，已保存当前进度")
            # 构造续处理命令
            command = f"python script.py --input {output_path} --output {output_path} " \
                      f"--batch-size {batch_size} --start-batch {batch_num}"
            if skip_existing:
                command += " --skip-existing"
            print(f"请使用以下命令继续处理：\n{command}")
            raise

    total_time = time.time() - start_time
    print(f"\n{'=' * 40}")
    print(f"处理完成！总耗时: {format_time(total_time)}")
    print(f"平均每批处理时间: {sum(time_records) / len(time_records):.1f}秒")


def main():
    parser = argparse.ArgumentParser(description="JSON数据批量处理工具")
    parser.add_argument("--input", required=True, help="输入JSON文件路径")
    parser.add_argument("--output", required=True, help="输出JSON文件路径")
    parser.add_argument("--model", type=str, default="qwen2.5:14b", help="所用模型名称（默认qwen2.5:14b）")
    parser.add_argument("--batch-size", type=int, default=25, help="每批处理数量（默认25）")
    parser.add_argument("--start-batch", type=int, default=0, help="起始批次号（从0开始）")
    parser.add_argument("--skip-existing", action='store_true',
                        help="跳过已存在instruction的条目")

    args = parser.parse_args()

    try:
        data = read_json(args.input)
    except Exception as e:
        print(f"无法读取输入文件: {str(e)}")
        return

    # 筛选需要处理的索引
    if args.skip_existing:
        process_indices = [i for i, item in enumerate(data) if not item.get('instruction')]
    else:
        process_indices = list(range(len(data)))

    # 验证起始批次
    total_batches = (len(process_indices) + args.batch_size - 1) // args.batch_size
    if args.start_batch >= total_batches and total_batches > 0:
        print(f"错误：起始批次 {args.start_batch} 超出总批次数 {total_batches}")
        return

    try:
        process_json_in_batches(
            model=args.model,
            json_data=data,
            process_indices=process_indices,
            batch_size=args.batch_size,
            start_batch=args.start_batch,
            output_path=args.output,
            skip_existing=args.skip_existing
        )
        print("\n处理完成！")
    except Exception as e:
        print(f"\n处理中断: {str(e)}")


if __name__ == "__main__":
    main()
