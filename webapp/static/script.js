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

let currentMp3Name = null;
let selectedProjectId = null;
let projectCache = [];

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
  currentMp3Name = null;
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
