"""
一个简单的demo，调用ChatGLM生成角色的设定，调用CharacterGLM实现角色扮演。

依赖：
pyjwt
requests
streamlit
zhipuai
python-dotenv

运行方式：
```bash
streamlit run role_play_streamlit.py
```
"""
import os
import itertools
import time
from typing import Iterator, Optional
import streamlit as st
import api
from api import get_chatglm_response_via_sdk, get_characterglm_response
from data_types import TextMsg, filter_image_msg
from dotenv import load_dotenv
import json
# 通过.env文件设置环境变量
# reference: https://github.com/theskumar/python-dotenv
load_dotenv()


st.set_page_config(page_title="CharacterGLM API", page_icon="🤖", layout="wide")
debug = os.getenv("DEBUG", "").lower() in ("1", "yes", "y", "true", "t", "on")


def update_api_key(key: Optional[str] = None):
    if debug:
        print(f'update_api_key. st.session_state["API_KEY"] = {st.session_state["API_KEY"]}, key = {key}')
    key = key or st.session_state["API_KEY"]
    if key:
        api.API_KEY = key


# 设置API KEY
api_key = st.sidebar.text_input("API_KEY", value=os.getenv("API_KEY", ""), key="API_KEY", type="password",
                                on_change=update_api_key)
update_api_key(api_key)


# 初始化
if "history" not in st.session_state:
    st.session_state["history"] = []
if "meta" not in st.session_state:
    st.session_state["meta"] = {
        "user_name": "",
        "assistant_name": "",
        "user_info": "",
        "assistant_info": ""
    }
if "novel" not in st.session_state:
    st.session_state["novel"] = ""


def init_session():
    st.session_state["history"] = []


# 4个输入框，设置meta的4个字段
meta_labels = {
    "user_name": "用户名",
    "assistant_name": "角色名",
    "user_info": "用户人设",
    "assistant_info": "角色人设"
}


with st.container():
    st.text_area(label="小说，用来提取角色的名字和人设)", key="novel", max_chars=2000)


def update_meta():
    st.session_state["meta"]["assistant_name"] = st.session_state["assistant_name"]
    st.session_state["meta"]["assistant_info"] = st.session_state["assistant_info"]
    st.session_state["meta"]["user_name"] = st.session_state["user_name"]
    st.session_state["meta"]["user_info"] = st.session_state["user_info"]
    st.session_state["meta"]["bot_name"] = st.session_state["assistant_name"]
    st.session_state["meta"]["bot_info"] = st.session_state["assistant_info"]
    print("meta updated: " + json.dumps(st.session_state["meta"]))


def reset_meta():
    st.session_state["meta"] = {
        "user_name": "",
        "assistant_name": "",
        "user_info": "",
        "assistant_info": "",
        "bot_name": "",
        "bot_info": ""
    }
    del st.session_state.assistant_name
    del st.session_state.assistant_info
    del st.session_state.user_name
    del st.session_state.user_info

    st.session_state.assistant_name = ""
    st.session_state.assistant_info = ""
    st.session_state.user_name = ""
    st.session_state.user_info = ""


# 2x2 layout
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.text_input(label="角色名", key="assistant_name",
                      on_change=update_meta, help="角色名，不可以为空")
        st.text_area(label="角色人设", key="assistant_info",
                     on_change=update_meta, help="角色人设，不可以为空")
        
    with col2:
        st.text_input(label="用户名", key="user_name",
                      on_change=update_meta, help="用户名，不可以为空")
        st.text_area(label="用户人设", key="user_info",
                     on_change=update_meta, help="用户人设，不可以为空")


def verify_meta() -> bool:
    # 检查`角色名`和`角色人设`是否空，若为空，则弹出提醒
    if st.session_state["meta"]["assistant_name"] == "" or st.session_state["meta"]["assistant_info"] == "":
        st.error("角色名和角色人设不能为空")
        return False
    if st.session_state["meta"]["user_name"] == "" or st.session_state["meta"]["user_info"] == "":
        st.error("用户名和用户人设不能为空")
        return False
    return True


def verify_novel() -> bool:
    # 检查`小说`是否空，若为空，则弹出提醒
    if st.session_state["novel"] == "":
        st.error("小说不能为空")
        return False
    return True


def generate_meta() -> bool:
    novel = st.session_state["novel"]
    prompt = """
    你是资深的导演和编剧，给你一段剧本，请分析和概括出两个角色的名字和人设，按指定的格式输出，不要输出多余的内容。剧本如下:\n
    """ + novel
    prompt += """
    \n
    输出的格式:
    角色名字:角色人设
    角色名字:角色人设
    """
    prompt_list = [TextMsg(role="user", content=prompt)]
    # print("prompt: " + json.dumps(prompt_list))
    try:
        messages = get_chatglm_response_via_sdk(prompt_list)

        result = ""
        # 展示角色名和人设
        for message in messages:
            result += message

        # print("role_info: " + result)
        kvs = result.split("\n")
        if len(kvs) == 0:
            st.error("提取角色名和人设失败")

        name_index = 0
        info_index = 0
        for kv in [kv for kv in kvs if kv != ""]:
            if kv.find("角色名字:") >= 0:
                name = kv.replace("角色名字:", "").strip()
                print(f'名字:{name}')
                if name_index % 2 == 0:
                    del st.session_state.assistant_name
                    st.session_state.assistant_name = name
                    st.session_state["meta"]["assistant_name"] = name
                    st.session_state["meta"]["bot_name"] = name
                else:
                    del st.session_state.user_name
                    st.session_state.user_name = name
                    st.session_state["meta"]["user_name"] = name
                name_index += 1
            if kv.find("角色人设:") >= 0:
                info = kv.replace("角色人设:", "").strip()
                print(f'人设:{info}')
                if info_index % 2 == 0:
                    del st.session_state.assistant_info
                    st.session_state.assistant_info = info
                    st.session_state["meta"]["assistant_info"] = info
                    st.session_state["meta"]["bot_info"] = info
                else:
                    del st.session_state.user_info
                    st.session_state.user_info = info
                    st.session_state["meta"]["user_info"] = info
                info_index += 1
    except api.ApiKeyNotSet as e:
        st.error("API_KEY不能为空")
        return False
    # print("meta: " + json.dumps(st.session_state.meta))
    return True


def generate_chat():
    init_session()

    index = 1
    query = "开始对话吧"
    st.session_state["history"].append(TextMsg(role="user", content=query))
    while index < 10:
        response_stream = get_characterglm_response(messages=st.session_state.history, meta=st.session_state.meta)
        response = ""
        for response in itertools.accumulate(response_stream):
            pass
        if not response:
            st.error("生成出错")
            st.session_state["history"].pop()
        else:
            if index % 2 == 0:
                st.session_state["history"].append(TextMsg(role="user", content=response))
            else:
                st.session_state["history"].append(TextMsg(role="assistant", content=response))
        index += 1
        # time.sleep(100)
        # print(f"第{i}次调用...\n")
    st.rerun()


def save_chats():
    with open("./saved_chat.md", mode="w") as f:
        for message in st.session_state.history:
            name = st.session_state.user_name if message["role"] == "user" else st.session_state.assistant_name
            f.write(name + ":" + message["content"] + "<br>\n")
    st.info("对话已经保存到文件saved_chat.md")


button_labels = {
    "gen_meta": "生成人设",
    "clear_meta": "清空人设",
    "gen_chat": "生成对话",
    "clear_history": "清空对话历史",
    "save_chat": "保存对话"
}


if debug:
    button_labels.update({
        "show_api_key": "查看API_KEY",
        "show_meta": "查看meta",
        "show_history": "查看历史"
    })


# 在同一行排列按钮
with st.container():
    n_button = len(button_labels)
    cols = st.columns(n_button)
    button_key_to_col = dict(zip(button_labels.keys(), cols))

    with button_key_to_col["gen_meta"]:
        gen_meta = st.button(button_labels["gen_meta"], key="gen_meta")
        if gen_meta:
            if verify_novel() and generate_meta():
                st.rerun()
    
    with button_key_to_col["clear_meta"]:
        clear_meta = st.button(button_labels["clear_meta"], key="clear_meta")
        if clear_meta:
            reset_meta()
            st.rerun()

    with button_key_to_col["gen_chat"]:
        gen_chat = st.button(button_labels["gen_chat"], key="gen_chat")
        if gen_chat:
            if verify_novel() and verify_meta():
                generate_chat()

    with button_key_to_col["save_chat"]:
        save_chat = st.button(button_labels["save_chat"], key="save_chat")
        if save_chat:
            if len(st.session_state.history) == 0:
                st.error("对话为空")
            else:
                save_chats()

    with button_key_to_col["clear_history"]:
        clear_history = st.button(button_labels["clear_history"], key="clear_history")
        if clear_history:
            init_session()
            st.rerun()

    if debug:
        with button_key_to_col["show_api_key"]:
            show_api_key = st.button(button_labels["show_api_key"], key="show_api_key")
            if show_api_key:
                print(f"API_KEY = {api.API_KEY}")
        
        with button_key_to_col["show_meta"]:
            show_meta = st.button(button_labels["show_meta"], key="show_meta")
            if show_meta:
                print(f"meta = {st.session_state['meta']}")
        
        with button_key_to_col["show_history"]:
            show_history = st.button(button_labels["show_history"], key="show_history")
            if show_history:
                print(f"history = {st.session_state['history']}")


# 展示对话历史
for msg in st.session_state["history"]:
    if msg["role"] == "user":
        with st.chat_message(name="user", avatar="user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message(name="assistant", avatar="assistant"):
            st.markdown(msg["content"])
    else:
        st.error("无效的角色")


with st.chat_message(name="user", avatar="user"):
    input_placeholder = st.empty()
with st.chat_message(name="assistant", avatar="assistant"):
    message_placeholder = st.empty()


def output_stream_response(response_stream: Iterator[str], placeholder):
    content = ""
    for content in itertools.accumulate(response_stream):
        placeholder.markdown(content)
    return content


def start_chat():
    query = st.chat_input("开始对话吧")
    if not query:
        return
    else:
        if not verify_meta():
            return
        if not api.API_KEY:
            st.error("未设置API_KEY")

        input_placeholder.markdown(query)
        st.session_state["history"].append(TextMsg(role="user", content=query))

        response_stream = get_characterglm_response(messages=st.session_state["history"],
                                                    meta=st.session_state["meta"])
        response = output_stream_response(response_stream, message_placeholder)
        if not response:
            message_placeholder.markdown("生成出错")
            st.session_state["history"].pop()
        else:
            st.session_state["history"].append(TextMsg(role="assistant", content=response))


if __name__ == '__main__':
    start_chat()