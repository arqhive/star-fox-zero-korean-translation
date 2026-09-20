# 원문+번역문 전체를 JSON 한 파일로 내보내기
#   python export_all.py [출력경로]
import sys, json, glob, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import TEXT
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser('~'), 'Desktop', '스타폭스 제로 원문+번역.json')

SCREEN = {
    'core__coreui': '공용 폰트(영숫자)',
    'ui__ui_core': '공용 UI (예·아니요, 스테이지 이름·부제)',
    'ui__ui_ending': '엔딩 자막·스태프 크레디트·청구서',
    'ui__ui_gallery': '갤러리(테스트 문구)',
    'ui__ui_hud': 'HUD·목표·결과 배너·보스 이름',
    'ui__ui_loading': '로딩 표시',
    'ui__ui_logo': '로고 화면',
    'ui__ui_msg_area_3': '에어리어 3 대사',
    'ui__ui_msg_briefing': '브리핑 대사',
    'ui__ui_msg_common': '공통 무전 대사',
    'ui__ui_msg_corneria': '코네리아 대사',
    'ui__ui_msg_corneria_2nd': '코네리아(2회차) 대사',
    'ui__ui_msg_corneriae3': '코네리아(E3판) 대사',
    'ui__ui_msg_ending': '엔딩 대사',
    'ui__ui_msg_fichina': '피치나 대사',
    'ui__ui_msg_fortuna': '포르투나 대사',
    'ui__ui_msg_prologue': '프롤로그 내레이션',
    'ui__ui_msg_sector_alpha': '섹터 α 대사',
    'ui__ui_msg_sector_beta': '섹터 β 대사',
    'ui__ui_msg_sector_gamma': '섹터 γ 대사',
    'ui__ui_msg_sector_omega': '섹터 Ω 대사',
    'ui__ui_msg_titania': '타이타니아 대사',
    'ui__ui_msg_training': '트레이닝 안내',
    'ui__ui_msg_venom': '베놈 대사',
    'ui__ui_msg_zoness': '조네스 대사',
    'ui__ui_option': '옵션(테스트 문구)',
    'ui__ui_pause': '일시정지 메뉴·조작 설명',
    'ui__ui_title': '타이틀·메인 메뉴',
    'ui__ui_tutorial': '튜토리얼(테스트 문구)',
}


def main():
    files, entries = [], []
    for jp in sorted(glob.glob(os.path.join(glob.escape(TEXT), '*.json'))):
        key = os.path.basename(jp)[:-5]
        rows = json.load(open(jp, encoding='utf-8'))
        n_tr = sum(1 for r in rows if r['ko'])
        files.append({'file': key, 'dat': key.replace('__', '/', 1) + '.dat',
                      'screen': SCREEN.get(key, ''), 'entries': len(rows), 'translated': n_tr})
        for r in rows:
            entries.append({'file': key, 'screen': SCREEN.get(key, ''), 'id': r['id'],
                            'event': r['event'], 'font': r['font'], 'ja': r['ja'], 'ko': r['ko']})
    doc = {
        'game': 'Star Fox Zero (Wii U, 일본판 00050000101AFF00)',
        'source': 'data003.cpk > ui/*.dat > mess*.mcd',
        'exported': datetime.date.today().isoformat(),
        'note': ('ko 가 빈 항목은 원문에 일본어가 없어 번역하지 않은 것(영문·숫자·기호). '
                 '표기: \\n 줄바꿈, {I숫자} 버튼 아이콘, {G0}...{/G0} 아이콘 묶음, {{ }} 중괄호 문자.'),
        'counts': {'files': len(files), 'entries': len(entries),
                   'translated': sum(1 for e in entries if e['ko'])},
        'files': files,
        'entries': entries,
    }
    json.dump(doc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s\n항목 %d개 (번역 %d개) / 파일 %d개 / %.1f MB'
          % (OUT, doc['counts']['entries'], doc['counts']['translated'],
             doc['counts']['files'], os.path.getsize(OUT) / 1e6))


if __name__ == '__main__':
    main()
