import argparse
import json
import requests
import os
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument("--lesson_id", type=str, required=True)
parser.add_argument("--step_id", type=str, required=False)
parser.add_argument("--position", type=str, required=True)
parser.add_argument("--token", type=str, required=True)
args = parser.parse_args()


os.makedirs("submissions", exist_ok=True)

headers = {"Authorization": f"Bearer {args.token}"}
params = {"step": args.step_id}

response = requests.get(
    "https://stepik.org/api/submissions", headers=headers, params=params
)

data = response.json()

submissions = data.get("submissions", [])


for submission in submissions:
    if submission.get("status") == "correct":
        status_str = "OK"
    else:
        status_str = "FAIL"

    filename = f"{args.lesson_id}_{args.position}_{submission['id']}_{status_str}.json"
    filepath = os.path.join("submissions", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(submission, f, ensure_ascii=False, indent=2)

    print(f"Сохранено: {filename}")
