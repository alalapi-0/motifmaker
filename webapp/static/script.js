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
const btnProjectList = document.getElementById("btn-project-list");
const btnProjectSave = document.getElementById("btn-project-save");
const btnProjectLoad = document.getElementById("btn-project-load");
const btnProjectDelete = document.getElementById("btn-project-delete");
const btnProjectRename = document.getElementById("btn-project-rename");
const projectTableBody = document.getElementById("project-table-body");
const btnAutoMix = document.getElementById("btn-auto-mix");
const btnApplyMix = document.getElementById("btn-apply-mix");
const btnPreviewMix = document.getElementById("btn-preview-mix");
const mixPreviewPlayer = document.getElementById("mix-preview");
const mixControls = {
  mainVolume: document.getElementById("mix-main-volume"),
  bgVolume: document.getElementById("mix-bg-volume"),
  noiseVolume: document.getElementById("mix-noise-volume"),
  mainPan: document.getElementById("mix-main-pan"),
  bgPan: document.getElementById("mix-bg-pan"),
  noisePan: document.getElementById("mix-noise-pan"),
  reverb: document.getElementById("mix-reverb"),
  eqLow: document.getElementById("mix-eq-low"),
  eqHigh: document.getElementById("mix-eq-high"),
};
const mixOutputs = {
  mainVolume: document.getElementById("mix-main-volume-value"),
  bgVolume: document.getElementById("mix-bg-volume-value"),
  noiseVolume: document.getElementById("mix-noise-volume-value"),
  mainPan: document.getElementById("mix-main-pan-value"),
  bgPan: document.getElementById("mix-bg-pan-value"),
  noisePan: document.getElementById("mix-noise-pan-value"),
  reverb: document.getElementById("mix-reverb-value"),
  eqLow: document.getElementById("mix-eq-low-value"),
  eqHigh: document.getElementById("mix-eq-high-value"),
};

// 专辑面板相关元素引用，便于后续统一更新状态
const albumTitleInput = document.getElementById("album-title");
const albumTracksInput = document.getElementById("album-tracks");
const albumBpmInput = document.getElementById("album-bpm");
const albumBarsInput = document.getElementById("album-bars");
const albumSeedInput = document.getElementById("album-seed");
const albumScaleSelect = document.getElementById("album-scale");
const albumAutoMixCheckbox = document.getElementById("album-auto-mix");
const albumPlanButton = document.getElementById("album-btn-plan");
const albumStartButton = document.getElementById("album-btn-start");
const albumRefreshButton = document.getElementById("album-btn-refresh");
const albumDownloadButton = document.getElementById("album-btn-download");
const albumProgressBar = document.getElementById("album-progress");
const albumStatusText = document.getElementById("album-status-text");
const albumTrackList = document.getElementById("album-track-list");

let currentMp3Name = null;
let selectedProjectId = null;
let projectCache = [];
let latestMixPreviewUrl = null;
let albumTaskId = null;
let albumPlanData = null;
let albumPollTimer = null;
let albumZipUrl = null;
let albumLastStatus = null;

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

// 混音预览播放器与主预览相互独立，便于来回比较
function playMixPreview(url) {
  if (!url) {
    return;
  }
  const cacheBusted = url.includes("?") ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
  latestMixPreviewUrl = cacheBusted;
  mixPreviewPlayer.src = cacheBusted;
  mixPreviewPlayer.play().catch(() => {});
}

// 重置下载链接与播放器状态，适用于清理与流程重置
function resetMediaState() {
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
  currentMp3Name = null;
  mixPreviewPlayer.pause();
  mixPreviewPlayer.removeAttribute("src");
  mixPreviewPlayer.load();
  latestMixPreviewUrl = null;
}

// 清理专辑面板的显示状态，通常在重新规划时调用
function resetAlbumPanel() {
  if (albumPollTimer) {
    clearTimeout(albumPollTimer);
    albumPollTimer = null;
  }
  albumProgressBar.value = 0;
  albumStatusText.textContent = "No album task planned.";
  albumTrackList.innerHTML = "";
  albumZipUrl = null;
  albumTaskId = null;
  albumPlanData = null;
  albumLastStatus = null;
  updateAlbumControls();
}

// 根据当前任务状态切换按钮可用性
function updateAlbumControls() {
  const inProgress = albumPlanData && albumLastStatus === "running";
  albumStartButton.disabled = !albumPlanData || inProgress;
  albumRefreshButton.disabled = !albumTaskId;
  albumDownloadButton.disabled = !albumZipUrl;
}

// 收集表单数据，准备发送给后端的 JSON 负载
function collectAlbumPayload() {
  const parsedSeed = albumSeedInput.value.trim();
  return {
    title: albumTitleInput.value.trim(),
    num_tracks: Number(albumTracksInput.value) || 1,
    base_bpm: Number(albumBpmInput.value) || 120,
    bars_per_track: Number(albumBarsInput.value) || 16,
    base_seed: parsedSeed === "" ? null : Number(parsedSeed),
    scale: albumScaleSelect.value,
    auto_mix: albumAutoMixCheckbox.checked,
  };
}

// 渲染状态快照中的已生成曲目列表，包含可播放的音频标签
function renderAlbumTrackList(results) {
  albumTrackList.innerHTML = "";
  results.forEach((track) => {
    const li = document.createElement("li");
    const duration = typeof track.duration_sec === "number" ? `${track.duration_sec.toFixed(1)}s` : "-";
    li.textContent = `#${String(track.index).padStart(2, "0")} ${track.title || "Track"} (${track.bpm || 0} BPM, ${duration})`;
    if (track.mp3_url) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.src = `${track.mp3_url}?t=${Date.now()}`;
      audio.style.display = "block";
      li.appendChild(audio);
    }
    albumTrackList.appendChild(li);
  });
}

// 处理状态接口返回的数据，更新进度与提示文案
function applyAlbumSnapshot(snapshot) {
  albumProgressBar.value = Number(snapshot.progress || 0);
  albumStatusText.textContent = `Status: ${snapshot.status || "unknown"} (${snapshot.progress || 0}%)`;
  albumLastStatus = snapshot.status || null;
  if (Array.isArray(snapshot.results)) {
    renderAlbumTrackList(snapshot.results);
  }
  if (snapshot.zip_url) {
    albumZipUrl = snapshot.zip_url;
  }
  if (snapshot.message) {
    updateLog(snapshot);
  }
  updateAlbumControls();
}

// 启动或重置轮询定时器，默认每 3 秒刷新一次状态
function scheduleAlbumPolling() {
  if (albumPollTimer) {
    clearTimeout(albumPollTimer);
  }
  albumPollTimer = setTimeout(() => {
    refreshAlbumStatus(false);
  }, 3000);
}

async function planAlbum() {
  const payload = collectAlbumPayload();
  updateLog({ message: "Planning album...", payload });
  resetAlbumPanel();
  try {
    const response = await fetch("/album/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      updateLog(data);
      return;
    }
    albumTaskId = data.task_id;
    albumPlanData = data.plan;
    albumZipUrl = null;
    albumProgressBar.value = 0;
    albumStatusText.textContent = `Planned ${data.plan.num_tracks} tracks. Ready to start.`;
    albumTrackList.innerHTML = "";
    if (albumPollTimer) {
      clearTimeout(albumPollTimer);
      albumPollTimer = null;
    }
    updateAlbumControls();
    albumRefreshButton.disabled = false;
    updateLog(data);
  } catch (error) {
    updateLog(`Failed to plan album: ${error}`);
  }
}

async function startAlbumGeneration() {
  if (!albumTaskId) {
    updateLog("No album task to start. Plan the album first.");
    return;
  }
  updateLog("Starting album generation...");
  try {
    const response = await fetch(`/album/generate/${albumTaskId}`, { method: "POST" });
    const data = await response.json();
    if (!response.ok || data.error) {
      updateLog(data);
      return;
    }
    albumProgressBar.value = 5;
    albumStatusText.textContent = "Status: running (5%)";
    updateAlbumControls();
    scheduleAlbumPolling();
  } catch (error) {
    updateLog(`Failed to start album generation: ${error}`);
  }
}

async function refreshAlbumStatus(manual = true) {
  if (!albumTaskId) {
    if (manual) {
      updateLog("No album task to refresh.");
    }
    return;
  }
  try {
    const response = await fetch(`/album/status/${albumTaskId}`);
    const data = await response.json();
    if (!response.ok || data.error) {
      updateLog(data);
      return;
    }
    applyAlbumSnapshot(data);
    if (data.status === "running") {
      scheduleAlbumPolling();
    } else {
      if (albumPollTimer) {
        clearTimeout(albumPollTimer);
        albumPollTimer = null;
      }
      if (data.zip_url) {
        albumZipUrl = data.zip_url;
        updateAlbumControls();
      }
    }
    if (manual) {
      updateLog(data);
    }
  } catch (error) {
    updateLog(`Failed to fetch album status: ${error}`);
  }
}

function downloadAlbumZip() {
  if (!albumZipUrl) {
    updateLog("Album ZIP not ready yet.");
    return;
  }
  window.location.href = albumZipUrl;
}

// 实时更新滑块右侧的数值显示，方便精确调节
function bindMixSlider(input, output) {
  input.addEventListener("input", () => {
    output.textContent = Number(input.value).toFixed(2);
  });
  // 初始化一次显示
  output.textContent = Number(input.value).toFixed(2);
}

bindMixSlider(mixControls.mainVolume, mixOutputs.mainVolume);
bindMixSlider(mixControls.bgVolume, mixOutputs.bgVolume);
bindMixSlider(mixControls.noiseVolume, mixOutputs.noiseVolume);
bindMixSlider(mixControls.mainPan, mixOutputs.mainPan);
bindMixSlider(mixControls.bgPan, mixOutputs.bgPan);
bindMixSlider(mixControls.noisePan, mixOutputs.noisePan);
bindMixSlider(mixControls.reverb, mixOutputs.reverb);
bindMixSlider(mixControls.eqLow, mixOutputs.eqLow);
bindMixSlider(mixControls.eqHigh, mixOutputs.eqHigh);

// 读取滑块当前值，构建发送给后端的参数字典
function collectMixParams() {
  return {
    main_volume: Number(mixControls.mainVolume.value),
    bg_volume: Number(mixControls.bgVolume.value),
    noise_volume: Number(mixControls.noiseVolume.value),
    panning: {
      main: Number(mixControls.mainPan.value),
      bg: Number(mixControls.bgPan.value),
      noise: Number(mixControls.noisePan.value),
    },
    reverb: Number(mixControls.reverb.value),
    eq_low: Number(mixControls.eqLow.value),
    eq_high: Number(mixControls.eqHigh.value),
  };
}

// 将后端返回的建议值写回滑块，保持界面与实际状态一致
function applyMixParams(params) {
  if (!params) {
    return;
  }
  const safe = (value, fallback) => (typeof value === "number" ? value : fallback);
  mixControls.mainVolume.value = safe(params.main_volume, Number(mixControls.mainVolume.value));
  mixControls.bgVolume.value = safe(params.bg_volume, Number(mixControls.bgVolume.value));
  mixControls.noiseVolume.value = safe(params.noise_volume, Number(mixControls.noiseVolume.value));
  const pan = params.panning || {};
  mixControls.mainPan.value = safe(pan.main, Number(mixControls.mainPan.value));
  mixControls.bgPan.value = safe(pan.bg, Number(mixControls.bgPan.value));
  mixControls.noisePan.value = safe(pan.noise, Number(mixControls.noisePan.value));
  mixControls.reverb.value = safe(params.reverb, Number(mixControls.reverb.value));
  mixControls.eqLow.value = safe(params.eq_low, Number(mixControls.eqLow.value));
  mixControls.eqHigh.value = safe(params.eq_high, Number(mixControls.eqHigh.value));

  // 更新显示文本
  Object.entries(mixOutputs).forEach(([key, output]) => {
    const control = mixControls[key];
    if (control) {
      output.textContent = Number(control.value).toFixed(2);
    }
  });
}

// 高亮选中的行，便于用户确认当前操作对象
function highlightSelectedRow(row) {
  projectTableBody.querySelectorAll("tr").forEach((tr) => tr.classList.remove("selected"));
  if (row) {
    row.classList.add("selected");
  }
}

// 根据接口返回的数据刷新项目列表表格
function updateProjectTable(projects) {
  projectCache = projects;
  projectTableBody.innerHTML = "";
  let hasSelection = false;

  projects.forEach((project) => {
    const projectId = Number(project.id);
    const row = document.createElement("tr");
    row.dataset.projectId = projectId;

    const selectCell = document.createElement("td");
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "project-select";
    radio.value = projectId;
    radio.addEventListener("change", (event) => {
      event.stopPropagation();
      selectedProjectId = projectId;
      highlightSelectedRow(row);
    });
    selectCell.appendChild(radio);
    row.appendChild(selectCell);

    const nameCell = document.createElement("td");
    nameCell.textContent = project.name || "(unnamed project)";
    row.appendChild(nameCell);

    const createdCell = document.createElement("td");
    createdCell.textContent = project.created_at || "-";
    row.appendChild(createdCell);

    const lengthCell = document.createElement("td");
    lengthCell.textContent = project.length != null ? project.length : "-";
    row.appendChild(lengthCell);

    const actionCell = document.createElement("td");
    if (project.mp3_url) {
      const previewButton = document.createElement("button");
      previewButton.textContent = "Preview";
      previewButton.classList.add("secondary");
      previewButton.addEventListener("click", (event) => {
        event.stopPropagation();
        playPreview(project.mp3_url);
        currentMp3Name = project.mp3_path ? project.mp3_path.split(/[/\\]/).pop() : null;
      });
      actionCell.appendChild(previewButton);
    } else {
      actionCell.textContent = "No audio";
    }
    row.appendChild(actionCell);

    row.addEventListener("click", () => {
      radio.checked = true;
      selectedProjectId = projectId;
      highlightSelectedRow(row);
    });

    if (selectedProjectId === projectId) {
      radio.checked = true;
      highlightSelectedRow(row);
      hasSelection = true;
    }

    projectTableBody.appendChild(row);
  });

  if (!hasSelection) {
    selectedProjectId = null;
    highlightSelectedRow(null);
  }
}

// 绑定专辑面板按钮的点击事件
albumPlanButton.addEventListener("click", (event) => {
  event.preventDefault();
  planAlbum();
});

albumStartButton.addEventListener("click", (event) => {
  event.preventDefault();
  startAlbumGeneration();
});

albumRefreshButton.addEventListener("click", (event) => {
  event.preventDefault();
  refreshAlbumStatus(true);
});

albumDownloadButton.addEventListener("click", (event) => {
  event.preventDefault();
  downloadAlbumZip();
});

// 页面初始化时根据默认状态刷新一次按钮可用性
updateAlbumControls();

// 调用 API 并刷新表格，出现错误时交给 requestJSON 统一处理
async function refreshProjects() {
  try {
    const data = await requestJSON("/projects");
    const projects = Array.isArray(data.projects) ? data.projects : [];
    updateProjectTable(projects);
  } catch (error) {
    // 错误已经在 requestJSON 内部记录，这里无需额外处理
  }
}

// 从缓存中获取当前选中项目，便于后续操作
function getSelectedProject() {
  if (selectedProjectId == null) {
    return null;
  }
  return projectCache.find((item) => Number(item.id) === Number(selectedProjectId)) || null;
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
    currentMp3Name = data.filename || null;
  }
});

// 自动混音：请求后端参数并刷新滑块
btnAutoMix.addEventListener("click", async () => {
  try {
    const data = await requestJSON("/mix/auto");
    if (data.params) {
      applyMixParams(data.params);
    }
    if (data.preview_url) {
      playMixPreview(data.preview_url);
    }
  } catch (error) {
    // requestJSON 已处理错误日志
  }
});

// 应用当前滑块参数，后端返回的值会再次刷新滑块
btnApplyMix.addEventListener("click", async () => {
  const params = collectMixParams();
  try {
    const data = await requestJSON("/mix/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params }),
    });
    if (data.params) {
      applyMixParams(data.params);
    }
    if (data.preview_url) {
      playMixPreview(data.preview_url);
    }
  } catch (error) {
    // 错误已记录
  }
});

// 快速试听最近一次混音结果
btnPreviewMix.addEventListener("click", () => {
  const url = latestMixPreviewUrl || "/mix/preview?file=preview_mix.wav";
  playMixPreview(url);
});

// 清理 outputs 目录，同时重置按钮与媒体状态
btnCleanup.addEventListener("click", async () => {
  await requestJSON("/cleanup", { method: "DELETE" });
  resetMediaState();
  btnMelody.disabled = true;
  btnRender.disabled = true;
  btnMotifRegenerate.hidden = true;
  btnMelodyRegenerate.hidden = true;
  selectedProjectId = null;
  highlightSelectedRow(null);
});

// 关闭服务器，收到成功响应后提示用户
btnShutdown.addEventListener("click", async () => {
  await requestJSON("/shutdown", { method: "POST" });
  alert("Server stopped. You may close this tab.");
});

// 列出所有项目并刷新表格
btnProjectList.addEventListener("click", async () => {
  await refreshProjects();
});

// 保存当前会话的项目，需要已有的 MP3 文件名
btnProjectSave.addEventListener("click", async () => {
  if (!currentMp3Name) {
    alert("Please render a project before saving.");
    return;
  }
  const name = prompt("Project name (leave blank for timestamp):", "") || "";
  try {
    await requestJSON("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, mp3_name: currentMp3Name }),
    });
    await refreshProjects();
  } catch (error) {
    // 错误日志已在 requestJSON 中处理
  }
});

// 加载选中的项目，自动播放对应的 MP3
btnProjectLoad.addEventListener("click", async () => {
  if (selectedProjectId == null) {
    alert("Select a project first.");
    return;
  }
  try {
    const data = await requestJSON(`/projects/${selectedProjectId}`);
    if (data.mp3_url) {
      playPreview(data.mp3_url);
    }
    if (data.project && data.project.mp3_path) {
      currentMp3Name = data.project.mp3_path.split(/[/\\]/).pop();
    }
  } catch (error) {
    // 已有日志
  }
});

// 删除选中项目并刷新列表
btnProjectDelete.addEventListener("click", async () => {
  if (selectedProjectId == null) {
    alert("Select a project first.");
    return;
  }
  if (!confirm("Delete the selected project?")) {
    return;
  }
  try {
    await requestJSON(`/projects/${selectedProjectId}`, { method: "DELETE" });
    selectedProjectId = null;
    await refreshProjects();
  } catch (error) {
    // 已记录
  }
});

// 重命名选中项目
btnProjectRename.addEventListener("click", async () => {
  if (selectedProjectId == null) {
    alert("Select a project first.");
    return;
  }
  const project = getSelectedProject();
  const newName = prompt("New project name:", project ? project.name : "");
  if (newName == null) {
    return;
  }
  const trimmed = newName.trim();
  if (!trimmed) {
    alert("Project name cannot be empty.");
    return;
  }
  try {
    await requestJSON(`/projects/${selectedProjectId}/rename`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: trimmed }),
    });
    await refreshProjects();
  } catch (error) {
    // 已记录
  }
});
