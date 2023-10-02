import requests
def fetch_data(id):
    url = "http://170.187.174.223:9999/item/" + str(id)
    headers = {
        "API-KEY": "tutorcode_api_key_temp_52312"
    }

    response = requests.get(url, headers=headers)

    # 检查响应是否成功
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

    # 检查响应是否成功
    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code)
        return {'status': 'failed'}

if __name__ == "__main__":
    import sys
    print(fetch_data(int(sys.argv[1])))
    print(judge(int(sys.argv[1]), '#include <bits/stdc++.h>\nusing namespace std;\nlong long n;\nset<long long> a;\nint main() {\n    freopen("elevater.in", "r", stdin);\n    freopen("elevator.out", "w", stdout);\n    cin >> n;\n    long long int sum = 0;\n    long long x1, last = 0;\n    for (int i = 1; i <= n; i++) {\n        int x;\n        cin >> x;\n        a.insert(x);\n    }\n    for (set<long long>::iterator it = a.begin(); it != a.end(); it++) {\n        x1 = (*it);\n        if (x1 > last) {\n            sum += 5 * (x1 - last);\n        }else {\n            sum += 4 * (last - x1);\n        }\n        last = x1;\n    }\n    sum += a.size() * 3;\n    sum += n * 2;\n    if (x1 == 0) {\n        cout << sum << endl;\n        return 0;\n    } else {\n        sum += last * 4;\n        cout << sum << endl;\n    }\n    return 0; \n}\n'))