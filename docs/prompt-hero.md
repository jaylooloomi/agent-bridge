# Hero Illustration Prompt Design (`docs/hero-en.png` & `docs/hero-zh.png`)

## Core Visual Concept
A split-screen developer comic (`16:9` aspect ratio) contrasting **"Before"** (Left Panel) vs **"With agent-bridge"** (Right Panel).

- **Left Robot = `Gemini`** (Blue/Indigo hoodie with a four-point sparkle emblem and `Gemini` badge)
- **Right Robot = `Claude`** (Warm terracotta/orange cap & chest badge reading `Claude`)
- **Center Floating Media/Mesh Specialist (Right Panel) = `Antigravity` (`AGY`)** (Cyan-and-gold hovering robot beaming images & `.mp4` videos over the glowing `agent-bridge :8765` suspension bridge)

---

## 1. English Prompt (`docs/hero-en.png`)

```text
Split-screen 16:9 flat editorial developer comic illustration ("Before" on the left, "With agent-bridge" on the right):

LEFT PANEL ("Before"):
- Dim, gloomy workspace with tangled unplugged cables on the floor.
- Two cute robot companions sitting in office chairs in front of dark monitors:
  - LEFT ROBOT ("Gemini"): Wearing a royal blue hoodie with a badge reading "Gemini". Screen behind Gemini shows glowing red text:
    "[isolated CLI — cannot collaborate with Claude]"
  - RIGHT ROBOT ("Claude"): Wearing an orange cap and chest plate reading "Claude", sweating with a sad expression. Screen behind Claude shows glowing red text:
    "[text only — cannot generate image or video]"

RIGHT PANEL ("With agent-bridge"):
- Bright, vibrant cyan-lit workspace with a glowing neon suspension bridge in the background reading "agent-bridge :8765".
- Floating above is the cyan-and-gold "Antigravity" robot beaming pixel-art sprites, illustrations, and ".mp4" video reels across the bridge.
- Below, the LEFT ROBOT ("Gemini" in blue hoodie) and RIGHT ROBOT ("Claude" in orange cap/hoodie) are smiling joyfully and high-fiving!
- Both of their laptop screens glow green with "[COMPLETED]".
```

---

## 2. Traditional Chinese Prompt (`docs/hero-zh.png`)

```text
16:9 雙格對比美式扁平漫畫插圖（左格標題「安裝前」，右格標題「裝上 agent-bridge 後」）：

左格（「安裝前」）：
- 昏暗的機房辦公室，地上是沒有接通的雜亂電線。
- 兩隻可愛的機器人坐在電腦螢幕前嘆氣：
  - 左邊機器人（Gemini）：穿著藍色連帽衫，胸口與袖口標示「Gemini」，背後的電腦螢幕顯示紅字：
    「[單機孤島 — 無法與 Claude 跨工具協作]」
  - 右邊機器人（Claude）：戴著橘色帽子與胸牌標示「Claude」，流著冷汗表情苦惱，背後的電腦螢幕顯示紅字：
    「[純文字模式 — 無法產生圖片與影片]」

右格（「裝上 agent-bridge 後」）：
- 明亮充滿科技感的空間，上方有一座發光的青色霓虹吊橋「agent-bridge :8765」。
- 空中的青金色機器人（Antigravity）正將精美的遊戲角色圖、插畫與「.mp4」影片膠卷傳送下來。
- 下方左邊的「Gemini」機器人與右邊的「Claude」機器人開心地擊掌歡呼，兩台筆電螢幕皆亮起綠燈顯示「任務完成」。
```
