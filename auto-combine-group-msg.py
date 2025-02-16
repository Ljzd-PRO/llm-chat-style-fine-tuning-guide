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
        preview_str = f"合并条目 {i + 1}: "
        if 'output' in item:
            content = str(item['output'])
            shortened = content[:max_length] + "..." if len(content) > max_length else content
            preview_str += shortened
        preview.append(preview_str)
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
    """发送合并请求到Ollama并进行自动重试"""
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
你是一个助手，你会收到一个群成员的聊天记录，你要帮我进行数据集的生成

要求如下：
- 你收到的聊天记录每句话是分隔开的，其中可能有其他成员发送的内容，你需要按顺序合并其中有关联的几句话，并添加合适的标点符号
- 如果该成员聊天记录中间可能存在其他人插话，则需要在可能插话的地方拆分开
- 生成为 JSON 列表格式，不要添加任何其他内容
- 不要丢失语句

样例：

输入：
[
  "康帅博",
  "sb amd显卡驱动",
  "更新选项又没了，又特么重新装",
  "今年必须把显卡换了",
  "amd狗屎再也不用了",
  "？",
  "AIR不是早出了？",
  "不信就算了",
  "AIR去年就出了",
  "对",
  "AIR是和Pro一起发布的"
]
输出：
[
  "康帅博",
  "sb amd显卡驱动，更新选项又没了，又特么重新装，今年必须把显卡换了，amd狗屎再也不用了",
  "？AIR不是早出了？",
  "不信就算了，AIR去年就出了",
  "对，AIR是和Pro一起发布的"
]

解析：
其中输出内容的
- 第1句是讨论泡面品牌话题，合并了相关语句
- 第2句是AMD显卡驱动问题，合并了相关语句
- 第3句是AIR产品相关话题，合并了相关语句
- 第4句也是AIR产品相关话题，但根据“不信就算了”，前面很可能有人插话，因此与第3句分开
- 第5句也是AIR产品相关话题，但根据“对”，前面很可能有人插话，因此与第4句分开
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

            content = content.replace("```", "")
            if (think_index := content.find("</think>")) != -1:
                content = content[think_index + len("</think>"):]

            merged_content = json.loads(content)

            # 验证合并结果格式
            if not isinstance(merged_content, list):
                raise ValueError("返回结果不是有效的列表格式")

            merged_content = [{"instruction": "", "input": "", "output": merged_output} for merged_output in
                              merged_content]
            return merged_content

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"解析失败（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
            if attempt >= max_retries:
                raise Exception("达到最大重试次数，请检查合并结果格式")
        finally:
            if conn:
                conn.close()


def process_merge(model, json_data, merged_json_data, process_indices, batch_size, start_batch, output_path):
    """分批处理合并任务"""
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
        print(f"处理进度: {batch_num + 1}/{total_batches} 批（原始数据共{len(json_data)}条）")
        print(f"已用时间: {format_time(elapsed)}")
        print(f"预计剩余: {format_time(remaining) if remaining > 0 else '计算中...'}")

        try:
            merged_batch = send_to_ollama(model, current_batch)

            print(f"\n合并结果预览（原始{len(current_batch)}条 → 合并为{len(merged_batch)}条）：")
            print(preview_results(merged_batch))

            # 将合并结果添加到新列表
            merged_json_data.extend(merged_batch)

            # 立即保存进度
            save_json(output_path, merged_json_data)

            batch_time = time.time() - batch_start_time
            time_records.append(batch_time)
            print(f"本批处理时间: {batch_time:.1f}秒")

        except Exception as e:
            save_json(output_path, merged_json_data)
            print(f"\n错误：处理批次 {batch_num + 1} 时失败，已保存当前进度")
            command = f"python script.py --input {output_path} --output {output_path} " \
                      f"--batch-size {batch_size} --start-batch {batch_num}"
            print(f"续处理命令：\n{command}")
            raise

    # 最终统计
    total_time = time.time() - start_time
    print(f"\n{'=' * 40}")
    print(f"合并完成！总耗时: {format_time(total_time)}")
    print(f"原始条目数: {len(json_data)} → 合并后条目数: {len(merged_json_data)}")
    print(f"平均每批处理时间: {sum(time_records) / len(time_records):.1f}秒")
    return merged_json_data


def main():
    parser = argparse.ArgumentParser(description="数据合并工具")
    parser.add_argument("--input", required=True, help="输入JSON文件路径")
    parser.add_argument("--output", required=True, help="输出JSON文件路径")
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理数量（默认10）")
    parser.add_argument("--start-batch", type=int, default=0, help="起始批次号（从0开始）")
    parser.add_argument("--model", type=str, default="qwen2.5:14b", help="所用模型名称（默认qwen2.5:14b）")

    args = parser.parse_args()

    try:
        original_data = read_json(args.input)
    except Exception as e:
        print(f"无法读取输入文件: {str(e)}")
        return

    try:
        processed_data = read_json(args.output)
    except Exception as e:
        print(f"无法读取输出文件，将设置已合并数据为空: {str(e)}")
        processed_data = []

    # 创建待处理索引列表（全量处理模式）
    process_indices = list(range(len(original_data)))

    # 验证起始批次
    total_batches = (len(process_indices) + args.batch_size - 1) // args.batch_size
    if args.start_batch >= total_batches and total_batches > 0:
        print(f"错误：起始批次 {args.start_batch} 超出总批次数 {total_batches}")
        return

    try:
        process_merge(
            model=args.model,
            json_data=original_data,
            merged_json_data=processed_data,
            process_indices=process_indices,
            batch_size=args.batch_size,
            start_batch=args.start_batch,
            output_path=args.output
        )
        print("\n合并完成！")
    except Exception as e:
        print(f"\n处理中断: {str(e)}")


if __name__ == "__main__":
    main()
