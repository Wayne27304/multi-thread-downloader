# Multi-Thread Downloader

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**English** · [繁體中文](README.md)

A simple multi-threaded HTTP/HTTPS downloader built with Python and Tkinter.

When HTTP Range requests are supported, files can be split into multiple sections and downloaded simultaneously using multiple connections, which may improve download performance in some server environments.

---

## Features

- Multi-connection downloads
- Supports up to **100 connections**
- Automatically detects whether the server supports HTTP Range requests
- Automatically uses segmented downloads when Range is supported
- Automatically falls back to a single connection when Range is not supported
- Real-time download progress
- Displays downloaded size and total file size
- Download cancellation
- Custom file save location
- Automatically determines the default filename from the URL
- Uses `.part` temporary files instead of directly writing to the final file
- Automatically renames the temporary file after the download is completed
- Windows Tkinter graphical interface
- No third-party Python packages required

---

## Requirements

- Python **3.x**
- Tkinter
- Network access to HTTP / HTTPS servers

This project primarily uses the Python Standard Library, so no additional packages need to be installed through `pip`.

---

## Installation

### 1. Download the Project (Git)

```bash
git clone https://github.com/Wayne27304/multi-thread-downloader.git
cd multi-thread-downloader
```

### 2. Run the Application

```bash
python main.py
```

---

## Usage

After launching the application:

1. Enter the HTTP / HTTPS URL you want to download.
2. Select the file save location.
3. Set the number of connections.
4. Click **Start Download**.
5. The application automatically checks whether the server supports Range requests.
6. If supported, the application uses multiple connections to download the file.
7. If unsupported, the application automatically switches to a single connection.

The default connection count is:

```text
8
```

The maximum connection count is:

```text
100
```

---

## How Multi-Threaded Downloading Works

The application first sends the following request to the server:

```http
Range: bytes=0-0
```

If the server responds with:

```http
206 Partial Content
```

and provides a valid:

```http
Content-Range
```

for example:

```http
Content-Range: bytes 0-0/104857600
```

the application can determine the total file size and split the file into multiple sections.

For example, with:

```text
4 connections
```

a file may be divided into:

```text
Connection 1 → bytes 0 - 26214399
Connection 2 → bytes 26214400 - 52428799
Connection 3 → bytes 52428800 - 78643199
Connection 4 → bytes 78643200 - 104857599
```

Each connection is responsible for its assigned range and writes the downloaded data directly to the corresponding position in the `.part` temporary file.

After the download is completed:

```text
example.zip.part
```

is renamed to:

```text
example.zip
```

---

## Servers Without Range Support

If the server does not support HTTP Range requests, the application does not force multi-threaded downloading.

Instead, it automatically displays:

```text
Server does not support segmented downloads, falling back to a single connection
```

and uses a normal HTTP connection to download the file.

This helps prevent download failures caused by servers that do not support Range requests.

---

## Download Progress

When the server provides the total file size, the interface displays information such as:

```text
75.4%

75.40 MB / 100.00 MB
```

If the server does not provide `Content-Length`, the application displays the amount currently downloaded:

```text
Downloaded 75.40 MB (total size unknown)
```

and uses an indeterminate progress indicator to show the download status.

---

## Canceling a Download

During a download, you can click:

**Cancel**

The application will stop further download operations.

The unfinished temporary file will remain, for example:

```text
example.zip.part
```

The current version does not automatically resume a download from an existing `.part` file.

---

## Connection Count

The connection count can be configured from:

```text
1 ~ 100
```

For example:

```text
1
```

means that a single connection is used.

```text
8
```

means that up to 8 concurrent connections can be used.

```text
32
```

means that up to 32 concurrent connections can be used.

Actual download speed still depends on:

- Server limitations
- Network bandwidth
- HTTP server configuration
- CDN limitations
- File size
- Whether the server supports Range requests
- The number of simultaneous connections allowed by the server

Therefore, increasing the connection count does not necessarily make the download faster.

---

## Temporary Files

During the download process, the application uses:

```text
<destination>.part
```

For example:

```text
Minecraft.zip
Minecraft.zip.part
```

After the download is completed, the application uses `os.replace()` to move the `.part` file to the final destination.

This prevents an incomplete download from appearing as the final completed file.

---

## Python Standard Library

This project primarily uses the Python Standard Library:

- `os`
- `queue`
- `re`
- `threading`
- `urllib`
- `concurrent.futures`
- `pathlib`
- `tkinter`

No additional third-party downloader packages are required.

---

## Notes

### More Connections Do Not Always Mean Higher Speed

Setting the connection count to 100 does not guarantee the highest possible download speed.

Some servers, CDNs, or network environments may limit the number of simultaneous connections.

### Resume Is Currently Not Supported

The `.part` file is currently used as a temporary file during the download process.

If the application is closed while downloading, it will not automatically analyze the existing `.part` file and resume the download from the previous progress.

---

## License

This project is licensed under the MIT License.

For more information, see [LICENSE](LICENSE).

---

## Author

**Wayne**

GitHub:

[Wayne27304](https://github.com/Wayne27304)

Project:

[Multi-Thread Downloader](https://github.com/Wayne27304/multi-thread-downloader)

---

[繁體中文版](README.md)
