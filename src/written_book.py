def get_text(text, color='black', bold=False):
    obj = {
        'text': text,
        'color': color
    }
    if bold:
        obj['bold'] = True
    return obj


def get_link(text, color, action, value):
    return {
        'text': text,
        'color': color,
        'underlined': True,
        'clickEvent': {
            'action': action,
            'value': value
        }
    }
