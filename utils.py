import os
import json
import tiktoken
import re
import difflib

OJ_STATUSES = [
    "WT0",
    "WT1",
    "CI",
    "RI",
    "AC",
    "PE",
    "WA",
    "TL",
    "ML",
    "OL",
    "RE",
    "CE",
    "CO",
    "TF",
    "JE",
    "UE",
    "RE_SEGV",
    "RE_FPE",
    "RE_BUS",
    "RE_ABRT",
    "RE_SYS",
    "CTL",
]

def similarity(s1, s2):
    normalized1 = s1.replace('\n', ' ').replace('\r', '')
    normalized2 = s2.replace('\n', ' ').replace('\r', '')
    matcher = difflib.SequenceMatcher(None, normalized1, normalized2)
    return matcher.ratio()

case_max_cnt = {}
case_cnt = {}
for line in open('case.config', 'r').readlines():
    ts = line.strip().split('\t')
    case_max_cnt[int(ts[0])] = int(ts[1])
    case_cnt[int(ts[0])] = int(ts[2])

def read_file_contents(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def all_whitespace(str):
    for i in str:
        if i not in ['\n', '\r', '\t', ' ']:
            return False
    return True

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

def strings_are_same_except_blank_lines(s1, s2):
    s1_no_blank_lines = ''.join(line for line in s1.splitlines() if line.strip())
    s2_no_blank_lines = ''.join(line for line in s2.splitlines() if line.strip())

    return s1_no_blank_lines == s2_no_blank_lines

def parse_warning(warning_json):
    try:
        warning_dicts = json.loads(warning_json)
    except Exception as e:
        return warning_json
    res = ""
    for item in warning_dicts:
        if 'ignoring return value of ‘FILE* freopen(const char*, const char*, FILE*)’ declared with attribute ‘warn_unused_result’' in item['message']:
            continue
        if bool(re.search('comparison of integer expressions of different signedness: ‘int’ and ‘[a-zA-Z_:<>]*size_type’', item['message'])):
            continue
        if 'suggest' in item['message']:
            continue
        if item['kind'] != 'error':
            continue
        location = item['locations'][0]
        res += "%s in line %d column %d, " % (item['kind'].capitalize(), location['caret']['line'], location['caret']['column']) + item['message'] + '\n'
    return res

def add_eoln(s):
    if len(s) == 0 or s[-1] != '\n':
        s += '\n'
    return s

def contains_chinese(s):
    if re.search(r'[\u4e00-\u9fff]+', s):
        return True
    else:
        return False

def extract_code(response):
    response = response[:response.rfind('```')]
    response = re.sub(r'```[a-zA-Z+]*', '', response).strip()
    response = response[:response.rfind('\n}')+2]
    response = response[response.find('#'):]
    return response

def extract_last_cpp_code(s: str) -> str:
    matches = re.findall(r'```c\+\+(.*?)```', s, re.DOTALL)
    return matches[-1].strip() if matches else ""

def format_extra(ret, case_cnt):
    extra = {}
    times = []
    statuses = []
    memory = []
    for item in ret['extra']:
        times.append(item['runTime'])
        statuses.append(item['statusCode'])
        memory.append(item['memory'])
    extra = {'testcase': {'total': case_cnt, 'passed': ret['passed']},
             'time': times, 'statuses': statuses, 'memory': memory}
    if 'debug_info' in ret:
        extra['debug_info'] = ret['debug_info']
    return extra