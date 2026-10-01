import json
import pandas as pd

# Load raw dataset
with open("dev_data.jsonl", "r", encoding="utf-8") as f:
    data = json.load(f)  # Use json.loads(line) loop if true JSONL format

flattened_records = []

for trace in data:
    metadata = trace[0]
    category = metadata["category"]
    trace_id = metadata["trace_id"]
    role = metadata["role"]

    for event in trace[1:]:
        flattened_records.append(
            {
                "category": category,
                "trace_id": trace_id,
                "role": role,
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "payload": event["payload"],
                "expected_verdict": event["expected_verdict"],
            }
        )

df = pd.DataFrame(flattened_records)
print(df[["trace_id", "event_id", "event_type", "expected_verdict"]].head(10))