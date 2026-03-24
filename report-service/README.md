# Report Service (Node + Puppeteer)

独立 PDF 报告服务，供后端通过 HTTP 调用。

## 接口

- `GET /health`
- `POST /api/v1/reports/render`：请求体为报告数据 JSON，返回 `application/pdf`

## 本地运行

```bash
cd report-service
npm install
npm start
```

默认端口 `3001`。
