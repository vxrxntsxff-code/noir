import re, json

def _restore_json(s):
    import re
    result = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', s)
    result = re.sub(r'(:\s*)(/[a-zA-Z0-9_/.-]*)', r'\1"\2"', result)
    result = re.sub(r'(:\s*)(@[a-zA-Z0-9_]*)', r'\1"\2"', result)
    result = re.sub(r'([{,]\s*)(/[a-zA-Z0-9_/.-]*)(\s*:)', r'\1"\2"\3', result)
    result = re.sub(r'([{,]\s*)(@[a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', result)
    result = re.sub(r'(:\s*)([a-zA-Z_][a-zA-Z0-9_:/.]*)(\s*[,}])', r'\1"\2"\3', result)
    result = re.sub(r'"true"', 'true', result)
    result = re.sub(r'"false"', 'false', result)
    result = re.sub(r'"null"', 'null', result)
    return json.loads(result)

tests = [
    '{message:{chat:{id:811147128,type:private},text:/start}}',
    '{action:payment_confirm,order_id:test123}',
    '{update_id:123,message:{message_id:1,from:{id:811147128},chat:{id:811147128,type:private},text:hi}}',
    '{callback_query:{id:abc,data:pay:qr}}',
]

for t in tests:
    print(f'Input: {t}')
    try:
        result = _restore_json(t)
        print(f'Output: {result}')
    except Exception as e:
        print(f'ERROR: {e}')
    print()
