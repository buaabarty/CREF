import os
import difflib
import sys
import numpy as np
import tutorcode_api
import re

def find_modified_blocks(data1, data2):
    data1_lines = data1.split('\n')
    data2_lines = data2.split('\n')

    d = difflib.Differ()
    diff = list(d.compare(data1_lines, data2_lines))
    cnt = 0
    last_item = ' '
    for item in diff:
        if last_item[0] == ' ' and item[0] in ['-', '+']:
            cnt += 1
        last_item = item
    return cnt

if __name__ == "__main__":
    code_length = {}
    diff_hunk_cnt = {}
    titles = {}
    for id in range(1, 1240):
        print('processing', id)
        item = tutorcode_api.fetch_data(id)
        qa = item['tutorGuidance']
        description = item['problemDescription']
        solution = item['solutionDescription']
        code_to_fix = item['incorrectCode']
        judge_result = item['judgeResult']
        status_id = item['statusId']
        user_out = item['userOut']
        ground_truth = item['groudTruthCode']
        title = description.split('\n')[0].split('#')[-1].strip()
        problem_id = judge_result['problemId']
        titles[problem_id] = title
        if problem_id not in code_length:
            code_length[problem_id] = []
            diff_hunk_cnt[problem_id] = []
        max_len = max(len(code_to_fix.split('\n')), len(ground_truth.split('\n')))
        changes = find_modified_blocks(code_to_fix, ground_truth)
        code_length[problem_id].append(len(code_to_fix.split('\n')))
        diff_hunk_cnt[problem_id].append(find_modified_blocks(code_to_fix, ground_truth))
    print('title\tcode_length\tdiff_hunk_cnt')
    for problem_id in code_length:
        print('%s\t%.1f\t%.1f' % (titles[problem_id], sum(code_length[problem_id]) / len(code_length[problem_id]), sum(diff_hunk_cnt[problem_id]) / len(diff_hunk_cnt[problem_id])))
