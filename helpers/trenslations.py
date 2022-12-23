import re
from googletrans import Translator
from retry import retry

from helpers.loggers import get_logger

logger = get_logger(__file__)


@retry(exceptions=(TypeError, AttributeError), tries=5, delay=5, jitter=3)
def translate_it(text: str, lang_from: str, lang_to: str):
    translated_text = None

    translator = Translator()
    trans_obj = translator.translate(text=text,
                                     src=lang_from,
                                     dest=lang_to)
    translated_text = trans_obj.text
    return translated_text


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


if __name__ == '__main__':
    # print(get_translations('corresponds'))

    sentence = """
**🛑 الشهيد المجاهد احمد دراغمة ابن مدينة طوباس والذي ارتقى اثناء تصديه لقوات الاحتلال المتوغلة بقبر يوسف في نابلس..
    """
    print(translate_it(sentence, lang_from='ar', lang_to='he'))
