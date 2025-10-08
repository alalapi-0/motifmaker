<!--
  MotifMaker Kubernetes 占位说明
  当前版本未提供完整清单，后续可根据部署需求扩展。
-->
# MotifMaker Kubernetes 部署提示

- 本目录预留给未来的 Kubernetes 配置（Deployment、Service、Ingress 等）。
- 如需自行编写清单，请参考以下建议：
  - 使用 ConfigMap 或 Secret 注入环境变量，确保敏感信息安全。
  - 通过 PersistentVolume 声明 outputs/ 与 projects/ 持久化卷。
  - 使用 HorizontalPodAutoscaler 根据 CPU/MEM 或自定义指标扩缩容。
- 完整步骤可在后续版本补充，欢迎在 issue 中反馈需求。
