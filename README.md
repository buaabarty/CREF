# CREF
CREF codes with the description of benchmark TutorCode

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
