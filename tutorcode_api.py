import requests
def fetch_data(id):
    url = "http://170.187.174.223:9999/item/" + str(id)
    headers = {
        "API-KEY": "tutorcode_api_key_temp_52312"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code)
        return {'status': 'failed'}

def get_testcase(problem_id, case_id):
    url = f"http://170.187.174.223:9999/testcase/{problem_id}/{case_id}"
    headers = {
        "API-KEY": "tutorcode_api_key_temp_52312"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code)
        return {'status': 'failed'}

def judge(id, code):
    url = "http://170.187.174.223:9999/judge"
    headers = {
        "API-KEY": "tutorcode_api_key_temp_52312",
        'Content-Type': 'application/json',
    }
    payload = {
        'code': code,
        'id': id,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code)
        return {'status': 'failed'}

if __name__ == "__main__":
    import sys
    if sys.argv[1] == 'fetch':
        print(fetch_data(int(sys.argv[2])))
    elif sys.argv[1] == 'testcase':
        print(get_testcase(int(sys.argv[2]), int(sys.argv[3])))
    else:
        print(judge(int(sys.argv[2]), open(sys.argv[3]).read()))
