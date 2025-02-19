import argparse
import http.client
import json
from datetime import timedelta

import time

USER_NAME = "敬业"


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
                    "temperature": 0.8
                },
                "messages": [
                    {
                        "role": "system",
                        "content": """\
请帮我进行数据集的生成，你会收到一些具有特殊风格的聊天语句。

你需要以 JSON 格式转换这些语句到正常风格，并使其表述更完整，更容易理解，
**不要解释语句**，而是把语句**换一种更通俗易懂的方式重新表达**，
如果无法理解，就重复原话

有一些可能出现的网络用语需要转换成通俗易懂的：
- byd：表达感慨情绪
- 若只：是“弱智”的意思
- 啥比、沙比：是“傻逼”的意思
- fw：是“废物”的意思
- 吆西：表达感慨情绪
- 皮燕子：屁眼子
此外如果遇到了不认识的词，可根据其拼音进行猜测

例如输入：
[
    "byd真爽啊",
    "不如面条",
    "千层面好吃"
]

你应该输出：
[
    ["啊，这真的太爽了太舒服了", "byd真爽啊"],
    ["它没有比面条更好吃", "不如面条"],
    ["千层面非常好吃", "千层面好吃"]
]
\
"""
                    },
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

            if not isinstance(generated_content, list) or len(generated_content) != len(data_chunk) or not all(
                    map(lambda x: isinstance(x, str), generated_content)
                ):
                raise ValueError("返回数据格式或长度不正确")

            generated_content = [
                {
                    "input": input_,
                    "output": output_row["output"],
                    "system": f"你是一个助手，需要对下面的聊天语句进行风格转换，目标风格是说话直接的、喜欢用粗话、心直口快的、刻薄、高高在上、嘲讽的"
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
                        help="跳过已存在input的条目")

    args = parser.parse_args()

    try:
        data = read_json(args.input)
    except Exception as e:
        print(f"无法读取输入文件: {str(e)}")
        return

    # 筛选需要处理的索引
    if args.skip_existing:
        process_indices = [i for i, item in enumerate(data) if not item.get('input')]
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
