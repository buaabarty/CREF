import socket
import glob
import sys
import os
import json
import judge
import time
import openai
import copy
from settings import *
import poe
import requests
from bardapi import Bard
from prompts import *
from utils import *
from transformers import pipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSeq2SeqLM
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
socket.setdefaulttimeout(480)

openai.api_key = api_key
engine = "gpt-3.5-turbo-0613"
temperature = 1.0
prompt_type = None
print('sys.argv is ', sys.argv)
if len(sys.argv) > 2:
    reply_count = int(sys.argv[2])
    print('reply count is', reply_count)
    if len(sys.argv) > 3:
        prompt_type = sys.argv[3]
        if len(sys.argv) > 4:
            engine = sys.argv[4]
else:
    reply_count = 5

if engine == 'starchat':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "starchat-alpha")
    model = AutoModelForCausalLM.from_pretrained(model_dir + "starchat-alpha", device_map="auto", load_in_8bit=True)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'codellama':
    use_triton = False
    model_name = model_dir + "CodeLlama-13B-Instruct-GPTQ"
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoGPTQForCausalLM.from_quantized(model_name,
        use_safetensors=True,
        trust_remote_code=True,
        device="cuda:0",
        use_triton=use_triton,
        quantize_config=None)
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer
    )
elif engine == 'vicuna':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "stable-vicuna-13B-HF")
    model = AutoModelForCausalLM.from_pretrained(model_dir + "stable-vicuna-13B-HF", device_map="auto", load_in_8bit=True)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'codegen6b':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "codegen-6B-multi")
    model = AutoModelForCausalLM.from_pretrained(model_dir + "codegen-6B-multi", load_in_8bit=True, device_map='auto')
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'codegen16b':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "codegen-16B-multi")
    model = AutoModelForCausalLM.from_pretrained(model_dir + "codegen-16B-multi", load_in_8bit=True, device_map='auto')
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'codet5p':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "codet5p-16b")
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir + "codet5p-16b", load_in_8bit=True, device_map='auto', low_cpu_mem_usage=True, trust_remote_code=True)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'incoder':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "incoder-6B")
    model = AutoModelForCausalLM.from_pretrained(model_dir + "incoder-6B", load_in_8bit=True, device_map='auto')
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
elif engine == 'replit':
    tokenizer = AutoTokenizer.from_pretrained(model_dir + "replit-code-v1-3b", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_dir + "replit-code-v1-3b", trust_remote_code=True, device_map='auto')
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

delay_time = 0.001
timeout = 20
poe_token_cnt = 0

def translate(content):
    if content.isspace():
        return ''
    if not contains_chinese(content):
        return content
    ret = ""
    while True:
        try:
            chat_completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Don't display task instructions and any additional contents, and follow the task instructions to translate the given Chinese content literally, and only return the translated content."
                }, {
                    "role": "user",
                    "content": 'Translate the following Chinese content into English literally, making sure to keep the formatting (such as `` , $$, #, etc.) unchanged. When the phrase "蒜头君" appears in its entirety, translate it as "Mr. Garlic." Do not translate other words in this way. Remove all unnecessary interjections such as "哦," "噢," "嗯嗯," etc. Do not translate this sentence; only translate the content below and organize the format according to the Markdown standard.\n\nContent: ' + content
                }],
                temperature=temperature,
                n=1,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                user="user",
                timeout=20
            )
            ret = chat_completion['choices'][0]['message']['content']
            print(ret)
            break
        except Exception as e:
            print(e)
            print('sleep 30s ...')
            time.sleep(30)
    if '\nContent: ' in ret or ret.startswith('Content: '):
        ret = ret.split('Content: ')[-1]
    print('result: ', ret + '\n')
    return ret

def sendToGPT(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    old_response, old_ret, old_prompt, old_origin_response = result
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    history = []
    if old_prompt != "" and old_prompt != prompt:
        old_response, old_ret, old_prompt, old_origin_response = [], [], "", []
    if isinstance(prompt, list):
        for pmt in prompt:
            history.append({'role': 'user', 'content': pmt})
    else:
        history.append({'role': 'user', 'content': prompt})
    tot_token = num_tokens_from_messages(history)
    if engine.startswith('gpt-4'):
        max_token = 7800
    else:
        max_token = 4000
    todo = reply_count - len(old_response)
    while True:
        try:
            start_time = time.time()
            chat_completion = openai.ChatCompletion.create(
                model=engine,
                messages=history,
                temperature=temperature,
                n=todo,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                max_tokens=max_token-tot_token,
                stream=True,
            )
            res = ["" for i in range(todo)]
            for event in chat_completion:
                event_time = time.time() - start_time
                for choice in event['choices']:
                    event_text = choice['delta']
                    answer = event_text.get('content', '')
                    res[choice['index']] += answer
                time.sleep(delay_time)
            origin_response = res
            break
        except Exception as e:
            print(e)
            print('response illegal, sleep 120s and retry...', flush=True)
            time.sleep(120)
            continue
    response, ret = [], []
    for item in origin_response:
        now_code = extract_code(item)
        response.append(now_code)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    return [old_response + response, old_ret + ret, prompt, old_origin_response + origin_response]

def sendToCodeModel(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = "/*\n" + prompt + "\n*/\n#"
    if engine == "incoder":
        inputs = "<| file ext=.cpp |>\n" + inputs
    responses = []
    retry_cnt = 0
    cnt = len(tokenizer.tokenize(inputs))
    res = []
    for i in range(reply_count):
        if cnt > 1900:
            output = [{'generated_text': '#'}]
        else:
            output = pipe(inputs, max_length=min(2048, cnt+1024), min_length=cnt+64, temperature=temperature, do_sample=True)
        responses.append(output[0]['generated_text'])
        print(output[0]['generated_text'], flush=True)
    response, ret = [], []
    for item in responses:
        now_code = extract_code(item.split('\n*/\n')[-1])
        response.append(now_code)
        print(now_code, flush=True)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToGPTInteractive(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    old_response, old_ret, old_prompt, old_origin_response = result
    history = [{'role': 'user', 'content': buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "one_reply")}]
    if engine.startswith('gpt-4'):
        max_token = 7800
    else:
        max_token = 4090
    for i in range(reply_count):
        print('number: ', i, flush=True)
        inside_ret = copy.deepcopy(old_ret[i])
        inside_ret['extra'] = judge.format_extra(inside_ret, case_max_cnt[judge_result['problemId']])
        if inside_ret['statusCode'] == 4:
            print('Already been accepted, skip ......', flush=True)
            continue
        if isinstance(old_origin_response[i], list) and len(old_origin_response[i]) == 1 and isinstance(old_origin_response[i][0], str):
            inside_old_response = old_origin_response[i][0]
        elif isinstance(old_origin_response[i], str):
            inside_old_response = old_origin_response[i]
        else:
            inside_old_response = old_origin_response[i]['message']['content']
        history.append({'role': 'assistant', 'content': inside_old_response})
        inside_res = [inside_old_response]
        for j in range(2):
            print('step: ', j, flush=True)
            if j == 0:
                prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "solution")
            else:
                prompt = buildPrompt({'item': inside_ret, 'problemId': judge_result['problemId'], 'status': inside_ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "append_testcase")
            history.append({'role': 'user', 'content': prompt})
            print('history: ', history, flush=True)
            print('prompt: ', prompt, flush=True)
            tot_token = num_tokens_from_messages(history)
            res = ""
            if max_token - tot_token >= 10:
                chat_completion = openai.ChatCompletion.create(
                    model=engine,
                    messages=history,
                    temperature=temperature,
                    n=1,
                    top_p=1.0,
                    presence_penalty=0.0,
                    frequency_penalty=0.0,
                    max_tokens=max_token-tot_token,
                    stream=True,
                )
                for event in chat_completion:
                    for choice in event['choices']:
                        event_text = choice['delta']
                        answer = event_text.get('content', '')
                        print(answer, end="", flush=True)
                        res += answer
                    time.sleep(delay_time)
            inside_res.append(res)
            history.append({'role': 'assistant', 'content': res})
            now_code = extract_code(res)
            inside_ret = judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code, True)
            if inside_ret['statusCode'] == 4 or j == 1:
                break
            inside_ret['extra'] = judge.format_extra(inside_ret, case_max_cnt[judge_result['problemId']])
        old_origin_response[i] = inside_res
        old_response[i] = now_code
        old_ret[i] = inside_ret
    return [old_response, old_ret, history, old_origin_response]

def sendToClaude(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath=""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    responses = []
    retry_cnt = 0
    while True:
        try:
            response = ""
            global poe_token_cnt, poe_tokens
            poe_token_cnt += 1
            client = poe.Client(poe_tokens[poe_token_cnt % len(poe_tokens)])
            print('number: ', len(responses) + 1, flush=True)
            if isinstance(prompt, list):
                response = []
                first = True
                step = 0
                for pmt in prompt:
                    step += 1
                    print('step: ', step, flush=True)
                    if first:
                        for chunk in client.send_message("a2", pmt, with_chat_break=True):
                            pass
                        print(chunk['text'], flush=True)
                        response.append(chunk['text'])
                    else:
                        for chunk in client.send_message("a2", pmt, with_chat_break=False):
                            pass
                        print(chunk['text'], flush=True)
                        response.append(chunk['text'])
                    first = False
                responses.append(response)
            else:
                for chunk in client.send_message("a2", prompt, with_chat_break=True):
                    pass
                print(chunk['text'], flush=True)
                response = chunk['text']
                responses.append(response)
            if isinstance(response, list):
                print('sleep 15s to avoid banned by poe...', flush=True)
                time.sleep(15)
            else:
                print('sleep 5s to avoid banned by poe...', flush=True)
                time.sleep(5)
            if len(responses) >= reply_count:
                break
        except Exception as e:
            print(e)
            print(poe_tokens[poe_token_cnt % len(poe_tokens)])
            print('response illegal, sleep 30s and retry...')
            time.sleep(30)
            retry_cnt += 1
            if retry_cnt > 5:
                sys.exit(1)
            continue
    response, ret = [], []
    for item in responses:
        if isinstance(item, list):
            now_code = extract_code(item[-1])
        else:
            now_code = extract_code(item)
        response.append(now_code)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToClaudeInteractive(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa):
    responses = []
    retry_cnt = 0
    rets = []
    codes = []
    while True:
        try:
            response = ""
            global poe_token_cnt, poe_tokens
            poe_token_cnt += 1
            client = poe.Client(poe_tokens[poe_token_cnt % len(poe_tokens)])
            print('number: ', len(responses) + 1, flush=True)
            response = []
            ret_in = []
            now_code = None
            ret = None
            for step in range(3):
                if step == 0: # human reply
                    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "one_reply")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=True):
                        pass
                    res = chunk['text']
                elif step == 1: # document
                    prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "solution")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=False):
                        pass
                    res = chunk['text']
                elif step == 2: # testcase
                    prompt = buildPrompt({'item': ret, 'problemId': judge_result['problemId'], 'status': ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "append_testcase")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=False):
                        pass
                    res = chunk['text']
                print(res, flush=True)
                response.append(res)
                now_code = extract_code(res)
                ret = judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code, True)
                ret_in.append(ret)
                if ret['statusCode'] == 4 or step == 2:
                    break
                ret['extra'] = judge.format_extra(ret, case_max_cnt[judge_result['problemId']])
                print(ret, flush=True)
                time.sleep(3)
                print('sleep 3s to avoid banned by poe...', flush=True)
            rets.append(ret)
            responses.append(response)
            codes.append(now_code)
            if len(responses) >= reply_count:
                break
            time.sleep(3)
            print('sleep 3s to avoid banned by poe...', flush=True)
        except Exception as e:
            print(e)
            print(poe_tokens[poe_token_cnt % len(poe_tokens)])
            print('response illegal, sleep 30s and retry...')
            time.sleep(30)
            retry_cnt += 1
            if retry_cnt > 5:
                sys.exit(1)
            continue
    print([codes, rets, prompt, responses])
    return [codes, rets, prompt, responses]

def sendToBard(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath=""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    responses = []
    retry_cnt = 0
    while True:
        try:
            response = ""
            global poe_token_cnt, poe_tokens
            poe_token_cnt += 1
            session = requests.Session()
            session.headers = {
                "Host": "bard.google.com",
                "X-Same-Domain": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://bard.google.com",
                "Referer": "https://bard.google.com/",
            }
            session.cookies.set("__Secure-1PSID", bard_tokens[poe_token_cnt % len(bard_tokens)])
            chatbot = Bard(token=bard_tokens[poe_token_cnt % len(bard_tokens)], session=session, timeout=30)
            if isinstance(prompt, list):
                response = []
                for pmt in prompt:
                    response.append(chatbot.get_answer(pmt)['content'])
            else:
                response = chatbot.get_answer(prompt)['content']
            if 'Response Error: b\')]}\\\'\\n\\n' in response:
                raise Exception(response)
            responses.append(response)
            print(response, flush=True)
            if len(responses) >= reply_count:
                break
            if isinstance(prompt, list):
                print('sleep 12s to avoid banned by google bard...', flush=True)
                time.sleep(12)
            else:
                print('sleep 4s to avoid banned by google bard...', flush=True)
                time.sleep(4)
        except Exception as e:
            print(e)
            print(bard_tokens[poe_token_cnt % len(bard_tokens)])
            print('response illegal, sleep 5s and retry, remain %d tokens...' % (len(bard_tokens)))
            if '429' in str(e):
                del bard_tokens[poe_token_cnt % len(bard_tokens)]
                if len(bard_tokens) == 0:
                    sys.exit(1)
            time.sleep(5)
            continue
    response, ret = [], []
    for item in responses:
        if isinstance(item, list):
            now_code = extract_code(item[-1])
        else:
            now_code = extract_code(item)
        response.append(now_code)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToBardInteractive(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa):
    responses = []
    rets = []
    codes = []
    print('hey', flush=True)
    while True:
        try:
            print('number: ', len(responses) + 1, flush=True)
            response = ""
            global poe_token_cnt, poe_tokens
            poe_token_cnt += 1
            session = requests.Session()
            session.headers = {
                "Host": "bard.google.com",
                "X-Same-Domain": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://bard.google.com",
                "Referer": "https://bard.google.com/",
            }
            session.cookies.set("__Secure-1PSID", bard_tokens[poe_token_cnt % len(bard_tokens)]) 
            chatbot = Bard(token=bard_tokens[poe_token_cnt % len(bard_tokens)], session=session, timeout=30)
            response = []
            now_code = None
            ret = None
            for step in range(3):
                if step == 0: # human reply
                    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "one_reply")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                elif step == 1: # document
                    prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "solution")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                elif step == 2: # testcase
                    prompt = buildPrompt({'item': ret, 'problemId': judge_result['problemId'], 'status': ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "append_testcase")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                if 'Response Error: b\')]}\\\'\\n\\n' in res:
                    raise Exception(res)
                print(res, flush=True)
                response.append(res)
                now_code = extract_code(res)
                ret = judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code, True)
                if ret['statusCode'] == 4 or step == 2:
                    break
                ret['extra'] = judge.format_extra(ret, case_max_cnt[judge_result['problemId']])
                print(ret, flush=True)
                time.sleep(3)
                print('sleep 3s to avoid banned by Bard...', flush=True)
            rets.append(ret)
            responses.append(response)
            codes.append(now_code)
            if len(responses) >= reply_count:
                break
            time.sleep(3)
            print('sleep 3s to avoid banned by Bard...', flush=True)
        except Exception as e:
            print(e)
            print(bard_tokens[poe_token_cnt % len(bard_tokens)])
            print('response illegal, sleep 360s and retry...')
            time.sleep(360)
    print([codes, rets, prompt, responses])
    return [codes, rets, prompt, responses]

def sendToStarChat(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = "<|system|>\n<|end|>\n"
    if isinstance(prompt, list):
        for pmt in prompt:
            inputs += "<|user|>" + pmt + "\n"
    else:
        inputs += "<|user|>" + prompt + "<|end|>\n"
    inputs += "<|assistant|>"
    responses = []
    retry_cnt = 0
    cnt = len(tokenizer.tokenize(inputs))
    res = []
    for i in range(reply_count):
        if cnt > 1900:
            output = [{'generated_text': '#'}]
        else:
            output = pipe(inputs, max_length=min(2048, cnt+1024), min_length=cnt+64, temperature=temperature, stop_sequence='<|end|>', do_sample=True)
        responses.append(output[0]['generated_text'])
        print(output[0]['generated_text'], flush=True)
    response, ret = [], []
    for item in responses:
        now_code = extract_code(item.split('<|assistant|>')[-1])
        response.append(now_code)
        print(now_code, flush=True)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToVicuna(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = "### Human: " + prompt + "\n\n### Assistant:\n"
    responses = []
    retry_cnt = 0
    cnt = len(tokenizer.tokenize(inputs))
    res = []
    for i in range(reply_count):
        if cnt > 1900:
            output = [{'generated_text': '#'}]
        else:
            output = pipe(inputs, max_length=min(2048, cnt+1024), min_length=cnt+64, temperature=temperature, do_sample=True)
        responses.append(output[0]['generated_text'])
        print(output[0]['generated_text'], flush=True)
    response, ret = [], []
    for item in responses:
        now_code = extract_code(item.split('\n### Assistant:\n')[-1])
        response.append(now_code)
        print(now_code, flush=True)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToCodeLLAMA(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = ""
    if isinstance(prompt, list):
        for pmt in prompt:
            inputs += "[INST]\n" + pmt + "\n"
        inputs += "[/INST]\n"
    else:
        inputs += "[INST]\n" + prompt + "\n[/INST]\n"
    inputs += "```c++\n#include"
    responses = []
    retry_cnt = 0
    cnt = len(tokenizer.tokenize(inputs))
    res = []
    for i in range(reply_count):
        if cnt > 1900:
            output = [{'generated_text': '#'}]
        else:
            output = pipe(inputs, max_length=min(2048, cnt+1024), min_length=cnt+64, temperature=temperature, do_sample=True)
        responses.append(output[0]['generated_text'])
        print(output[0]['generated_text'], flush=True)
    response, ret = [], []
    for item in responses:
        now_code = extract_last_cpp_code(item.split('\n[/INST]')[-1])
        response.append(now_code)
        print('code:', now_code, flush=True)
        ret.append(judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToCodeLLAMAInteractive(result, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type, filepath = ""):
    old_response, old_ret, old_prompt, old_origin_response = result
    inputs_lst = ['' for i in range(reply_count)]
    for i in range(reply_count):
        print('number: ', i, flush=True)
        inside_ret = copy.deepcopy(old_ret[i])
        inside_ret['extra'] = judge.format_extra(inside_ret, case_max_cnt[judge_result['problemId']])
        if inside_ret['statusCode'] == 4:
            print('Already been accepted, skip ......', flush=True)
            continue
        inputs = old_origin_response[i]
        for j in range(2):
            print('step: ', j, flush=True)
            if j == 0:
                prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "solution")
            else:
                prompt = buildPrompt({'item': inside_ret, 'problemId': judge_result['problemId'], 'status': inside_ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, "append_testcase")
            inputs += "\n[INST] " + prompt + "\n[/INST]\n```c++\n#include"
            print('history================\n', inputs, flush=True)
            res = ""
            cnt = len(tokenizer.tokenize(inputs))
            if cnt > 3900:
                res = ''
            else:
                res = pipe(inputs, max_length=min(4096, cnt+1024), min_length=cnt+64, do_sample=True, temperature=temperature, top_p=1.0)[0]['generated_text']
            print(res, flush=True)
            now_code = extract_last_cpp_code(res.split('\n[/INST]')[-1])
            print(now_code, flush=True)
            inside_ret = judge.judgeByDetails(judge_result['problemId'], judge_result['timeLimit'], judge_result['memoryLimit'], case_max_cnt[judge_result['problemId']], judge_result.get('fileName', None), now_code, True)
            old_origin_response[i] = res
            if inside_ret['statusCode'] == 4 or j == 1:
                break
            inputs = res
            inside_ret['extra'] = judge.format_extra(inside_ret, case_max_cnt[judge_result['problemId']])
        old_response[i] = now_code
        inputs_lst[i] = inputs
        old_ret[i] = inside_ret
    return [old_response, old_ret, inputs_lst, old_origin_response]

def process(suffix = "", select_ids = None):
    total = 0
    ac = 0
    almost_correct = 0
    total_pass = 0
    ac_more = 0
    base_dir = 'final/'
    for root, dirs, _ in os.walk(base_dir):
        for qa_id in sorted(dirs):
            problem_id = json.loads(read_file_contents(base_dir + str(qa_id) + '/judge_result.txt'))['problemId']
            print(problem_id)
            if select_ids is not None and problem_id not in select_ids:
                continue
            print(qa_id)
            if select_ids is not None:
                description = read_file_contents(work_dir + '/descriptions/' + str(problem_id) + '_fix.txt')
            else:
                description = read_file_contents(base_dir + str(qa_id) + '/description_en.txt')
            solution = read_file_contents(base_dir + str(qa_id) + '/solution_en.txt')
            samples = []
            for i in range(1, 4):
                if os.path.exists(base_dir + str(qa_id) + '/sample' + str(i) + '.in'):
                    sample_in = read_file_contents(base_dir + str(qa_id) + '/sample' + str(i) + '.in')
                    sample_out = read_file_contents(base_dir + str(qa_id) + '/sample' + str(i) + '.out')
                    samples.append([sample_in, sample_out])
            if not os.path.exists(base_dir + str(qa_id) + '/question_en.txt'):
                question = json.loads(read_file_contents(base_dir + str(qa_id) + '/question.txt'))
                for idx in range(len(question)):
                    question[idx][0] = translate(question[idx][0])
                with open(base_dir + str(qa_id) + '/question_en.txt', 'w') as file:
                    file.write(json.dumps(question) + '\n')
            qa = json.loads(read_file_contents(base_dir + str(qa_id) + '/question_en.txt'))
            for filepath in sorted(glob.glob(os.path.join(base_dir + str(qa_id) + '/', '*_*.cpp'))):
                if 'AC' not in filepath:
                    judge_result = json.loads(read_file_contents(base_dir + str(qa_id) + '/judge_result.txt'))
                    if os.path.exists(filepath + '.result' + suffix):
                        result = json.loads(read_file_contents(filepath + '.result' + suffix))
                    else:
                        result = [[], [], "", []]
                    if len(result[0]) < reply_count or (int(suffix) > 2000 and not isinstance(result[0][0], list) and int(suffix) < 100000):
                        code_to_fix = read_file_contents(filepath)
                        std_in = read_file_contents(filepath.replace('.cpp', '.stdin'))
                        std_out = read_file_contents(filepath.replace('.cpp', '.stdout'))
                        try:
                            user_out = read_file_contents(filepath.replace('.cpp', '.out'))
                        except:
                            user_out = ''
                        status = filepath.split('/')[-1].split('_')[-1].split('.')[0]
                        status_id = int(filepath.split('/')[-1].split('_')[0])
                        if prompt_type == "interactive":
                            if 'gpt' in engine:
                                if not os.path.exists(filepath + '.result' + suffix):
                                    result = json.loads(read_file_contents(filepath + '.result' + str(int(suffix) % 1000)))
                                    result = sendToGPTInteractive(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            elif engine == 'bard':
                                result = sendToBardInteractive(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa)
                            elif engine == 'claude':
                                result = sendToClaudeInteractive(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa)
                            elif engine == 'codellama':
                                if not os.path.exists(filepath + '.result' + suffix):
                                    result = json.loads(read_file_contents(filepath + '.result' + str(int(suffix) - 1000)))
                                    result = sendToCodeLLAMAInteractive(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                        else:
                            if 'gpt' in engine:
                                result = sendToGPT(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            elif engine == 'bard':
                                result = sendToBard(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            elif engine == 'claude':
                                result = sendToClaude(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            elif engine == 'codellama':
                                result = sendToCodeLLAMA(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            elif engine == 'starchat':
                                result = sendToStarChat(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                            else:
                                result = sendToCodeModel(result, judge_result, status_id, description, code_to_fix, solution, status, user_out, std_in, std_out, samples, qa, prompt_type)
                        if result is None:
                            continue
                        with open(filepath + '.result' + suffix, 'w') as file:
                            file.write(json.dumps(result) + '\n')
                    old_passed = -1
                    nanti_status_id = int(filepath.split('/')[-1].split('_')[0])
                    for item in judge_result['notac']:
                        if item['nantiStatusId'] == nanti_status_id:
                            old_passed = item['extra']['testcase']['passed']
                            break
                    if old_passed == -1:
                        print('data error')
                        sys.exit(-1)
                    result_data = json.loads(read_file_contents(filepath + '.result' + suffix))
                    result = result_data[1]
                    add_ac, add_almost = True, False
                    for i in range(min(reply_count, len(result))):
                        if result[i]['statusCode'] == 4:
                            add_almost = True
                            total_pass += 1
                        else:
                            add_ac = False
                        now_pass = 0
                        print(result[i])
                        for it in result[i]['extra']:
                            print(it)
                            if it['statusCode'] == 4:
                                now_pass += 1
                        if now_pass > old_passed:
                            ac_more += 1
                    if add_ac:
                        ac += 1
                    if add_almost:
                        almost_correct += 1
                    total += 1
                    print('%d(%.1f\\%%) & %.1f(%.1f\\%%) & %d' % (almost_correct, almost_correct * 100 / total, total_pass / reply_count, total_pass * 100 / reply_count / total, total))
if __name__ == "__main__":
    output_self()
    process(sys.argv[1])
