스타폭스 제로 한글 패치 (비공식 팬 패치)
=========================================

이 패치는 게임 데이터를 포함하지 않습니다.
본인이 소유한 일본판 게임에서 덤프한 파일이 필요합니다.


1. 준비물
---------
- 일본판 스타폭스 제로 (타이틀 ID 00050000101AFF00) 에서 덤프한 content 폴더
- 그 안의 data003.cpk
    크기   : 815,910,328 바이트
    SHA-1  : 9dfa60ddbb9b0e1ebcc313eae6ca081244c312b1
- 실기에 넣으려면 Aroma + SDCafiine 플러그인, 또는 Cemu


2. 패치 만들기
--------------
1) 받은 압축 파일을 아무 폴더에나 풉니다.
2) 원본 data003.cpk 를 압축을 푼 폴더에 복사합니다.
   (또는 나중에 물어보는 경로에 그대로 두어도 됩니다)
3) "패치하기.bat" 를 두 번 클릭합니다.
4) 2~5분 정도 걸립니다. 끝나면 out 폴더에 한글판 data003.cpk 가 생깁니다.

파이썬이 함께 들어 있어서 따로 설치할 필요가 없습니다.
백신이 python.exe 를 물어보면 허용해 주세요 (파이썬 재단 공식 배포본입니다).


3. 넣는 위치
------------
[ 실기 — Aroma + SDCafiine ]
  sd:\wiiu\sdcafiine\00050000101AFF00\StarFoxZero_KR\content\data003.cpk

  (StarFoxZero_KR 자리에는 아무 이름이나 써도 됩니다)
  SD카드를 뺄 때는 "하드웨어 안전하게 제거"를 먼저 해 주세요.

[ Cemu ]
  Cemu 의 graphicPacks 폴더에 아래처럼 만듭니다.

  graphicPacks\SFZeroKR\rules.txt
  graphicPacks\SFZeroKR\content\data003.cpk

  rules.txt 내용:
    [Definition]
    titleIds = 00050000101AFF00
    name = Korean Translation
    path = "Star Fox Zero/Mods/Korean Translation"
    description = 스타폭스 제로 한글화
    version = 7

  Cemu 를 켜고 Options - Graphic packs 에서 켜 주세요.

어느 쪽이든 원본 게임 폴더는 고치지 않습니다. 패치를 빼려면 파일만 지우면 됩니다.


4. 무엇이 한글로 바뀌나
-----------------------
- 대사 전체 (프롤로그, 스테이지 무전, 브리핑, 트레이닝, 엔딩)
- HUD, 타이틀·메인 메뉴, 일시정지 메뉴, 조작 설명, 세이브·amiibo 안내
- 타이틀 로고의 「スターフォックス ゼロ」
- 엔딩 청구서 이미지

음성은 일본어 그대로입니다.


5. 알려진 문제
--------------
- 북미판·유럽판에는 쓸 수 없습니다.
- 게임 세계관 속 영어 간판은 그대로 두었습니다.


문제가 있거나 어색한 문장을 찾으면 알려 주세요.
