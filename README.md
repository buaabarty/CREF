# CREF
CREF codes with the description of benchmark TutorCode

# preparement

1. You should install llvm-16 for calculating RPSR results, and set the llvm directory like `/usr/lib/llvm-16/lib/libclang.so.1` within `settings.py`.

2. Install python libraries:

```
pip install -r requirements.txt
```

3. Set the values in the `settings.py`, such as OpenAI api_key.

# RQ-1
```
python3 experiment.py 5 default gpt-4
python3 experiment.py 5 default gpt-3.5-turbo-0613
python3 experiment.py 5 default claude
python3 experiment.py 5 default bard
python3 experiment.py 5 default codellama
python3 experiment.py 5 default starchat
python3 experiment.py 5 default vicuna
python3 experiment.py 5 default codegen16b
python3 experiment.py 5 default codegen6b
python3 experiment.py 5 default codet5p
python3 experiment.py 5 default incoder
python3 experiment.py 5 default replit
```

# RQ-2
```
python3 experiment.py 5 reply gpt-4
python3 experiment.py 5 solution gpt-4
python3 experiment.py 5 testcase gpt-4
python3 experiment.py 5 reply_and_solution gpt-4
python3 experiment.py 5 reply_and_testcase gpt-4
python3 experiment.py 5 solution_and_testcase gpt-4
python3 experiment.py 5 reply_and_solution_and_testcase4 gpt-4
```

Other LLM can replace `gpt-4` with correseponding model name, detailed in `buildPrompt` function of `prompts.py` file.

# RQ-3
```
python3 experiment.py 5 interactive gpt-4
python3 experiment.py 5 interactive gpt-3.5-turbo
python3 experiment.py 5 interactive claude
python3 experiment.py 5 interactive bard
python3 experiment.py 5 interactive codellama
```

# TutorCode API

The usage of TutorCode API refers to the source code `tutorcode_api.py`.
