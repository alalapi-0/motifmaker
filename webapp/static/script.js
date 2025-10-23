// 简易工具函数：将对象友好地显示到日志区域
const logBox = document.getElementById("log");
const audioPlayer = document.getElementById("preview-player");
const downloadLink = document.getElementById("download-link");

const btnCheck = document.getElementById("btn-check");
const btnMotif = document.getElementById("btn-motif");
const btnMotifRegenerate = document.getElementById("btn-motif-regenerate");
const btnMelody = document.getElementById("btn-melody");
const btnMelodyRegenerate = document.getElementById("btn-melody-regenerate");
const btnRender = document.getElementById("btn-render");
const btnCleanup = document.getElementById("btn-cleanup");
const btnShutdown = document.getElementById("btn-shutdown");

// 工具函数：统一处理日志输出，字符串直接打印，其他对象转为格式化 JSON
function updateLog(data) {
  if (typeof data === "string") {
    logBox.textContent = data;
  } else {
    logBox.textContent = JSON.stringify(data, null, 2);
  }
}

// 工具函数：播放后端返回的预览音频，同时利用时间戳避免缓存干扰
function playPreview(url) {
  if (!url) {
    return;
  }
  const cacheBusted = url.includes("?") ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
  audioPlayer.src = cacheBusted;
  audioPlayer.play().catch(() => {
    // 若浏览器限制自动播放，这里静默失败即可
  });
}

// 重置下载链接与播放器状态，适用于清理与流程重置
function resetMediaState() {
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
}

// 通用的请求封装，包含错误捕捉与日志输出
async function requestJSON(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed with status ${response.status}`);
    }
    const data = await response.json();
    updateLog(data);
    return data;
  } catch (error) {
    updateLog(`Error: ${error.message}`);
    throw error;
  }
}

// 绑定环境检查按钮，便于随时确认依赖情况
btnCheck.addEventListener("click", async () => {
  await requestJSON("/check_env");
});

// 动机生成的统一处理函数，首次与再生成共用逻辑
async function handleMotifGeneration() {
  const data = await requestJSON("/generate_motif", { method: "POST" });
  playPreview(data.preview_url);
  btnMotifRegenerate.hidden = false;
  btnMelody.disabled = false;
}

btnMotif.addEventListener("click", handleMotifGeneration);
btnMotifRegenerate.addEventListener("click", handleMotifGeneration);

// 旋律与编曲生成逻辑，同样支持再次生成
async function handleMelodyGeneration() {
  const data = await requestJSON("/generate_melody", { method: "POST" });
  playPreview(data.preview_url);
  btnMelodyRegenerate.hidden = false;
  btnRender.disabled = false;
}

btnMelody.addEventListener("click", handleMelodyGeneration);
btnMelodyRegenerate.addEventListener("click", handleMelodyGeneration);

// 渲染最终 MP3 并显示下载链接
btnRender.addEventListener("click", async () => {
  const data = await requestJSON("/render", { method: "POST" });
  if (data.mp3_url) {
    downloadLink.href = data.mp3_url;
    downloadLink.textContent = `Download ${data.filename || "MP3"}`;
    downloadLink.hidden = false;
  }
});

// 清理 outputs 目录，同时重置按钮与媒体状态
btnCleanup.addEventListener("click", async () => {
  await requestJSON("/cleanup", { method: "DELETE" });
  resetMediaState();
  btnMelody.disabled = true;
  btnRender.disabled = true;
  btnMotifRegenerate.hidden = true;
  btnMelodyRegenerate.hidden = true;
});

// 关闭服务器，收到成功响应后提示用户
btnShutdown.addEventListener("click", async () => {
  await requestJSON("/shutdown", { method: "POST" });
  alert("Server stopped. You may close this tab.");
});
