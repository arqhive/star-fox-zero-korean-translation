# 번역 검수 가이드

플레이하면서 이상한 곳을 찾으면 아래 순서로 고친다.

## 1. 문장 찾기

`translation/text/*.json` 을 문구로 검색한다. 파일 이름이 곧 화면 구역이다.

| 파일 | 내용 |
|---|---|
| `ui__ui_msg_<스테이지>.json` | 스테이지별 무전 대사 |
| `ui__ui_msg_common.json` | 어느 스테이지에서나 나오는 공통 대사 |
| `ui__ui_msg_briefing.json` / `prologue` | 브리핑 / 프롤로그 내레이션 |
| `ui__ui_msg_training.json` | 트레이닝 안내 |
| `ui__ui_hud.json` | HUD, 목표, 결과 배너, 보스 이름 |
| `ui__ui_title.json` / `ui__ui_pause.json` | 타이틀·메인 메뉴 / 일시정지 메뉴 |
| `ui__ui_core.json` | 예·아니요, 스테이지 이름과 부제 |
| `ui__ui_ending.json` | 엔딩 자막·스태프 크레디트 |

각 항목의 `event` 가 화자와 상황을 알려 준다(`FALCO_CORNERIA_006` = 코네리아의 팔코 대사).

## 2. 고치기

`ko` 항목만 고친다. `ja`, `id`, `event`, `font` 와 항목 순서는 건드리지 않는다.

- 표기·말투: `translation/glossary.md`
- 구두점·문체: `translation/punct_rules.md`
- 같은 원문이 여러 파일에 있으면 함께 고친다(스테이지 공통 대사가 많다).
- 폰트만 다른 쌍둥이 항목(`0047.0`, `0047.1`, `0047.2`)은 같은 문장을 넣는다.

표기법: `\n` 줄바꿈, `{I숫자}` 버튼 아이콘, `{G0}`…`{/G0}` 아이콘 묶음, `{{` `}}` 중괄호.

## 3. 검사

```
python tools/lint.py                 # 전체
python tools/lint.py ui__ui_hud      # 파일 지정
```

- **태그 불일치**: `{I…}` 개수가 원문과 다르다.
- **일본어/한자 남음**: 번역이 덜 됐다.
- **줄 폭 초과**: 화면 밖으로 나간다. 줄바꿈 위치를 바꾸거나 문장을 줄인다.
- **줄 수 초과**: 원문보다 줄이 많다. 대사창을 벗어날 수 있다.

## 4. 빌드·확인

```
python tools/patch.py <원본 data003.cpk> -o out
```

`out/data003.cpk` 를 SD카드나 Cemu 그래픽 팩에 넣고 확인한다.
글자 모양·자간이 이상하면 `tools/font_render.py` 의 `STYLES`(폰트ID별 크기·굵기·여백)를 조정한다.
