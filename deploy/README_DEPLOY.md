<!--
  中文部署说明文档
  本文件详细介绍项目在多种环境中的部署方式以及运维要点。
-->
# MotifMaker 部署与运维指南

> 本文档帮助运维人员在保持核心功能不变的前提下，将 MotifMaker 后端（FastAPI）与前端（Vite+React）安全、稳定地部署到不同平台。

> As of this release, the MotifMaker web interface is in English only. To localize in the future, extend the i18n dictionary before rebuilding the web bundle.

## 1. 部署路径选择对比

| 场景 | 优点 | 适用人群 | 备注 |
| ---- | ---- | -------- | ---- |
| VPS/裸机 | 完整控制系统、便于调优，使用 systemd + 反向代理 管理 | 熟悉 Linux 的研发/运维 | 需要自行维护安全补丁与监控 |
| PaaS | 平台托管运行时，易于扩缩容 | 希望快速上线的团队 | 注意 PaaS 的资源配额与网络出站限制 |
| Docker/Compose | 打包成容器，环境一致性强 | 想用容器化快速启动的人 | 适用于开发和小规模试运行 |
| 反向代理（Nginx/Caddy） | 提供统一入口、TLS 与缓存 | 所有需要对外暴露服务的场景 | 建议后端仅监听回环地址 |

> **提示：** 初次部署推荐按照 VPS 场景操作，随后可以根据团队经验迁移到 Docker 或 PaaS。

## 2. VPS/裸机部署流程

1. **克隆仓库**
   ```bash
   git clone https://your.git.repo/motifmaker.git
   cd motifmaker
   ```
   - 在拉取前确认机器仅开放 22/80/443 端口。

2. **创建虚拟环境并安装依赖**
   ```bash
   bash deploy/scripts/install_python_venv.sh
   ```
   - 脚本会创建 `.venv` 目录、安装 `requirements.txt`，遇到网络慢可按注释切换镜像源。

3. **准备环境变量文件**
   ```bash
   cp deploy/env/.env.example.server .env
   # 编辑 .env，填入 ALLOWED_ORIGINS、LOG_LEVEL 等参数
   ```
   - `.env` 含敏感信息，请勿提交到仓库。

4. **注册 systemd 服务**
   ```bash
   bash deploy/scripts/setup_systemd.sh
   ```
   - 脚本会生成 `motifmaker.service`。完成后根据提示执行 `systemctl daemon-reload && systemctl enable --now motifmaker`。

5. **配置反向代理**
   - Nginx：将 `deploy/nginx/motifmaker.conf.example` 拷贝到 `/etc/nginx/conf.d/` 并按注释修改域名/路径。
   - Caddy：将 `deploy/caddy/Caddyfile.example` 拷贝到 `/etc/caddy/`。
   - 记得重新加载代理服务并检查 TLS。

6. **健康检查与烟囱测试**
   ```bash
   bash deploy/scripts/check_health.sh
   bash deploy/scripts/smoke_test.sh
   ```
   - 如有失败，根据脚本输出排查后端服务与反向代理。

7. **防火墙与安全**
   - 保持仅开放 22/80/443 端口。
   - 后端 FastAPI 进程监听 `127.0.0.1`，只通过反向代理对外发布。

## 3. Docker / Docker Compose 部署流程

1. **准备环境变量**
   ```bash
   cp deploy/env/.env.example.docker .env
   ```
   - Compose 会读取 `.env` 中的同名变量注入容器。

2. **构建并启动容器**
   ```bash
   docker compose -f deploy/docker/docker-compose.yml up -d
   ```
   - `api` 服务暴露 `8000`，`web` 服务暴露 `80`。首次启动会自动安装依赖并编译前端。

3. **卷与数据持久化**
   - `outputs/` 与 `projects/` 使用卷挂载到宿主，确保生成的 MIDI/JSON 不丢失。
   - 如需远程存储，可替换为对象存储或 NFS。

4. **访问服务**
   - 浏览器访问 `http://<宿主机 IP>`，前端会通过 `VITE_API_BASE` 指向后端。

5. **停止与更新**
   ```bash
   docker compose -f deploy/docker/docker-compose.yml down
   docker compose -f deploy/docker/docker-compose.yml pull
   docker compose -f deploy/docker/docker-compose.yml up -d
   ```
   - 更新镜像后重新启动即可。

## 4. 域名与 HTTPS 配置

- **Nginx + Certbot**
  1. 安装 Certbot：`sudo apt install certbot python3-certbot-nginx`。
  2. 执行 `sudo certbot --nginx -d api.example.com`，根据向导完成证书申请。
  3. 定期检查 `systemctl status certbot.timer` 确认证书续期正常。

- **Caddy 自动证书**
  - Caddy 会自动向 Let’s Encrypt 申请证书，只需确保 80/443 端口开放。
  - 首次申请可能因 DNS 解析未生效而失败，可稍后重试。

## 5. 日志与监控建议

- 使用 `deploy/scripts/tail_logs.sh` 快速查看后端 journal 日志，Nginx/Caddy 日志请分别查看 `/var/log/nginx/` 或 `/var/lib/caddy/`。
- 应用日志遵循 `src/motifmaker/logging_setup.py` 中的结构，未来可对接 Loki 或 ELK。
- 建议使用 node_exporter + Prometheus 采集系统指标，或在容器环境中启用 cAdvisor。

## 6. 安全实践

- `.env` 不应纳入版本控制，敏感参数可交由秘密管理服务（如 Vault、AWS Secrets Manager）。
- `ALLOWED_ORIGINS` 仅填入可信前端域名，防止跨站请求。
- 及时更新依赖与基础镜像，执行 `pip list --outdated` 与 `npm outdated` 了解升级需求。

## 7. 目录忽略与产物管理

- 仓库已在 `.gitignore` 中忽略 `outputs/`、`projects/`、`web/dist/`、`*.mid` 等二进制产物。
- 部署脚本只生成必要配置，不会写入二进制文件。

## 8. 进一步的可运维化计划

- 后续可引入 Kubernetes，相关约束可参考 `deploy/k8s/README_k8s.md` 占位说明。
- 建议在 CI/CD 中接入 smoke test 并推送到监控平台。

> 若遇到部署问题，请记录命令输出与日志，便于快速定位。
