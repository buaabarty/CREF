import socket
import glob
import sys
import os
import json
import time
import openai
import copy
from settings import *
import poe
import requests
from bardapi import Bard
from prompts import *
from utils import *
import tutorcode_api
import distance
from transformers import pipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSeq2SeqLM
from auto_gptq import AutoGPTQForCausalLM
socket.setdefaulttimeout(480)

openai.api_key = api_key
engine = "gpt-3.5-turbo-0613"
temperature = 1.0
prompt_type = None
print('sys.argv is ', sys.argv)
if len(sys.argv) > 1:
    reply_count = int(sys.argv[1])
    print('reply count is', reply_count)
    if len(sys.argv) > 2:
        prompt_type = sys.argv[2]
        if len(sys.argv) > 3:
            engine = sys.argv[3]
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

def sendToGPT(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
    history = []
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
    todo = reply_count
    print(history)
    print(max_token-tot_token)
    while True:
        try:
            chat_completion = openai.ChatCompletion.create(
                model=engine,
                messages=history,
                temperature=temperature,
                n=todo,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                max_tokens=max_token-tot_token,
            )
            origin_response = []
            for item in chat_completion['choices']:
                origin_response.append(item['message']['content'])
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
        ret.append(tutorcode_api.judge(id, now_code))
    return [response, ret, prompt, origin_response]

def sendToCodeModel(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = "/*\n" + prompt + "\n*/\n#"
    if engine == "incoder":
        inputs = "<| file ext=.cpp |>\n" + inputs
    responses = []
    cnt = len(tokenizer.tokenize(inputs))
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToGPTInteractive(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa):
    origin_response = ['' for i in range(reply_count)]
    response = ['' for i in range(reply_count)]
    ret = ['' for i in range(reply_count)]
    if engine.startswith('gpt-4'):
        max_token = 7800
    else:
        max_token = 4090
    for i in range(reply_count):
        print('number: ', i, flush=True)
        history = []
        inside_res = []
        for j in range(3):
            print('step: ', j, flush=True)
            if j == 0:
                prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, "reply")
            elif j == 1:
                prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "solution")
            else:
                prompt = buildPrompt({'item': inside_ret, 'problemId': judge_result['problemId'], 'status': inside_ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "append_testcase")
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
            inside_ret = tutorcode_api.judge(id, now_code)
            if inside_ret['statusCode'] == 4 or j == 2:
                break
            inside_ret['extra'] = format_extra(inside_ret, judge_result['case_cnt'])
        origin_response[i] = inside_res
        response[i] = now_code
        ret[i] = inside_ret
    return [response, ret, history, origin_response]

def sendToClaude(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToClaudeInteractive(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa):
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
                    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, "reply")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=True):
                        pass
                    res = chunk['text']
                elif step == 1: # document
                    prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "solution")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=False):
                        pass
                    res = chunk['text']
                elif step == 2: # testcase
                    prompt = buildPrompt({'item': ret, 'problemId': judge_result['problemId'], 'status': ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "append_testcase")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    for chunk in client.send_message("a2", prompt, with_chat_break=False):
                        pass
                    res = chunk['text']
                print(res, flush=True)
                response.append(res)
                now_code = extract_code(res)
                ret = tutorcode_api.judge(id, now_code)
                ret_in.append(ret)
                if ret['statusCode'] == 4 or step == 2:
                    break
                ret['extra'] = format_extra(ret, judge_result['case_cnt'])
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

def sendToBard(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToBardInteractive(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa):
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
                    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, "reply")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                elif step == 1: # document
                    prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "solution")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                elif step == 2: # testcase
                    prompt = buildPrompt({'item': ret, 'problemId': judge_result['problemId'], 'status': ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "append_testcase")
                    print('step: ', step, flush=True)
                    print('prompt:', prompt, flush=True)
                    res = chatbot.get_answer(prompt)['content']
                if 'Response Error: b\')]}\\\'\\n\\n' in res:
                    raise Exception(res)
                print(res, flush=True)
                response.append(res)
                now_code = extract_code(res)
                ret = tutorcode_api.judge(id, now_code)
                if ret['statusCode'] == 4 or step == 2:
                    break
                ret['extra'] = format_extra(ret, judge_result['case_cnt'])
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

def sendToStarChat(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToVicuna(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
    print('prompt:', prompt, flush=True)
    inputs = "### Human: " + prompt + "\n\n### Assistant:\n"
    responses = []
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToCodeLLAMA(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type):
    prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
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
        ret.append(tutorcode_api.judge(id, now_code))
    print(ret)
    return [response, ret, prompt, responses]

def sendToCodeLLAMAInteractive(id, judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa):
    origin_response = ['' for i in range(reply_count)]
    response = ['' for i in range(reply_count)]
    ret = ['' for i in range(reply_count)]
    inputs_lst = ['' for i in range(reply_count)]
    for i in range(reply_count):
        print('number: ', i, flush=True)
        inputs = ""
        for j in range(3):
            print('step: ', j, flush=True)
            if j == 0:
              prompt = buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, qa, "reply")
            elif j == 1:
                prompt = buildPrompt(judge_result, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "solution")
            else:
                prompt = buildPrompt({'item': inside_ret, 'problemId': judge_result['problemId'], 'status': inside_ret['statusCode']}, nanti_status_id, None, code_to_fix, solution, status, user_out, qa, "append_testcase")
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
            inside_ret = tutorcode_api.judge(id, now_code)
            origin_response[i] = res
            if inside_ret['statusCode'] == 4 or j == 2:
                break
            inputs = res
            inside_ret['extra'] = format_extra(inside_ret, judge_result['case_cnt'])
        response[i] = now_code
        inputs_lst[i] = inputs
        ret[i] = inside_ret
    return [response, ret, inputs_lst, origin_response]

def process():
    total = 0
    almost_correct = 0
    total_pass = 0
    base_rps = 0
    real_rps = 0
    for id in range(4, 1240):
        item = tutorcode_api.fetch_data(id)
        qa = item['tutorGuidance']
        description = item['problemDescription']
        solution = item['solutionDescription']
        code_to_fix = item['incorrectCode']
        judge_result = item['judgeResult']
        status_id = item['statusId']
        user_out = item['userOut']
        ground_truth = item['groudTruthCode']
        status = None
        base_rps += distance.calc_dist(code_to_fix, ground_truth)
        for item in judge_result['notac']:
            if item['nantiStatusId'] == status_id:
                status = OJ_STATUSES[item['statusFlag']]
        if prompt_type == "interactive":
            if 'gpt' in engine:
                result = sendToGPTInteractive(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa)
            elif engine == 'bard':
                result = sendToBardInteractive(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa)
            elif engine == 'claude':
                result = sendToClaudeInteractive(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa)
            elif engine == 'codellama':
                result = sendToCodeLLAMAInteractive(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa)
        else:
            if 'gpt' in engine:
                result = sendToGPT(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            elif engine == 'bard':
                result = sendToBard(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            elif engine == 'claude':
                result = sendToClaude(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            elif engine == 'codellama':
                result = sendToCodeLLAMA(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            elif engine == 'starchat':
                result = sendToStarChat(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            elif engine == 'vicuna':
                result = sendToVicuna(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
            else:
                result = sendToCodeModel(id, judge_result, status_id, description, code_to_fix, solution, status, user_out, qa, prompt_type)
        add_almost = False
        print(result[0])
        for i in range(reply_count):
            if result[1][i]['statusCode'] == 4:
                add_almost = True
                total_pass += 1
            real_rps += distance.calc_dist(code_to_fix, result[0][i])
        if add_almost:
            almost_correct += 1
        total += 1
        print('TOP-5: %d(%.1f\\%%), AVG-5: %.1f(%.1f\\%%), RPSR: %.3f TOT: %d' % (almost_correct, almost_correct * 100 / total, total_pass / reply_count, total_pass * 100 / reply_count / total, real_rps / reply_count / base_rps, total))
if __name__ == "__main__":
    process()
