import wikipedia


def get_summary():
    wikipedia.set_lang('ru')
    text = wikipedia.summary(object)
    return text
