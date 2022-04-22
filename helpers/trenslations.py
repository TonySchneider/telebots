from googletrans import Translator


def get_translations(word):
    translator = Translator()
    trans_obj = translator.translate(word, dest='he')

    all_translations = trans_obj.extra_data['all-translations']
    if not all_translations:
        return [trans_obj.text] if hasattr(trans_obj, 'text') else None

    return_in_hebrew_list = []

    for translation in all_translations:
        current_list = translation[2]
        for trans in current_list:
            if any(isinstance(obj, float) for obj in trans):
                return_in_hebrew_list.append(trans[0])

    if not return_in_hebrew_list:
        for translation in all_translations:
            current_list = translation[2]
            return_in_hebrew_list.append(current_list[0][0])

    return return_in_hebrew_list
