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
    scales = {}
    tags = {}
    try:
        with open(os.path.join('tagmap.yml'), 'r', encoding='utf-8') as f:    
            tagmap = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading scale langmap: {e}")
    for root, dirs, files in os.walk(os.path.realpath('scales')):
        for filename in files:
            if filename.endswith(('.yaml', '.yml')):
                try:
                    with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                        scale = yaml.safe_load(f)
                        scale['instructions']=markdown.markdown(scale['instructions'], extensions=['fenced_code','tables','mdx_math'])
                        scale['descriptions']=markdown.markdown(scale['descriptions'], extensions=['fenced_code','tables','mdx_math'])
                        scale['abstract']=markdown.markdown(scale['abstract'], extensions=['fenced_code','tables','mdx_math'])
                        if 'tag' not in scale or scale['tag'] not in tagmap:
                            scale['tag']='other'
                        tags[scale['tag']]=tagmap[scale['tag']]
                        scale_id = os.path.splitext(filename)[0] # 使用文件名作为标识
                        scales[scale_id] = scale
                except Exception as e:
                    print(f"Error loading scale {filename}: {e}")
    return tags, scales

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tags, _ = load_all_scales()
    # 新增读取README.md的逻辑
    readme_content = ""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = markdown.markdown(f.read())
    except FileNotFoundError:
        pass  # 如果README不存在则静默失败
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tags": tags,
        "readme_content": readme_content  # 新增模板变量
    })

@app.get("/tag/{tag}", response_class=HTMLResponse)
async def list(request: Request, tag: str):
    tags, scales = load_all_scales()
    return templates.TemplateResponse("list.html", {
        "request": request,
        "tags": tags,
        "scales": scales,
        "tag": tag
    })  

@app.get("/scales/{scale_id}", response_class=HTMLResponse)
async def scale(request: Request, scale_id: str):
    tags, scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        return templates.TemplateResponse("scale.html", {
            "request": request,
            "scale_id": scale_id,
            "scale": scale,
            "tags":tags
        })
    raise HTTPException(status_code=404, detail="问卷未找到")

@app.post("/scales/{scale_id}", response_class=HTMLResponse)
async def result(request: Request, scale_id: str):
    form_data = await request.form()
    tags, scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        # 这里可以添加保存数据到数据库等逻辑
        responses = {}
        options = {}
        for subscale, qids in scale['subscales'].items():
            responses[subscale] = 0
            min_val = min(scale['options'].keys())
            max_val = max(scale['options'].keys())
            options[subscale] = [min_val*len(qids),max_val*len(qids)]
            for qid in qids:
                if qid<0:
                    responses[subscale] += min_val + max_val - int(form_data[str(-qid)])
                else:
                    responses[subscale] += int(form_data[str(qid)])
        return templates.TemplateResponse("result.html", {
            "request": request,
            "responses": responses,
            "options": options,
            "scale": scale,
            "tags":tags
        })
    raise HTTPException(status_code=404, detail="问卷未找到")


if __name__ == '__main__':
   uvicorn.run(app,host='0.0.0.0',port=8000)