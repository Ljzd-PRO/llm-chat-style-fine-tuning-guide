import csv
from multiprocessing import Pool, freeze_support
import json
from datetime import datetime
from collections import defaultdict


INPUT_CSV_PATH = r"group_msg.csv"
INPUT_CSV_ENCODING = "gbk"
OUTPUT_JSON_PATH = r"auto-combine-group-msg_no-llm.json"

def remove_at_nickname(args):
    text_list, nickname_list = args
    for i in range(len(text_list)):
        for nickname in nickname_list:
            text_list[i] = text_list[i].replace(f"@{nickname}", "")
        while text_list[i].startswith("@"):
            text_parts = text_list[i].split(" ")
            text_list[i] = "".join(text_parts[1:])
        text_list[i] = text_list[i].replace("[表情]", "").replace("[语音通话]", "").replace("@天才工具 人战兔", "").strip()
    return list(filter(bool, text_list))

if __name__ == "__main__":
    freeze_support()

    try:
        # Step 1: 读取所有可能的用户昵称
        nicknames = set()
        with open(INPUT_CSV_PATH, 'r', encoding=INPUT_CSV_ENCODING) as f:
            reader = csv.reader(f)
            for row in reader:
                nicknames.add(row[2])  # 第三列为用户昵称
                if row[2].startswith("?"):
                    nicknames.add(row[2][1:])
                if row[2].endswith("?"):
                    nicknames.add(row[2][:-1])   
        nicknames.discard("")
        nicknames.discard(" ")

        # Step 2: 处理聊天内容并合并片段
        processed_rows = []
        with open(INPUT_CSV_PATH, 'r', encoding=INPUT_CSV_ENCODING) as f:
            reader = csv.reader(f)
            content_list = []
            row_list = []
            for row in reader:
                # 解析聊天内容
                content_str = row[4].replace("', '", "','")  # 处理格式问题
                try:
                    content_seg = [seg.strip("'") for seg in content_str[1:-1].split("','")]
                except:
                    content_seg = []
                row_list.append(row)
                content_list.append(content_seg)
            
            # 处理每个片段
            nickname_list = list(nicknames)
            with Pool() as pool:
                cleaned_segments_parts = list(
                    pool.map(remove_at_nickname, map(lambda x: (x, nickname_list), content_list))
                )
            
            for (row, cleaned_segments) in zip(row_list, cleaned_segments_parts):
                if not cleaned_segments:
                    continue
                merged_content = '，'.join(cleaned_segments)
                
                # 解析时间
                dt = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
                
                processed_rows.append({
                    'datetime': dt,
                    'user_id': row[3],
                    'content': merged_content
                })

        # 按时间排序
        processed_rows.sort(key=lambda x: x['datetime'])

        # Step 3: 合并符合条件的记录
        user_indices = defaultdict(list)
        for idx, msg in enumerate(processed_rows):
            user_indices[msg['user_id']].append(idx)

        all_merged = []
        for user_id, indices in user_indices.items():
            if not indices:
                continue
            
            groups = []
            current_group = [indices[0]]
            
            for i in range(1, len(indices)):
                prev_idx = indices[i-1]
                current_idx = indices[i]
                
                # 计算中间他人消息数量
                other_count = 0
                for between_idx in range(prev_idx + 1, current_idx):
                    if processed_rows[between_idx]['user_id'] != user_id:
                        other_count += 1
                
                # 计算时间差
                time_diff = (processed_rows[current_idx]['datetime'] - processed_rows[prev_idx]['datetime']).total_seconds()
                
                if other_count <= 2 and time_diff <= 60:
                    current_group.append(current_idx)
                else:
                    groups.append(current_group)
                    current_group = [current_idx]
            
            groups.append(current_group)
            
            # 生成合并后的消息
            for group in groups:
                content_list = [processed_rows[i]['content'] for i in group]
                merged_content = '，'.join(content_list)
                avg_time = sum(processed_rows[i]['datetime'].timestamp() for i in group) / len(group)
                merged_dt = datetime.fromtimestamp(avg_time)
                all_merged.append({
                    'user_id': user_id,
                    'datetime': merged_dt,
                    'content': merged_content
                })

        # Step 4: 按时间排序合并后的记录
        all_merged.sort(key=lambda x: x['datetime'])

        # Step 5: 计算时间差
        result = []
        prev_time = None
        for msg in all_merged:
            current_time = msg['datetime']
            delta_seconds = 0
            if prev_time is not None:
                delta_seconds = int((current_time - prev_time).total_seconds())
            result.append({
                'user_id': msg['user_id'],
                'content': msg['content'],
                'delta': f"{delta_seconds}秒"
            })
            prev_time = current_time

        # Step 6: 导出为JSON
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except KeyboardInterrupt:
        print("用户中断了程序")
