# 저장소 공통 경로·설정
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(TOOLS, '..'))
TRANSLATION = os.path.join(ROOT, 'translation')
TEXT = os.path.join(TRANSLATION, 'text')          # 번역 JSON (저장소에 포함)
WORK = os.path.join(ROOT, 'work')                 # 원본에서 뽑은 작업 파일 (gitignore)
ORIG = os.path.join(WORK, 'orig')                 # 원본 DAT/MCD/텍스처
FONTS = os.path.join(TOOLS, 'fonts')

NOTO = os.path.join(FONTS, 'NotoSansKR-VF.ttf')
PEN = os.path.join(FONTS, 'NanumPenScript-Regular.ttf')
_WIN_NOTO = 'C:/Windows/Fonts/NotoSansKR-VF.ttf'
if not os.path.exists(NOTO) and os.path.exists(_WIN_NOTO):
    NOTO = _WIN_NOTO

TITLE_ID = '00050000101AFF00'
CPK_NAME = 'data003.cpk'
# 원본 data003.cpk (일본판 v16)
ORIG_SHA1 = '9dfa60ddbb9b0e1ebcc313eae6ca081244c312b1'
ORIG_SIZE = 815910328
# 번역이 들어 있는 DAT (CPK 내 경로 ↔ translation/text 파일 이름)
def dat_path(key):
    return key.replace('__', '/', 1) + '.dat'   # ui__ui_title -> ui/ui_title.dat
SKIP_KEYS = {'ui__ui_option', 'ui__ui_gallery'}  # BC3 아틀라스 + 테스트 문구
