# CREF
CREF codes with the description of benchmark TutorCode

# preparement
```
pip install -r requirements.txt
```

# RQ-1
```
python3 experiment.py 1 5 default gpt-4
python3 experiment.py 2 5 default gpt-3.5-turbo-0613
python3 experiment.py 3 5 default claude
python3 experiment.py 4 5 default bard
python3 experiment.py 5 5 default codellama
python3 experiment.py 6 5 default starchat
python3 experiment.py 7 5 default vicuna
python3 experiment.py 8 5 default codegen16b
python3 experiment.py 9 5 default codegen6b
python3 experiment.py 10 5 default codet5p
python3 experiment.py 11 5 default incoder
python3 experiment.py 12 5 default replit
```

# RQ-2
```
python3 experiment.py 13 5 reply gpt-4
python3 experiment.py 14 5 solution gpt-4
python3 experiment.py 15 5 testcase gpt-4
python3 experiment.py 16 5 reply_and_solution gpt-4
python3 experiment.py 17 5 reply_and_testcase gpt-4
python3 experiment.py 18 5 solution_and_testcase gpt-4
python3 experiment.py 19 5 reply_and_solution_and_testcase4 gpt-4
```

Other LLM can replace `gpt-4` with correseponding model name, detailed in `buildPrompt` function of `prompts.py` file.

# RQ-3
```
python3 experiment.py 20 5 interactive gpt-4
python3 experiment.py 21 5 interactive gpt-3.5-turbo
python3 experiment.py 22 5 interactive claude
python3 experiment.py 23 5 interactive bard
python3 experiment.py 24 5 interactive codellama
```

The first parameter of each command should be unique.

# TutorCode API

The usage of TutorCode API refers to the source code `tutorcode_api.py`.
