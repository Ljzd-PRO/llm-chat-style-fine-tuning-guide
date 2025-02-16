import argparse
import http.client
import json
from datetime import timedelta

import time


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
                    "temperature": 0.7
                },
                "messages": [
                    {
                        "role": "system",
                        "content": """\
你是一个助手，要帮我进行数据集的生成，你会收到长度固定的 JSON 列表格式的聊天记录，是一个群成员发送的消息。

你需要根据每条聊天记录中该成员的回复内容，推测聊天话题和上下文语境，依次为每条聊天记录生成对应的其他成员的聊天前文。
需符合以下要求：
- 日常聊天，不要过多使用敬语
- 聊天前文和该成员回复内容的关联需要在语法和语境上合理正确，前后连贯，不要让聊天前文简单重复该成员回复内容里提到的关键词
- 返回 JSON Object 格式，其他成员的聊天前文和该成员的回复内容按键和值一一对应
- 返回的 JSON Object 键值对数量要和输入的一致，不要丢失聊天记录
- 不要输出额外的其他任何内容

例如输入：
[
    "康帅博",
    "不会是侧透吧",
    "便宜还有花香"
]

反例输出：
{
    "你认识康帅博吗": "康帅博",
    "你电脑机箱是什么类型的": "不会是侧透吧",
    "什么东西好用又便宜？": "便宜还有花香",
}

正确输出：
{
    "你喜欢哪个品牌的泡面": "康帅博",
    "我看了，他的机箱很独特": "不会是侧透吧",
    "为什么选择种水仙花": "便宜还有花香"
}\
"""
                    },
                    #                     {
                    #                         "role": "assistant",
                    #                         "content": """\
                    # <think>
                    # 嗯，用户让我生成对应每条聊天记录的前文，需要符合日常对话，不能简单重复关键词，还要保持语法和语境合理。首先，我得仔细分析每个回复内容，推测可能的上下文。比如第一个例子“康帅博”，正确输出是“你喜欢哪个品牌的泡面”，因为康帅博可能是一个山寨品牌，和泡面相关，而不是直接问认不认识。反例中的前文直接用了“康帅博”这个名字，这样重复了关键词，不符合要求。

                    # 接下来，第二个回复“不会是侧透吧”，正确前文是“我看了，他的机箱很独特”，这里提到机箱类型，侧透是一种机箱设计，所以前文提到机箱独特，引导出侧透的可能，而没有直接问类型。反例中的前文直接问类型，导致重复关键词，应该避免。

                    # 第三个例子“便宜还有花香”，正确前文是“为什么选择种水仙花”，这里把花香和水仙花联系起来，而回复提到便宜，可能是在讨论种植水仙的原因，既便宜又有花香。反例中的前文直接问便宜的东西，导致重复。

                    # 现在用户给的任务是处理类似的输入，生成合理的前文。需要注意不要使用敬语，保持自然。比如如果输入是“明天要下雨”，前文可以是“周末计划去爬山怎么办”，这样回复提到下雨可能影响计划，而不是直接说天气。

                    # 另外，返回的JSON必须键值对应，长度一致，不能遗漏任何条目。需要确保每个回复都有对应的前文，且结构正确。例如输入三个回复，输出三个键值对。同时，前文和回复之间要有逻辑关联，但不要显式重复关键词。可能需要考虑不同的场景，比如讨论食物、电子产品、生活小窍门等，根据回复内容推断可能的上下文。

                    # 比如，如果回复是“我选了蓝色”，前文可能是“你觉得新出的手机颜色哪个好看”，这样关联颜色选择而不重复“蓝色”。再比如回复“可能需要带伞”，前文可以是“天气预报说下午有阵雨”，这样自然引出带伞的建议。

                    # 需要避免的是前文和回复之间的关联过于直接，比如回复是“喜欢跑步”，前文如果是“你喜欢什么运动”就太直接了，应该换成“最近公园里早上好多人”之类，引导出跑步作为活动。

                    # 总结步骤：1. 分析每条回复的内容，找出可能的讨论主题。2. 根据主题构建一个相关但不重复关键词的问题或陈述作为前文。3. 确保前文和回复在逻辑和语法上连贯。4. 严格遵循JSON格式，保持键值对数量一致，不添加额外内容。
                    # </think>
                    # {
                    # "我最近在找性价比高的泡面，有推荐吗": "康帅博",
                    # "张明新装的电脑照片你们看了没": "不会是侧透吧",
                    # "阳台种花哪种成本比较低": "便宜还有花香"
                    # }\
                    # """
                    #                     },
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

            if not isinstance(generated_content, dict) or len(generated_content) != len(data_chunk):
                raise ValueError("返回数据格式或长度不正确")

            generated_content = [{"instruction": instruction, "input": "", "output": output_row["output"]} for
                                 output_row, instruction in zip(data_chunk, generated_content)]

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
