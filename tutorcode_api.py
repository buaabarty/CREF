import requests
import time
def fetch_data(id):
    url = "https://api.tutorcode.org/item/" + str(id)
    headers = {
        "API-KEY": "tutorcode_api_key_temp_52312"
    }
    retry_cnt = 0
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(response.status_code)
            retry_cnt += 1
            time.sleep(1)
            if retry_cnt >= 5:
                break
    return {'status': 'failed'}

def get_testcase(problem_id, case_id):
    url = f"https://api.tutorcode.org/testcase/{problem_id}/{case_id}"
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
    url = "https://api.tutorcode.org/judge"
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
