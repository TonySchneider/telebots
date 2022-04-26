import re
from googletrans import Translator


def get_translations(word):
    translator = Translator()
    trans_obj = translator.translate(word, dest='he')

    all_translations = trans_obj.extra_data.get('all-translations')
    if not all_translations:
        return [trans_obj.text] if hasattr(trans_obj, 'text') else None

    return_in_hebrew_list = []

    for translation in all_translations:
        current_list = translation[2]
        for trans in current_list:
            if any(isinstance(obj, float) for obj in trans):
                return_in_hebrew_list.append(trans[0])

    # add the main translation that without a punctuations.
    main_translation = trans_obj.text
    # check that this translation already not in the list
    if all(main_translation != re.sub(r'[^\w\s]', '', he_translate) for he_translate in return_in_hebrew_list):
        return_in_hebrew_list.append(main_translation)

    return list(set(return_in_hebrew_list))


# if __name__ == '__main__':
#     trans = get_translations("regardless")
#     # print(re.sub(r'[^\w\s]', '', trans[0]))
#     # print(trans[0].translate(str.maketrans('', '', string.punctuation)))
#
#     print(trans)