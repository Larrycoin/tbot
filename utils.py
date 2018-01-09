'''
'''


def btc2str(val):
    if val:
        return '%.2fS' % (val * 1000000)
    else:
        return val


def str2btc(s):
    if not isinstance(s, str):
        val = s
    elif s[-1] == 's':
        val = float(s[:-1]) * 0.00000001
    elif s[-1] == 'S':
        val = float(s[:-1]) * 0.000001
    else:
        val = float(s)
    return val

# utils.py ends here
