// 연습용 가짜 광고센터 데이터 (브라우저 localStorage 에 저장). 실제 G마켓 광고센터 구조를 흉내냄.
const DEFAULT_GROUP = {
  name: "MK관리 REV.3 추가-FJUX",
  budget: 20000,
  products: [
    { no: "2168720238", name: "조명만들기 키트 /단품구성", keywords: [
      ["키트", 430, 400], ["미술놀이", 820, 800], ["색칠공부", 900, 1000], ["과학키트", 1200, 1350],
      ["겨울만들기", 900, 950], ["만들기자랑", 600, 650], ["조명만들기", 480, 500], ["유아장난감", 760, 800], ["공예", 610, 650],
    ]},
  ],
};
// 키워드별 가짜 성과 [노출, 클릭, 전환, 매출] - 규칙 엔진 연습용
const FAKE_PERF = {
  "키트": [5000, 120, 6, 180000], "미술놀이": [3000, 60, 0, 0], "과학키트": [2000, 45, 1, 20000],
  "색칠공부": [800, 10, 0, 0], "겨울만들기": [4000, 80, 4, 300000],
};
function loadGroup() {
  try { return JSON.parse(localStorage.getItem("mockGroup")) || structuredClone(DEFAULT_GROUP); }
  catch (e) { return structuredClone(DEFAULT_GROUP); }
}
function saveGroup(g) { localStorage.setItem("mockGroup", JSON.stringify(g)); }
const won = n => Number(n).toLocaleString();
