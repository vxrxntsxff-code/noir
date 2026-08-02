import re, json

def _restore_json(s):
    s = re.sub(r'([{,]\s*)([^"\\s{},:]+)(\s*:)', r'\1"\2"\3', s)
    
    def skip_ws(s, pos):
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        return pos

    def parse_value(s, pos):
        pos = skip_ws(s, pos)
        if pos >= len(s):
            raise ValueError("Unexpected end")
        if s[pos] == '{':
            return parse_object(s, pos)
        elif s[pos] == '[':
            return parse_array(s, pos)
        elif s[pos] == '"':
            return parse_string(s, pos)
        else:
            start = pos
            while pos < len(s) and s[pos] not in ',}]':
                pos += 1
            val = s[start:pos].strip()
            if re.match(r'^-?\d+(\.\d+)?$', val):
                return (float(val) if '.' in val else int(val), pos)
            elif val == 'true':
                return (True, pos)
            elif val == 'false':
                return (False, pos)
            elif val == 'null':
                return (None, pos)
            else:
                return (val, pos)

    def parse_string(s, pos):
        pos += 1
        result = []
        while pos < len(s) and s[pos] != '"':
            if s[pos] == '\\' and pos + 1 < len(s):
                result.append(s[pos+1])
                pos += 2
            else:
                result.append(s[pos])
                pos += 1
        return (''.join(result), pos + 1)

    def parse_object(s, pos):
        pos += 1
        obj = {}
        while True:
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == '}':
                return (obj, pos + 1)
            if pos >= len(s):
                return (obj, pos)
            if s[pos] == '"':
                key, pos = parse_string(s, pos)
            else:
                start = pos
                while pos < len(s) and s[pos] != ':':
                    pos += 1
                key = s[start:pos].strip()
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ':':
                pos += 1
            else:
                raise ValueError(f"Expected : at {pos}")
            val, pos = parse_value(s, pos)
            obj[key] = val
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ',':
                pos += 1
            elif pos < len(s) and s[pos] == '}':
                return (obj, pos + 1)
            else:
                break
        return (obj, pos)

    def parse_array(s, pos):
        pos += 1
        arr = []
        while True:
            pos = skip_ws(s, pos)
            if pos >= len(s) or s[pos] == ']':
                return (arr, pos + 1)
            val, pos = parse_value(s, pos)
            arr.append(val)
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ',':
                pos += 1
            elif pos < len(s) and s[pos] == ']':
                return (arr, pos + 1)
            else:
                break
        return (arr, pos)

    result, _ = parse_value(s, 0)
    return result

# Realistic Telegram /start update
real_update = '''{update_id:123456789,message:{message_id:1,from:{id:811147128,is_bot:false,first_name:Dmitry,last_name:Vorontsoff,username:vxrxntsxff,language_code:en},chat:{id:811147128,first_name:Dmitry,last_name:Vorontsoff,username:vxrxntsxff,type:private},date:1722000000,text:/start}}'''

print("Testing realistic update:")
try:
    result = _restore_json(real_update)
    print("Result:", json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"ERROR: {e}")
