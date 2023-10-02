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
```

# TutorCode API

GET http://tutorcode.org/item/${id}

RESPONSE

```
{
    'id': id,
    'incorrectCode': '...',
    'problemId': 1,
    'problemDescription': '...',
    'judgeResult': {...},
    'tutorGuidance': '...',
    'solutionDescription': '...',
    'groundTruthCode': '...',
}
```

POST http://tutorcode.org/judge

```
{
    'code': '...',
    'problemId': 1
}
```

RESPONSE

```
{
    'judgeResult': {...}
}
```
