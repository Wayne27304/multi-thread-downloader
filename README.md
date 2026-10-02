# Multi-Thread Downloader

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](en.md) · **繁體中文**

一個使用 Python 與 Tkinter 製作的簡潔多線程 HTTP/HTTPS 下載器。

支援 HTTP Range 分段下載時，可以將檔案切分成多個區段並使用多條連線同時下載，以提升部分伺服器環境下的下載效率。

---

## 功能

- 多線程 / 多連線下載
- 支援最多 **100 條連線**
- 自動偵測伺服器是否支援 HTTP Range
- 支援 Range 時自動進行分段下載
- 不支援 Range 時自動降級為單一連線
- 即時顯示下載進度
- 顯示已下載大小與總檔案大小
- 支援取消下載
- 支援自訂檔案儲存位置
- 自動從 URL 判斷預設檔名
- 使用 `.part` 暫存檔避免直接寫入最終檔案
- 下載完成後自動重新命名為目標檔案
- Windows Tkinter 圖形介面
- 不需要第三方 Python 套件

---

## Screenshot

> 將你的程式截圖放在這裡即可。

```text
docs/
└── screenshot.png
```

例如：

```markdown
![Multi-Thread Downloader](docs/screenshot.png)
```

---

## 系統需求

- Python **3.x**
- Tkinter
- 可連線至 HTTP / HTTPS 伺服器的網路環境

本專案主要使用 Python 標準函式庫，因此不需要透過 `pip` 安裝額外套件。

---

## 安裝

### 1. Clone 專案

```bash
git clone https://github.com/Wayne27304/multi-thread-downloader.git
cd multi-thread-downloader
```

### 2. 啟動程式

假設主程式檔案為 `main.py`：

```bash
python main.py
```

Windows 也可以使用：

```powershell
py main.py
```

---

## 使用方式

啟動程式後：

1. 輸入要下載的 HTTP / HTTPS URL。
2. 選擇檔案儲存位置。
3. 設定連線數。
4. 按下 **開始下載**。
5. 程式會自動判斷伺服器是否支援 Range 分段下載。
6. 如果支援，程式會使用多條連線進行下載。
7. 如果不支援，會自動改用單一連線。

預設連線數為：

```text
8
```

最大可以設定：

```text
100
```

---

## 多線程下載原理

程式首先會向伺服器發送：

```http
Range: bytes=0-0
```

如果伺服器回覆：

```http
206 Partial Content
```

並提供有效的：

```http
Content-Range
```

例如：

```http
Content-Range: bytes 0-0/104857600
```

程式就可以取得檔案總大小，並將檔案切割成多個區段。

例如設定：

```text
4 條連線
```

一個檔案可能被分成：

```text
Connection 1 → bytes 0 - 26214399
Connection 2 → bytes 26214400 - 52428799
Connection 3 → bytes 52428800 - 78643199
Connection 4 → bytes 78643200 - 104857599
```

每條連線負責自己的區段，最後直接寫入 `.part` 暫存檔的對應位置。

下載完成後：

```text
example.zip.part
```

會被重新命名成：

```text
example.zip
```

---

## 不支援分段下載

如果伺服器不支援 HTTP Range，程式不會強制進行多線程下載。

而是自動顯示：

```text
伺服器不支援分段下載，改用單一連線
```

並使用普通 HTTP 下載方式。

這可以避免因伺服器不支援 Range 而造成下載失敗。

---

## 下載進度

當伺服器提供檔案總大小時，介面會顯示：

```text
75.4%

75.40 MB / 100.00 MB
```

如果伺服器沒有提供 `Content-Length`，則會顯示目前已下載大小：

```text
已下載 75.40 MB（總大小未知）
```

並使用不定進度模式顯示下載狀態。

---

## 取消下載

下載進行期間可以按下：

**取消**

程式會停止後續下載工作。

未完成的暫存檔會保留，例如：

```text
example.zip.part
```

目前版本不會自動從 `.part` 檔案繼續下載。

---

## 連線數

可以設定：

```text
1 ~ 100
```

例如：

```text
1
```

代表使用單一連線。

```text
8
```

代表最多使用 8 條並行連線。

```text
32
```

代表最多使用 32 條並行連線。

實際速度仍取決於：

- 伺服器限制
- 網路頻寬
- HTTP Server 設定
- CDN 限制
- 檔案大小
- 伺服器是否支援 Range
- 伺服器允許的同時連線數

因此增加連線數並不一定會讓速度變快。

---

## 暫存檔

下載過程中會使用：

```text
<目標檔案>.part
```

例如：

```text
Minecraft.zip
Minecraft.zip.part
```

下載完成後，程式會使用 `os.replace()` 將 `.part` 檔案移動為最終檔案。

這樣可以避免下載尚未完成時直接產生看似完整的目標檔案。

---

## 專案結構

```text
multi-thread-downloader/
│
├── README.md
├── en.md
└── main.py
```

如果之後加入圖片：

```text
multi-thread-downloader/
│
├── README.md
├── en.md
├── main.py
└── docs/
    └── screenshot.png
```

---

## 使用的 Python 標準函式庫

本專案主要使用 Python Standard Library：

- `os`
- `queue`
- `re`
- `threading`
- `urllib`
- `concurrent.futures`
- `pathlib`
- `tkinter`

不需要額外安裝第三方下載套件。

---

## 注意事項

### 伺服器必須允許 Range

多線程模式需要伺服器支援：

```http
Range
```

如果伺服器不支援，程式會自動切換成單一連線。

### 高連線數不一定比較快

設定 100 條連線並不代表一定能達到最高速度。

部分伺服器、CDN 或網路環境可能會限制大量並行連線。

### 目前不支援斷點續傳

`.part` 檔案目前主要用於下載中的暫存。

如果程式中途關閉，再次啟動時不會自動解析 `.part` 並從上次進度繼續。

---

## License

本專案採用 MIT License。

詳細內容請參閱 [LICENSE](LICENSE)。

---

## Author

**Wayne**

GitHub：

[Wayne27304](https://github.com/Wayne27304)

Project：

[Multi-Thread Downloader](https://github.com/Wayne27304/multi-thread-downloader)

---

[English Version](en.md)
