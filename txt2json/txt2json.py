import json

def txt_to_json(input_file, output_file):
    # 获取用户输入的range范围
    range_input = input("请输入评分范围（格式：最小值,最大值，例如1,5）: ")
    range_values = list(map(int, range_input.split(',')))
    
    # 读取并分割问题和指令
    with open(input_file, 'r', encoding='utf-8') as f:
        all_lines = [line.strip() for line in f if line.strip()]
    
    # 分割问题定义和subscale指令
    if '--' in all_lines:
        split_index = all_lines.index('--')
        question_lines = all_lines[:split_index]
        subscale_lines = all_lines[split_index+1:]
    else:
        question_lines = all_lines
        subscale_lines = []

    # 解析subscale指令
    subscale_map = {}
    for line in subscale_lines:
        if '=' in line:
            name, ids = line.split('=', 1)
            for q_id in ids.split(','):
                subscale_map[q_id.strip()] = name.strip()

    questions = []
    for idx, line in enumerate(question_lines, 1):
        # 处理前导"-"标记
        reverse = 1 if line.startswith('-') else None
        text = line[1:] if reverse else line
        
        question = {
            "id": str(idx),
            "subscale": subscale_map.get(str(idx), ""),  # 新增subscale映射
            "text": text,
            "range": range_values.copy()
        }
        
        if reverse:
            question["reverse"] = 1
        
        questions.append(question)
    
    # 构建完整JSON结构
    result = {
        "title": "",
        "description": "",
        "instructions": "",
        "questions": questions
    }
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    txt_to_json("input.txt", "output.json")
