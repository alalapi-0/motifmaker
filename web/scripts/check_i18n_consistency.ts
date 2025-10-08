#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

// 脚本目标：扫描组件目录，检测是否仍存在中文字符，保障当前版本 UI 保持英文统一，可在未来 PR 流程中作为自动校验步骤。
const componentsDir = path.join(__dirname, "..", "src", "components");
const chineseRegex = /[\u4e00-\u9fa5]/;
let hasWarning = false;
let inBlockComment = false;

// 若未来组件目录结构调整，可在此扩展为递归遍历，便于在 CI 中复用。
const componentFiles = fs
  .readdirSync(componentsDir)
  .filter((file) => file.endsWith(".tsx"));

for (const file of componentFiles) {
  const fullPath = path.join(componentsDir, file);
  const content = fs.readFileSync(fullPath, "utf8");
  const lines = content.split(/\r?\n/);
  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (inBlockComment) {
      if (trimmed.includes("*/")) {
        inBlockComment = false;
      }
      return;
    }

    if (trimmed.startsWith("/*")) {
      if (!trimmed.includes("*/")) {
        inBlockComment = true;
      }
      return;
    }

    const codeWithoutInlineComment = line.split("//")[0];
    let sanitized = codeWithoutInlineComment.replace(/\/\*.*?\*\//g, "");
    if (!sanitized.trim() || /^[{}]*$/.test(sanitized.trim())) {
      return;
    }

    if (chineseRegex.test(sanitized)) {
      if (!hasWarning) {
        console.warn("Chinese characters detected in UI source files:");
        hasWarning = true;
      }
      console.warn(` - ${file}:${index + 1}`);
    }
  });
}

if (!hasWarning) {
  console.log("No Chinese characters found in src/components/*.tsx. UI language is consistent.");
}
