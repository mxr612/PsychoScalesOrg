import json
import os
from flask import Flask, render_template, request

app = Flask(__name__)

# 加载所有问卷数据
def load_all_scales():
    scale_folder = 'scales'
    scales = {}
    for filename in os.listdir(scale_folder):
        if filename.endswith('.json'):
            with open(os.path.join(scale_folder, filename), 'r', encoding='utf-8') as f:
                scale = json.load(f)
                # 使用文件名作为问卷的唯一标识
                scale_id = os.path.splitext(filename)[0]
                scales[scale_id] = scale
    return scales

@app.route('/')
def index():
    scales = load_all_scales()
    return render_template('index.html', scales=scales)

@app.route('/scales/<scale_id>')
def scale(scale_id):
    scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        return render_template('scale.html', scale_id=scale_id,scale=scale)
    return "问卷未找到", 404

@app.route('/result/<scale_id>', methods=['POST'])
def result(scale_id):
    # print(request.form)
    scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        responses = {}
        ranges = {}
        # print(scale['questions'])
        for question in scale['questions']:
            # print(question['subscale'])
            if question['subscale'] not in responses:
                responses[question['subscale']] = 0
                ranges[question['subscale']] = [0,0]
            if 'reverse' in question and question['reverse']:
                responses[question['subscale']] += question['range'][1] + question['range'][0] - int( request.form[question['id']])
            else:
                responses[question['subscale']] += int( request.form[question['id']])
            ranges[question['subscale']][0] += question['range'][0]
            ranges[question['subscale']][1] += question['range'][1]
        # 这里可以添加保存数据到数据库等逻辑
        # print(ranges)
        return render_template('result.html', responses=responses, ranges=ranges, scale_title=scale['title'])
    return "问卷未找到", 404


if __name__ == '__main__':
    app.run(debug=True)