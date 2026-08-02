import re, json

def _restore_json(s):
    """Tokenize and parse stripped-quote JSON."""
    
    # First, quote keys properly
    s = re.sub(r'([{,]\s*)([^"\s{},:]+)(\s*:)', r'\1"\2"\3', s)
    
    # Then parse using tokenization
    pos = 0
    
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
        elif s[pos:pos+4] in ('true', 'null'):
            val = 'true' if s[pos:pos+4] == 'true' else 'null'
            return (val if val != 'null' else None, pos + 4)
        elif s[pos:pos+5] == 'false':
            return (False, pos + 5)
        else:
            # Number or unquoted string
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
                return (val, pos)  # unquoted string
    
    def parse_string(s, pos):
        pos += 1  # skip opening "
        start = pos
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
        pos += 1  # skip {
        obj = {}
        while True:
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == '}':
                pos += 1
                break
            if pos >= len(s):
                break
            
            # Parse key
            if s[pos] == '"':
                key, pos = parse_string(s, pos)
            else:
                start = pos
                while pos < len(s) and s[pos] not in ':':
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
                pos += 1
                break
            else:
                break
        
        return obj, pos
    
    def parse_array(s, pos):
        pos += 1  # skip [
        arr = []
        while True:
            pos = skip_ws(s, pos)
            if pos >= len(s) or s[pos] == ']':
                pos += 1
                break
            val, pos = parse_value(s, pos)
            arr.append(val)
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ',':
                pos += 1
            elif pos < len(s) and s[pos] == ']':
                pos += 1
                break
            else:
                break
        return arr, pos
    
    result, _ = parse_value(s, 0)
    return result

tests = [
    '{"x":1,"y":"hi"}',
    '{message:{chat:{id:811147128,type:private},text:/start}}',
    '{callback_query:{id:abc,data:pay:qr}}',
    '{is_bot:false,text:hi,first_name:Dmitry}',
    '{"action":"payment_confirm","order_id":"test123"}',
]

for t in tests:
    print(f'Input: {t}')
    try:
        result = _restore_json(t)
        print(f'Output: {result}')
    except Exception as e:
        print(f'ERROR: {e}')
    print()
