# 스타폭스 제로 한글 패치

*Star Fox Zero* (Wii U, 일본판 `00050000101AFF00`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

- 게임 내 텍스트 전체 한글화 — 대사 2,000여 개, HUD, 타이틀·일시정지 메뉴, 브리핑, 트레이닝, 엔딩
- 타이틀 로고의 「スターフォックス ゼロ」와 엔딩 청구서 이미지도 한글로 교체
- 폰트는 원본과 같은 방식(파일별 사전 렌더 글리프 아틀라스)으로 새로 그려 넣습니다
- 고유명사는 정식 한국어판 『스타폭스 64 3D』·『스타폭스』(Switch 2)의 표기를 따릅니다
- 확인 환경: Cemu / 실기(Wii U + SDCafiine)

> 이 저장소에는 **게임 데이터가 들어 있지 않습니다.** 패치를 만들려면 본인이 소유한
> 일본판 게임에서 덤프한 `data003.cpk` 가 필요합니다.

## 사용자용: 패치 적용

릴리스에서 받은 압축을 풀고, 원본 `data003.cpk` 를 같은 폴더에 둔 뒤 `패치하기.bat` 를 실행하면
`out\data003.cpk` 가 만들어집니다. (파이썬이 함께 들어 있어 따로 설치할 필요가 없습니다.)

| 원본 (일본판 data003.cpk) | 값 |
|---|---|
| 크기 | 815,910,328 바이트 |
| SHA-1 | `9dfa60ddbb9b0e1ebcc313eae6ca081244c312b1` |

만들어진 파일을 아래 위치에 넣습니다.

- **실기 (Aroma + SDCafiine)**: `sd:\wiiu\sdcafiine\00050000101AFF00\StarFoxZero_KR\content\data003.cpk`
- **Cemu**: 그래픽 팩 폴더에 `rules.txt`(`titleIds = 00050000101AFF00`)와 `content\data003.cpk` 를 두고 팩을 켭니다.

원본 게임 폴더는 고치지 않습니다.

### 알려진 문제

- 음성은 일본어 그대로입니다.
- 스테이지 간판 등 게임 세계관 속 영어 표기(`CORNERIA PRECIOUS METALS LTD.`)는 그대로 두었습니다.
- 북미·유럽판에는 적용할 수 없습니다.

## 개발자용: 직접 빌드

```
pip install -r requirements.txt
python tools/patch.py <원본 data003.cpk> -o out
```

| 항목 | 비고 |
|---|---|
| Python 3.11 이상 | numpy, Pillow |
| 원본 `data003.cpk` | 일본판에서 덤프 |
| 폰트 | `tools/fonts/` 에 포함 (Noto Sans KR, 나눔손글씨 펜 — 둘 다 OFL) |

### 번역 수정

1. `translation/text/*.json` 의 `ko` 항목을 고칩니다. 표기 규칙은
   [`translation/glossary.md`](translation/glossary.md)(용어·말투)와
   [`translation/punct_rules.md`](translation/punct_rules.md)(구두점·문체)에 있습니다.
2. `python tools/lint.py` — 태그 손상, 일본어 잔존, 줄 폭·줄 수 초과를 검사합니다.
3. `python tools/patch.py ...` 로 다시 빌드합니다.

텍스트 표기: `\n` 줄바꿈, `{I숫자}` 버튼 아이콘, `{G0}`…`{/G0}` 아이콘 묶음, `{{` `}}` 중괄호 문자.

### 저장소 구성

| 경로 | 내용 |
|---|---|
| `tools/` | 패치 빌더와 포맷 도구 (CPK·DAT·MCD·GX2 텍스처) |
| `translation/text/` | 번역 JSON 29개 (원문 `ja` + 번역 `ko`) |
| `translation/*.md` | 용어집, 구두점·문체 규칙 |
| `docs/TECHNICAL.md` | 파일 포맷과 패치 방식 설명 |
| `release/` | 배포용 안내문 |
| `work/` | 원본에서 뽑은 작업 파일 (커밋하지 않음) |

## 라이선스

- 코드: [MIT](LICENSE)
- 번역문: CC BY-NC-SA 4.0
- 번들 폰트: SIL Open Font License 1.1 (`tools/fonts/OFL.txt`)
- `tools/addrlib.py` 는 [aboood40091/BFRES-Tool](https://github.com/aboood40091/BFRES-Tool) 의 Wii U 텍스처 주소 계산 코드입니다 (GPLv3).
- 게임 데이터의 저작권은 닌텐도에 있습니다. 이 저장소는 게임 데이터를 포함하지 않습니다.
