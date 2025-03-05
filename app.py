from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import markdown
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    scales = load_all_scales()
    # 新增读取README.md的逻辑
    readme_content = ""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = markdown.markdown(f.read())
    except FileNotFoundError:
        pass  # 如果README不存在则静默失败
    return templates.TemplateResponse("index.html", {
        "request": request,
        "scales": scales,
        "readme_content": readme_content  # 新增模板变量
    })

@app.get("/scales/{scale_id}", response_class=HTMLResponse)
async def scale(request: Request, scale_id: str):
    scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        return templates.TemplateResponse("scale.html", {
            "request": request,
            "scale_id": scale_id,
            "scale": scale
        })
    raise HTTPException(status_code=404, detail="问卷未找到")

@app.post("/result/{scale_id}", response_class=HTMLResponse)
async def result(request: Request, scale_id: str):
    # 保留原有的计分逻辑...
    form_data = await request.form()
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
                responses[question['subscale']] += question['range'][1] + question['range'][0] - int( form_data[question['id']])
            else:
                responses[question['subscale']] += int( form_data[question['id']])
            ranges[question['subscale']][0] += question['range'][0]
            ranges[question['subscale']][1] += question['range'][1]
        # 这里可以添加保存数据到数据库等逻辑
        # print(ranges)
        return templates.TemplateResponse("result.html", {
            "request": request,
            "responses": responses,
            "ranges": ranges,
            "scale_title": scale['title']
        })
    raise HTTPException(status_code=404, detail="问卷未找到")


if __name__ == '__main__':
   uvicorn.run(app,host='0.0.0.0',port=8000)