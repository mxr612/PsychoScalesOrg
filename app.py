from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import markdown
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, yaml
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
        if filename.endswith(('.yaml', '.yml')):
            try:
                with open(os.path.join(scale_folder, filename), 'r', encoding='utf-8') as f:
                    scale = yaml.safe_load(f)
                    scale['instructions']=markdown.markdown(scale['instructions'], extensions=['fenced_code','tables','mdx_math'])
                    scale['descriptions']=markdown.markdown(scale['descriptions'], extensions=['fenced_code','tables','mdx_math'])
                    scale_id = os.path.splitext(filename)[0] # 使用文件名作为标识
                    scales[scale_id] = scale
            except Exception as e:
                print(f"Error loading scale {filename}: {e}")
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
    form_data = await request.form()
    scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        # 这里可以添加保存数据到数据库等逻辑
        responses = {}
        ranges = {}
        for subscale, qids in scale['subscales'].items():
            responses[subscale] = 0
            ranges[subscale] = [len(scale['range'][0]*qids),len(scale['range'][1]*qids)]
            for qid in qids:
                if qid<0:
                    responses[subscale] += scale['range'][0] + scale['range'][1] - int(form_data[str(-qid)])
                else:
                    responses[subscale] += int(form_data[str(qid)])
        return templates.TemplateResponse("result.html", {
            "request": request,
            "responses": responses,
            "ranges": ranges,
            "scale": scale
        })
    raise HTTPException(status_code=404, detail="问卷未找到")


if __name__ == '__main__':
   uvicorn.run(app,host='0.0.0.0',port=8000)