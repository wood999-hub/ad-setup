// 연습용 가짜 광고 데이터. 브라우저 localStorage 에 저장된다.
const DEFAULT = [
  { id: "A1001", name: "여름 반팔티", bid: 200, budget: 30000, status: "ON",
    imp: 12000, clk: 240, conv: 30, rev: 900000 },
  { id: "A1002", name: "린넨 셔츠", bid: 250, budget: 20000, status: "ON",
    imp: 8000, clk: 120, conv: 2, rev: 40000 },
  { id: "A1003", name: "슬리퍼", bid: 150, budget: 10000, status: "ON",
    imp: 3000, clk: 8, conv: 0, rev: 0 },
];
function loadAds() {
  try { return JSON.parse(localStorage.getItem("mockAds")) || DEFAULT; } catch (e) { return DEFAULT; }
}
function saveAds(ads) { localStorage.setItem("mockAds", JSON.stringify(ads)); }
