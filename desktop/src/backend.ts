import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import fs from 'fs';
import path from 'path';
import { setTimeout as delay } from 'timers/promises';
import { dialog } from 'electron';
import { backendPort, skipBackendSpawn } from './env';

/**
 * 中文注释：后端仅监听回环地址，避免桌面应用在用户机器上意外暴露 HTTP 服务。
 */
const BACKEND_HOST = '127.0.0.1';

/**
 * 中文注释：在仓库根目录寻找 Python 解释器，以优先使用项目自带虚拟环境，若不存在再回落到系统 python/python3。
 */
function resolvePythonExecutable(): string {
  if (process.env.MM_PYTHON_PATH && fs.existsSync(process.env.MM_PYTHON_PATH)) {
    return process.env.MM_PYTHON_PATH;
  }
  const repoRoot = path.resolve(__dirname, '..', '..');
  const candidates = [
    path.join(repoRoot, '.venv', 'bin', 'python'),
    path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(repoRoot, '.venv', 'Scripts', 'python'),
    path.join(repoRoot, 'venv', 'bin', 'python'),
    path.join(repoRoot, 'venv', 'Scripts', 'python.exe'),
    'python3',
    'python'
  ];
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate) || candidate === 'python' || candidate === 'python3') {
        return candidate;
      }
    } catch (error) {
      // 中文注释：fs.existsSync 在某些权限受限环境可能抛错，忽略后继续回退。
    }
  }
  return 'python';
}

/**
 * 中文注释：BackendManager 负责启动、探活与优雅终止 FastAPI 子进程；
 * Electron 主进程只需调用 ensureStarted/stop 即可实现全生命周期管理。
 */
export class BackendManager {
  private child?: ChildProcessWithoutNullStreams;
  private stopping = false;

  constructor(private readonly port: number = backendPort) {}

  /**
   * 中文注释：开发模式下如果外部已通过 --reload 启动后端，则跳过 spawn；
   * 否则由 Electron 主进程负责启动 uvicorn 并等待健康检查通过。
   */
  async ensureStarted(): Promise<void> {
    if (!skipBackendSpawn) {
      await this.spawnBackend();
    }
    await this.waitUntilHealthy();
  }

  /**
   * 中文注释：spawnBackend 尝试使用虚拟环境中的 python 执行 uvicorn，
   * 并将 stdout/stderr 输出到 Electron 控制台，方便排查用户环境依赖问题。
   */
  private async spawnBackend(): Promise<void> {
    if (this.child) {
      return;
    }
    const python = resolvePythonExecutable();
    const repoRoot = path.resolve(__dirname, '..', '..');
    const args = [
      '-m',
      'uvicorn',
      'motifmaker.api:app',
      '--host',
      BACKEND_HOST,
      '--port',
      String(this.port),
      '--workers',
      '1'
    ];
    try {
      this.child = spawn(python, args, {
        cwd: repoRoot,
        env: {
          ...process.env,
          MM_BACKEND_STARTED_BY: 'electron'
        }
      });
    } catch (error) {
      dialog.showErrorBox(
        'Backend launch failed',
        '无法启动内置 FastAPI 后端，请确认已安装 Python 以及项目依赖。\n' +
          `详细错误：${String(error)}`
      );
      throw error;
    }

    // 中文注释：将后端日志输出到控制台，便于调试；生产环境用户可在系统日志查看。
    this.child.stdout.on('data', (chunk) => {
      console.log(`[backend] ${chunk}`.trim());
    });
    this.child.stderr.on('data', (chunk) => {
      console.error(`[backend] ${chunk}`.trim());
    });

    this.child.on('error', (error) => {
      dialog.showErrorBox(
        'Backend launch failed',
        '无法创建 Python 子进程，请确认已正确安装解释器并在环境变量中可见。\n' +
          `详细错误：${String(error)}`
      );
    });

    this.child.on('exit', (code, signal) => {
      console.log(`FastAPI backend exited with code=${code} signal=${signal}`);
      if (!this.stopping && !skipBackendSpawn) {
        dialog.showErrorBox(
          'Backend exited',
          'FastAPI 后端异常退出，请检查 Python 环境或端口占用后重新启动应用。'
        );
      }
    });
  }

  /**
   * 中文注释：通过轮询 /healthz 接口探活，最大等待 20 秒，期间每 500ms 重试一次；
   * 若连续超时则提示用户可能是依赖缺失或端口冲突。
   */
  private async waitUntilHealthy(): Promise<void> {
    const deadline = Date.now() + 20_000;
    const url = `http://${BACKEND_HOST}:${this.port}/healthz`;
    while (Date.now() < deadline) {
      try {
        const response = await fetch(url, { cache: 'no-store' });
        if (response.ok) {
          return;
        }
      } catch (error) {
        // 中文注释：初始阶段后端可能尚未监听，忽略错误继续等待。
      }
      await delay(500);
    }
    dialog.showErrorBox(
      'Backend timeout',
      'FastAPI 后端未在预期时间内启动，请确认 Python 依赖已安装且端口未被占用。'
    );
    throw new Error('Backend did not become healthy in time');
  }

  /**
   * 中文注释：stop 会尝试向 uvicorn 发送 SIGTERM，并在超时后根据平台执行强制终止，
   * 保证 Electron 退出时不会遗留僵尸进程。
   */
  async stop(): Promise<void> {
    if (!this.child) {
      return;
    }
    this.stopping = true;
    const child = this.child;
    if (process.platform === 'win32') {
      await new Promise<void>((resolve) => {
        const killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F']);
        killer.on('exit', () => resolve());
        killer.on('error', () => resolve());
      });
    } else {
      let exited = false;
      const waitForExit = new Promise<void>((resolve) => {
        child.once('exit', () => {
          exited = true;
          resolve();
        });
      });
      child.kill('SIGTERM');
      await Promise.race([waitForExit, delay(5_000)]);
      if (!exited) {
        child.kill('SIGKILL');
      }
    }
    this.child = undefined;
    this.stopping = false;
  }
}

/**
 * 中文注释：提供一个全局单例，避免多次创建后端进程。
 */
export const backendManager = new BackendManager();
