from utils import *
import tutorcode_api

type_name = {
    "AC": "run correctly",
    "WA": "produced a wrong output",
    "TL": "exceeded the runtime limit",
    "RE": "encountered a runtime error",
    "CE": "has compilication errors",
    "CTL": "exceeded the compile time limit",
    "ML": "exceeded the memory limit",
    'SEGV': 'encountered a segmentation fault',
    'ABRT': 'encountered an abnormal abort signal',
    'PE': 'produced an incorrect output format',
    'FPE': 'encountered a floating point exception',
    'OL': 'exceeded the output limit',
    'FE': 'has not output data to the correct file',
    'BE': 'produced binary data',
}

append_prompt = "The code you replied is still incorrect.\n\n"

def buildOneReplyPrompt(judge_result, nanti_status_id, description, code_to_fix, one_reply):
    if description is not None:
        prompt = "This is a programming problem description:\n" + description + "\n"
        if judge_result.get('fileName', None) is not None:
            prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
        prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
        prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
        prompt += "This is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    else:
        prompt = append_prompt
    prompt += 'You are a software engineer.\n\n'
    prompt += one_reply
    prompt += "\n\nCan you repair the incorrect code?"
    return prompt

def buildDefaultPrompt(judge_result, description, code_to_fix):
    if description is not None:
        prompt = "This is a programming problem description:\n" + description + "\n"
        if judge_result.get('fileName', None) is not None:
            prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
        prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
        prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
        prompt += "This is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    else:
        prompt = append_prompt
    prompt += "You are a software engineer. Can you repair the incorrect code?\n"
    return prompt

def buildSolutionPrompt(judge_result, description, code_to_fix, solution):
    if description is not None:
        prompt = "This is a programming problem description:\n" + description + "\n"
        if judge_result.get('fileName', None) is not None:
            prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
        prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
        prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
        prompt += "This is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    else:
        prompt = append_prompt
    prompt += "This is a solution to the problem:\n\n" + solution + "\n\n"
    prompt += "You are a software engineer. Can you repair the incorrect code?\n"
    return prompt

def buildOneReplyAndTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, status, one_reply):
    prompt = "This is a programming problem description:\n" + description + "\n"
    if judge_result.get('fileName', None) is not None:
        prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
    prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
    prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
    prompt += "This is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    input_test, output_test = [], []
    problem_id = judge_result['problemId']
    judge_item = None
    for item in judge_result['notac']:
        if item['nantiStatusId'] == nanti_status_id:
            judge_item = item
            break
    for i in range(case_max_cnt[judge_result['problemId']]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt += "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt += 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += 'You are a software engineer.\n\n'
    prompt += one_reply
    prompt += "\n\nCan you repair the incorrect code?"
    return prompt

def buildTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, status, user_out):
    if description is not None:
        prompt = "This is a programming problem description:\n" + description + "\n"
        if judge_result.get('fileName', None) is not None:
            prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
        prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
        prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
        prompt += "\n\nThis is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    else:
        prompt = append_prompt
    input_test, output_test = [], []
    problem_id = judge_result['problemId']
    judge_item = None
    for item in judge_result['notac']:
        if item['nantiStatusId'] == nanti_status_id:
            judge_item = item
            break
    if user_out == '未找到对应输出文件。':
        status = 'FE'
    elif user_out == '无法显示，输出包含二进制数据':
        status = 'BE'
    for i in range(case_max_cnt[judge_result['problemId']]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt += "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt += 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += "You are a software engineer. Can you repair the incorrect code?"
    return prompt

def buildOneReplyAndSolutionAndTestcaseImprovedNewPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, one_reply):
    prompt = "# Problem Description\n" + description + "\n"
    if judge_result.get('fileName', None) is not None:
        prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
    prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
    prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
    input_test, output_test = [], []
    problem_id = judge_result['problemId']
    judge_item = None
    for item in judge_result['notac']:
        if item['nantiStatusId'] == nanti_status_id:
            judge_item = item
            break
    if user_out == '未找到对应输出文件。':
        status = 'FE'
    elif user_out == '无法显示，输出包含二进制数据':
        status = 'BE'
    for i in range(case_max_cnt[judge_result['problemId']]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    prompt += "\n\n# Incorrect Code\n```c++\n" + code_to_fix + "```\n\n"
    prompt += "# Instructor Reply\n\n"
    prompt += one_reply
    prompt += "\n\n# Solution Document\n\n" + solution + "\n\n"
    prompt += "# Failing Test Cases\n\n"
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt += "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt += 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += '\nYou are a software engineer. Can you repair the incorrect code?'
    return prompt

def buildOneReplyAndSolutionAndTestcaseArray2Prompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, one_reply):
    prompts = []
    prompt = "This is a programming problem description:\n" + description + "\n"
    if judge_result.get('fileName', None) is not None:
        prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
    prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
    prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
    input_test, output_test = [], []
    problem_id = judge_result['problemId']
    judge_item = None
    for item in judge_result['notac']:
        if item['nantiStatusId'] == nanti_status_id:
            judge_item = item
            break
    if user_out == '未找到对应输出文件。':
        status = 'FE'
    elif user_out == '无法显示，输出包含二进制数据':
        status = 'BE'
    for i in range(case_max_cnt[judge_result['problemId']]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    prompt += "\n\nThis is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    prompt += one_reply
    prompts.append(prompt)
    prompts.append("This is a solution to the problem:\n\n" + solution + "\n\n")
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt = "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt = 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += 'You are a software engineer. Can you repair the incorrect code?'
    prompts.append(prompt)
    return prompts

def buildOneReplyAndSolutionPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, one_reply):
    prompt = "This is a programming problem description:\n" + description + "\n"
    if judge_result.get('fileName', None) is not None:
        prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
    prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
    prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
    prompt += "This is an incorrect code to the problem:\n```markdown\n" + code_to_fix + "```\n\n"
    prompt += "This is a solution to the problem:\n" + solution + "\n\n"
    prompt += 'You are a software engineer.\n\n'
    prompt += one_reply
    prompt += "\n\nCan you repair the incorrect code?"
    return prompt

def buildSolutionAndTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out):
    if description is not None:
        prompt = "This is a programming problem description:\n" + description + "\n"
        if judge_result.get('fileName', None) is not None:
            prompt += "Your program should use file input and output. Read the input from a file named '" + judge_result['fileName'] + ".in' and write the output to a file named '" + judge_result['fileName'] + ".out'.\n\n"
        prompt += "### Time Limit\n" + str(judge_result['timeLimit']) + "ms\n\n"
        prompt += "### Memory Limit\n" + str(judge_result['memoryLimit']) + "KB\n\n"
        prompt += "This is an incorrect code to the problem:\n```c++\n" + code_to_fix + "```\n\n"
    else:
        prompt = append_prompt
    input_test, output_test = [], []
    problem_id = judge_result['problemId']
    judge_item = None
    for item in judge_result['notac']:
        if item['nantiStatusId'] == nanti_status_id:
            judge_item = item
            break
    if user_out == '未找到对应输出文件。':
        status = 'FE'
    elif user_out == '无法显示，输出包含二进制数据':
        status = 'BE'
    for i in range(case_max_cnt[judge_result['problemId']]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt += "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt += 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += "This is a solution to the problem:\n\n" + solution + "\n\n"
    prompt += "You are a software engineer. Can you repair the incorrect code?"
    return prompt

def buildAppendTestcasePrompt(judge_item, problem_id, status):
    prompt = append_prompt
    input_test, output_test = [], []
    for i in range(case_max_cnt[problem_id]):
        if (status == 'CE' or judge_item['extra']['statuses'][i] != 4):
            input_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['input']))
            output_test.append(add_eoln(tutorcode_api.get_testcase(problem_id, i + 1)['output']))
    if status == "CE":
        compile_log = parse_warning(judge_item['compileErrorLog']).strip()
        prompt += "There are some compilation errors of the incorrect code:\n\n" + compile_log + '\n\n'
    elif len(input_test) > 0:
        prompt += 'The incorrect code failed to pass the following test cases.\n'
        for i in range(len(input_test)):
            prompt += 'For the input:\n\n' + input_test[i] + '\n\nthe output should be:\n\n' + output_test[i] + '\n\n'
    prompt += "You are a software engineer. Can you repair the incorrect code?"
    return prompt

def buildPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, one_reply, prompt_type):
    if prompt_type == "default":
        return buildDefaultPrompt(judge_result, description, code_to_fix)
    elif prompt_type == "reply":
        return buildOneReplyPrompt(judge_result, nanti_status_id, description, code_to_fix, one_reply)
    elif prompt_type == "solution":
        return buildSolutionPrompt(judge_result, description, code_to_fix, solution)
    elif prompt_type == "reply_and_testcase":
        return buildOneReplyAndTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, status, one_reply)
    elif prompt_type == "testcase":
        return buildTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, status, user_out)
    elif prompt_type == "reply_and_solution_and_testcase4": # For Most LLMs
        return buildOneReplyAndSolutionAndTestcaseArray2Prompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, one_reply)
    elif prompt_type == "reply_and_solution_and_testcase7": # Only For Bard and Claude, Due to Limitation of Usage
        return buildOneReplyAndSolutionAndTestcaseImprovedNewPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out, one_reply)
    elif prompt_type == "reply_and_solution":
        return buildOneReplyAndSolutionPrompt(judge_result, nanti_status_id, description, code_to_fix, solution, one_reply)
    elif prompt_type == "solution_and_testcase":
        return buildSolutionAndTestcasePrompt(judge_result, nanti_status_id, description, code_to_fix, solution, status, user_out)
    elif prompt_type == "append_testcase":
        return buildAppendTestcasePrompt(judge_result['item'], judge_result['problemId'], OJ_STATUSES[judge_result['status']])